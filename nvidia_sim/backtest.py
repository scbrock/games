"""Walk-forward backtest of the return-distribution models.

Universe: 13 mega-cap tech stocks with earnings dates. Origins: every 63 trading days
2007 -> latest possible. Horizons: 21 / 63 / 126 trading days (~1 / 3 / 6 months).
Each model sees only data up to the origin. Scores: CRPS (lower better), 80% interval
coverage, mean PIT (0.5 = unbiased). Ensemble weights are fitted on origins before 2017
and the ensemble is scored on 2017+ only (true out-of-sample).

Also: leave-one-out test of the CEO-departure drift adjustment on the 22 event firms.
"""
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import event_study
from models import (BlockBootstrap, Context, FactorRegimeJump, GJRGarch, StateAnalogs,
                    build_library, reaction_days, state_features)

HERE = Path(__file__).parent
OUT = HERE / "output"
H = (21, 63, 126)
N = 1000
TICKERS = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD", "AVGO", "INTC", "CSCO", "ORCL", "QCOM", "MU"]
UNIVERSE = TICKERS + ["TSM", "TSLA", "IBM", "TXN", "ADBE", "NFLX", "ASML", "CRM"]
MODELS = [BlockBootstrap(), GJRGarch(), FactorRegimeJump(), StateAnalogs()]
SPLIT = pd.Timestamp("2017-01-01")

_G = {}


def load():
    px = pd.read_csv(HERE / "data" / "prices.csv", index_col=0, parse_dates=True)
    earn = pd.read_csv(HERE / "data" / "earnings_dates.csv")
    return px, earn


def make_context(px, earn, lib, tkr, origin, horizons=H, earn_future_override=None):
    c = px[tkr].dropna()
    r = np.log(c).diff().dropna().loc[:origin]
    m = np.log(px["^IXIC"].dropna()).diff().dropna().loc[:origin]
    vix = px["^VIX"].dropna().loc[:origin]
    all_react = reaction_days(earn.loc[earn.ticker == tkr, "ts"], c.index)
    hist = [d for d in all_react if d <= origin]
    fut_idx = c.index[c.index > origin]
    if earn_future_override is not None:
        fut = earn_future_override
    else:
        fut = [int(fut_idx.get_loc(d)) + 1 for d in all_react if d > origin and d in fut_idx[: max(horizons)]]
    ctx = Context(tkr, origin, r, m, vix, hist, fut, lib)
    ctx.state = state_features(c.loc[:origin], px["^VIX"]).iloc[-1]
    return ctx


def _init():
    px, earn = load()
    _G.update(px=px, earn=earn, lib=build_library(px, px["^VIX"], UNIVERSE, H))


def _run_case(args):
    tkr, origin, seed = args
    px, earn, lib = _G["px"], _G["earn"], _G["lib"]
    rng = np.random.default_rng(seed)
    ctx = make_context(px, earn, lib, tkr, origin)
    c = np.log(px[tkr].dropna())
    i = c.index.get_loc(origin)
    real = {h: float(c.iloc[i + h] - c.iloc[i]) for h in H}
    out = {"ticker": tkr, "origin": origin, "dd": float(ctx.state["dd"]), "real": real, "samples": {}}
    for m in MODELS:
        try:
            out["samples"][m.name] = {h: v.astype(np.float32) for h, v in m.forecast(ctx, H, N, rng).items()}
        except Exception as e:  # noqa: BLE001
            print("fail", m.name, tkr, origin.date(), e)
    return out


_RNG = np.random.default_rng(0)


def crps(s, y):
    return float(np.mean(np.abs(s - y)) - 0.5 * np.mean(np.abs(s - _RNG.permutation(s))))


def score(cases, name, h):
    rows = [(c["samples"][name][h], c["real"][h]) for c in cases if name in c["samples"]]
    pit = np.array([np.mean(s <= y) for s, y in rows])
    return {"n": len(rows), "CRPS": np.mean([crps(s, y) for s, y in rows]),
            "cover80": float(np.mean((pit > .1) & (pit < .9))), "PIT": float(pit.mean())}


def table(cases, names):
    out = []
    for nm in names:
        row = {"model": nm}
        for h in H:
            s = score(cases, nm, h)
            row.update({f"CRPS_{h}": s["CRPS"], f"cov80_{h}": s["cover80"], f"PIT_{h}": s["PIT"]})
        out.append(row)
    return pd.DataFrame(out)


def add_ensemble(cases, weights, rng):
    names = list(weights)
    w = np.array([weights[k] for k in names])
    for c in cases:
        if not all(k in c["samples"] for k in names):
            continue
        counts = rng.multinomial(N, w / w.sum())
        c["samples"]["Ensemble"] = {h: np.concatenate([c["samples"][k][h][:n] for k, n in zip(names, counts)]) for h in H}


def event_adjustment_test(px, earn, lib, rng):
    """LOO: does shifting the factor model by the (shrunk) mean CAR of *other* CEO events help?"""
    ev = event_study.run(px)
    res = []
    for i, e in ev.iterrows():
        others = ev.drop(index=i)
        shift = {h: 0.5 * others[f"car_{h}"].mean() for h in H}  # 50% shrinkage toward zero
        idx = px[e.ticker].dropna().index
        origin = idx[idx.searchsorted(pd.Timestamp(e.day0)) + 1]
        if e.ticker not in TICKERS:
            earn_fut = [i for i in (40, 103) if i <= 126]  # approx quarterly dates when unknown
        else:
            earn_fut = None
        ctx = make_context(px, earn, lib, e.ticker, origin, earn_future_override=earn_fut)
        base = FactorRegimeJump().forecast(ctx, H, 2000, rng)
        c = np.log(px[e.ticker].dropna())
        j = c.index.get_loc(origin)
        for h in H:
            y = float(c.iloc[j + h] - c.iloc[j])
            res.append({"h": h, "base": crps(base[h], y), "adjusted": crps(base[h] + shift[h], y)})
    r = pd.DataFrame(res).groupby("h").mean()
    r["improvement_%"] = 100 * (1 - r["adjusted"] / r["base"])
    return r


if __name__ == "__main__":
    px, earn = load()
    idx = px["^IXIC"].dropna().index
    origins = [d for d in idx[idx >= "2007-01-01"][::63] if idx.get_loc(d) + 126 < len(idx)]
    jobs = [(t, o, k) for k, (t, o) in enumerate((t, o) for o in origins for t in TICKERS)
            if not px[t].loc[:o].dropna().shape[0] < 600]
    print(len(jobs), "cases")
    with ProcessPoolExecutor(os.cpu_count(), initializer=_init) as ex:
        cases = list(ex.map(_run_case, jobs, chunksize=4))

    names = [m.name for m in MODELS]
    train = [c for c in cases if c["origin"] < SPLIT]
    test = [c for c in cases if c["origin"] >= SPLIT]
    tr = table(train, names)
    inv = {nm: 1 / tr.loc[tr.model == nm, [f"CRPS_{h}" for h in H]].to_numpy().mean() ** 2 for nm in names}
    weights = {k: v / sum(inv.values()) for k, v in inv.items()}
    add_ensemble(test, weights, np.random.default_rng(1))
    allnames = names + ["Ensemble"]
    pd.set_option("display.width", 250)
    res = {"weights": weights}
    for label, subset in [("test 2017+, all", test),
                          ("test 2017+, drawdown <= -20%", [c for c in test if c["dd"] <= np.log(0.8)]),
                          ("test 2017+, NVDA only", [c for c in test if c["ticker"] == "NVDA"])]:
        t = table(subset, allnames)
        print(f"\n== {label} (n={len(subset)}) ==")
        print(t.round(3).to_string(index=False))
        res[label] = t.round(4).to_dict(orient="records")
    print("\nweights (fitted pre-2017):", {k: round(v, 3) for k, v in weights.items()})
    _init()
    ea = event_adjustment_test(px, earn, _G["lib"], np.random.default_rng(5))
    print("\nCEO-event drift adjustment, LOO over 22 events (CRPS):\n", ea.round(4))
    res["event_adjustment"] = ea.round(4).reset_index().to_dict(orient="records")
    OUT.mkdir(exist_ok=True)
    json.dump(res, open(OUT / "backtest.json", "w"), indent=2, default=float)
