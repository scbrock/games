"""Live NVDA forecast from the 2026-11-13 close.

1. Quant models (backtested) -> skill-weighted ensemble, with the CEO-departure drift
   adjustment applied only where the LOO test showed it helps (1-month, tapered to 0 at 3m).
2. Options-implied (risk-neutral) distribution from the NVDA chain (Breeden-Litzenberger).
3. Historical analog episodes: NVDA's own 30% drawdowns, and mega-cap tech stocks that
   fell >= 25% from a 52-week high within 30 trading days.
4. Earnings-day (Nov 18 reaction) distribution: NVDA history vs options straddle.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline
from scipy.optimize import brentq
from scipy.stats import norm

import event_study
from backtest import UNIVERSE, load, make_context
from models import (BlockBootstrap, Ensemble, FactorRegimeJump, GJRGarch, StateAnalogs,
                    build_library, reaction_days)

HERE = Path(__file__).parent
OUT = HERE / "output"
RATE = 0.04  # risk-free assumption for option maths
ATH = 239.24  # 2026 closing high (Oct 6)
NYSE_HOLIDAYS = pd.to_datetime(["2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15",
                                "2027-03-26", "2027-05-31", "2027-06-18"])
EXPIRIES = ["2026-12-18", "2027-02-19", "2027-05-21"]  # ~1, 3, 6 months
N = 40000


def trading_days(start, end):
    d = pd.bdate_range(start + pd.Timedelta(days=1), end)
    return d[~d.isin(NYSE_HOLIDAYS)]


# ------------------------------------------------------------------ options
def bs_price(S, K, T, sigma, call):
    d1 = (np.log(S / K) + (RATE + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if call:
        return S * norm.cdf(d1) - K * np.exp(-RATE * T) * norm.cdf(d2)
    return K * np.exp(-RATE * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def implied_dist(opts, expiry, spot, asof, n, rng):
    """Risk-neutral terminal-price samples via a smoothed OTM IV smile + Breeden-Litzenberger."""
    T = (pd.Timestamp(expiry) - pd.Timestamp(asof)).days / 365
    o = opts[(opts.expiry == expiry) & (opts.bid > 0) & (opts.ask > opts.bid)].copy()
    o["mid"] = (o.bid + o.ask) / 2
    o = o[((o.type == "put") & (o.strike < spot)) | ((o.type == "call") & (o.strike >= spot))]
    o = o[(o.strike > 0.3 * spot) & (o.strike < 2.5 * spot)]
    ivs = []
    for _, r in o.iterrows():
        f = lambda s: bs_price(spot, r.strike, T, s, r.type == "call") - r.mid
        try:
            ivs.append(brentq(f, 0.05, 4.0))
        except ValueError:
            ivs.append(np.nan)
    o["iv"] = ivs
    o = o.dropna(subset=["iv"]).sort_values("strike")
    k = np.log(o.strike / spot).to_numpy()
    sp = UnivariateSpline(k, o.iv.to_numpy(), k=3, s=len(k) * 0.0004)
    K = np.linspace(0.02 * spot, 3.5 * spot, 6000)
    kk = np.clip(np.log(K / spot), k.min(), k.max())  # flat extrapolation of the smile
    C = bs_price(spot, K, T, np.maximum(sp(kk), 0.05), True)
    dens = np.exp(RATE * T) * np.gradient(np.gradient(C, K), K)
    dens = np.clip(dens, 0, None)
    dens[:5] = dens[-5:] = 0  # finite-difference edge artifacts
    cdf = np.cumsum(dens)
    cdf /= cdf[-1]
    atm = float(sp(0.0))
    return np.interp(rng.random(n), cdf, K), atm, T


# ------------------------------------------------------------------ analogs
def drawdown_episodes(px, tickers, thresh=-0.25, max_days_from_high=30, gap=126):
    rows = []
    for t in tickers:
        c = px[t].dropna()
        hi = c.rolling(252, min_periods=200).max()
        dd = c / hi - 1
        days_since_high = c.groupby((c == hi).cumsum()).cumcount()
        last = -10**9
        for i in range(260, len(c)):
            if dd.iloc[i] <= thresh and days_since_high.iloc[i] <= max_days_from_high and i - last > gap:
                last = i
                row = {"ticker": t, "date": c.index[i].date(), "drawdown_%": round(100 * dd.iloc[i], 1)}
                for h, lab in ((21, "1m"), (63, "3m"), (126, "6m")):
                    row[f"fwd_{lab}_%"] = round(100 * (c.iloc[i + h] / c.iloc[i] - 1), 1) if i + h < len(c) else np.nan
                rows.append(row)
    return pd.DataFrame(rows)


SCENARIO_WEIGHTS = {  # judgment, edit freely: see REPORT.md section 6
    "S1 leadership transition, business intact": 0.70,
    "S2 legal/regulatory crisis, real business": 0.27,
    "S3 solvency failure / fraudulent business": 0.03,
}
H_LABEL = {24: "1m", 65: "3m", 129: "6m"}


def scenario_mixture(ens, px, horizons, n, rng, weights=None):
    """NVDA outcome as a mixture over what kind of CEO exit this turns out to be.

    S1: backtested ensemble + 50%-shrunk median abnormal drift of comparable S1 exits.
    S2/S3: NVDA beta x bootstrapped Nasdaq h-day return + an abnormal return drawn from the
           comparable S2/S3 cases (including companies that failed), with kernel jitter.
    """
    import comparable_events as ce
    weights = weights or SCENARIO_WEIGHTS
    cmp_ = ce.build()
    cmp_ = cmp_[cmp_.comparable]
    lr = np.log(px[["NVDA", "^IXIC"]].dropna()).diff().dropna().iloc[-250:]
    beta = np.cov(lr["NVDA"], lr["^IXIC"])[0, 1] / lr["^IXIC"].var()
    lc = np.log(px["^IXIC"].dropna())
    out, comp = {}, {}
    for h in horizons:
        k = H_LABEL[h]
        mkt_h = (lc.shift(-h) - lc).dropna().to_numpy()
        counts = rng.multinomial(n, [weights[s] for s in weights])
        parts = []
        for (sc, w), c in zip(weights.items(), counts):
            ab = cmp_.loc[cmp_.scenario == sc, f"ab_{k}"].dropna().to_numpy()
            if sc.startswith("S1"):
                x = rng.choice(ens[h], c) + 0.5 * np.median(ab)
            else:
                x = beta * rng.choice(mkt_h, c) + rng.choice(ab, c) + rng.normal(0, 0.08 * np.sqrt(h / 63), c)
            comp.setdefault(sc, {})[h] = x
            parts.append(x)
        out[h] = rng.permutation(np.concatenate(parts))
    return out, comp, beta


def q(x, spot):
    p = spot * np.exp(x)
    return {"p5": np.quantile(p, .05), "p25": np.quantile(p, .25), "median": np.median(p),
            "p75": np.quantile(p, .75), "p95": np.quantile(p, .95),
            "P(<150)": np.mean(p < 150), "P(<130)": np.mean(p < 130), "P(>200)": np.mean(p > 200),
            "P(>ATH 239)": np.mean(p > ATH), "P(up)": np.mean(p > spot), "P(<100)": np.mean(p < 100),
            "P(<=-50%)": np.mean(p <= spot / 2)}


def main():
    rng = np.random.default_rng(11)
    px, earn = load()
    opts = pd.read_csv(HERE / "data" / "nvda_options.csv")
    spot, asof = float(opts["spot"].iloc[0]), pd.Timestamp(opts["asof"].iloc[0])
    origin = px["NVDA"].dropna().index[-1]
    assert origin == asof

    cal = trading_days(origin, pd.Timestamp("2027-07-01"))
    horizons = tuple(int(cal.get_loc(cal[cal <= pd.Timestamp(e)][-1])) + 1 for e in EXPIRIES)
    # upcoming earnings reactions: Nov 18 2026 (reported Nov 17 after close), late Feb 2027, late May 2027
    earn_fut = [int(cal.get_loc(d)) + 1 for d in pd.to_datetime(["2026-11-18", "2027-02-25", "2027-05-27"])]
    lib = build_library(px, px["^VIX"], UNIVERSE, horizons)
    ctx = make_context(px, earn, lib, "NVDA", origin, horizons, earn_future_override=earn_fut)

    bt = json.load(open(OUT / "backtest.json"))
    models = [BlockBootstrap(), GJRGarch(), FactorRegimeJump(), StateAnalogs()]
    w = [bt["weights"][m.name] for m in models]

    ev = event_study.run(px)
    car21 = ev["car_21"].mean()
    taper = {h: 0.5 * car21 * max(0.0, 1 - (h - 21) / 42) if h > 21 else 0.5 * car21 for h in horizons}

    res, samples = {}, {}
    for m in models:
        samples[m.name] = m.forecast(ctx, horizons, N, rng)
    ens = Ensemble(models, w).forecast(ctx, horizons, N, rng)
    samples["Ensemble (no event adj.)"] = ens
    samples["Ensemble + CEO-exit adj."] = {h: ens[h] + taper[h] for h in horizons}
    mix, comp, beta = scenario_mixture(ens, px, horizons, N, rng)
    samples["Scenario mix (incl. failed-company analogs)"] = mix
    for sc, d in comp.items():
        samples[f"  only {sc}"] = d
    sens = []
    for w2, w3 in ((0.10, 0.0), (0.10, 0.03), (0.27, 0.03), (0.27, 0.10), (0.50, 0.03), (0.50, 0.10)):
        w = {"S1 leadership transition, business intact": 1 - w2 - w3,
             "S2 legal/regulatory crisis, real business": w2, "S3 solvency failure / fraudulent business": w3}
        m, _, _ = scenario_mixture(ens, px, horizons, 20000, rng, w)
        h = horizons[-1]
        sens.append({"w_S2": w2, "w_S3": w3, **{k: round(v, 3) for k, v in q(m[h], spot).items()
                                                 if k in ("median", "p5", "P(<130)", "P(<100)", "P(<=-50%)", "P(>ATH 239)")}})
    res["scenario_sensitivity_6m"] = sens
    res["nvda_beta_nasdaq"] = round(float(beta), 2)
    for e, h in zip(EXPIRIES, horizons):
        s, atm, T = implied_dist(opts, e, spot, asof, N, rng)
        samples.setdefault("Options-implied (risk-neutral)", {})[h] = np.log(s / spot)
        res.setdefault("atm_iv", {})[e] = round(atm, 3)

    rows = []
    for name, d in samples.items():
        for e, h in zip(EXPIRIES, horizons):
            rows.append({"model": name, "expiry": e, "days": h, **{k: round(v, 3) for k, v in q(d[h], spot).items()}})
    table = pd.DataFrame(rows)

    # earnings day: NVDA historical reaction-day returns vs options straddle for Nov 20 expiry
    c = px["NVDA"].dropna()
    rd = reaction_days(earn.loc[earn.ticker == "NVDA", "ts"], c.index)
    lr = np.log(c).diff()
    moves = lr.reindex([d for d in rd if d <= origin]).dropna()
    o20 = opts[(opts.expiry == "2026-11-20")]
    kk = o20.strike.iloc[(o20.strike - spot).abs().argsort().iloc[0]]
    straddle = ((o20[o20.strike == kk].bid + o20[o20.strike == kk].ask) / 2).sum()
    res["earnings"] = {
        "hist_mean_abs_move_all_%": round(100 * moves.abs().mean(), 2),
        "hist_mean_abs_move_last12_%": round(100 * moves.iloc[-12:].abs().mean(), 2),
        "hist_P(down)_last24": round(float(np.mean(moves.iloc[-24:] < 0)), 2),
        "straddle_Nov20_%_of_spot": round(100 * straddle / spot, 2),
        "straddle_strike": float(kk),
    }

    nv = drawdown_episodes(px, ["NVDA"], thresh=-0.30, max_days_from_high=40)
    mega = drawdown_episodes(px, UNIVERSE + ["VIAV"], thresh=-0.25, max_days_from_high=30)  # VIAV = JDS Uniphase history
    res["horizons"] = dict(zip(EXPIRIES, horizons))
    res["ceo_adjustment_log"] = {h: round(v, 4) for h, v in taper.items()}
    res["mega_episode_summary"] = {
        lab: {"median_%": float(mega[f"fwd_{lab}_%"].median()), "P(up)": float((mega[f"fwd_{lab}_%"] > 0).mean()),
              "p10_%": float(mega[f"fwd_{lab}_%"].quantile(.1)), "p90_%": float(mega[f"fwd_{lab}_%"].quantile(.9)),
              "n": int(mega[f"fwd_{lab}_%"].notna().sum())} for lab in ("1m", "3m", "6m")}
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / "nvda_forecast_table.csv", index=False)
    nv.to_csv(OUT / "nvda_drawdown_episodes.csv", index=False)
    mega.to_csv(OUT / "megacap_drawdown_episodes.csv", index=False)
    json.dump(res, open(OUT / "nvda_forecast_summary.json", "w"), indent=2, default=float)

    pd.set_option("display.width", 250)
    print(table.to_string(index=False))
    print(json.dumps(res, indent=1, default=float))
    print("\nNVDA own >=30% fast drawdowns:\n", nv.to_string(index=False))
    print(f"\nMega-cap fast >=25% drawdowns: n={len(mega)}")

    # ---- charts
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.4))
    show = ["Ensemble + CEO-exit adj.", "Scenario mix (incl. failed-company analogs)", "Options-implied (risk-neutral)"]
    cols = ["#4C72B0", "#DD8452", "#C44E52"]
    for a, e, h in zip(ax, EXPIRIES, horizons):
        bins = np.linspace(40, 360, 140)
        for nm, col in zip(show, cols):
            a.hist(spot * np.exp(samples[nm][h]), bins=bins, density=True, histtype="step", lw=1.6, color=col,
                   label=nm)
        a.axvline(spot, color="k", lw=0.8, ls="--")
        a.axvline(ATH, color="grey", lw=0.8, ls=":")
        a.set(title=f"NVDA on {e} ({h} trading days)", xlabel="$ / share", yticks=[])
    ax[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "nvda_forecast_distributions.png", dpi=130)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    for _, r in nv.dropna(subset=["fwd_1m_%"]).iterrows():
        i = c.index.get_loc(pd.Timestamp(r["date"]))
        seg = c.iloc[i - 30:i + 127] / c.iloc[i]
        ax.plot(np.arange(-30, -30 + len(seg)), seg.values, lw=1, alpha=0.8, label=str(r["date"]))
    i = len(c) - 1
    ax.plot(np.arange(-30, 1), (c.iloc[i - 30:] / c.iloc[i]).values, color="k", lw=2.5, label="now (2026-11-13)")
    ax.axhline(1, color="k", lw=0.5); ax.axvline(0, color="k", lw=0.5)
    ax.set(title="NVDA after past fast 30% drawdowns (indexed to the day it crossed -30%)",
           xlabel="trading days", ylabel="price / price on crossing day")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "nvda_drawdown_analogs.png", dpi=130)


if __name__ == "__main__":
    main()
