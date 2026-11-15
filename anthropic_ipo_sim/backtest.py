"""Backtest first-day and post-listing models on historical IPOs.

First-day models: leave-one-out (LOO) and chronological walk-forward (train only on
IPOs that happened earlier). Post-listing models: probability-integral-transform (PIT)
calibration against approximate 1-year returns from the first-day close.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from models import Ensemble, all_models, features, target
from paths import ConstantVolGBM, RegimeJumpModel, TD

HERE = Path(__file__).parent
OUT = HERE / "output"
N = 4000
PATH_VARIANTS = [ConstantVolGBM(vol=0.40), ConstantVolGBM(vol=0.80), RegimeJumpModel(),
                 RegimeJumpModel(idio_vol=0.50, abn_drift=-0.10),
                 RegimeJumpModel(idio_vol=0.70, abn_drift=-0.10)]


def load():
    df = pd.read_csv(HERE / "data" / "historical_ipos.csv", parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


_RNG = np.random.default_rng(0)


def crps(samples, y):
    """Sample-based continuous ranked probability score: E|X-y| - 0.5 E|X-X'| (lower is better)."""
    s = np.asarray(samples)
    return np.mean(np.abs(s - y)) - 0.5 * np.mean(np.abs(s - _RNG.permutation(s)))


def score(preds, ys):
    """preds: list of sample arrays (log returns); ys: realised log returns."""
    pct = lambda v: np.expm1(v) * 100
    med = np.array([np.median(p) for p in preds])
    lo = np.array([np.quantile(p, 0.10) for p in preds])
    hi = np.array([np.quantile(p, 0.90) for p in preds])
    ys = np.asarray(ys)
    return {
        "MAE_pts": float(np.mean(np.abs(pct(med) - pct(ys)))),
        "MedAE_pts": float(np.median(np.abs(pct(med) - pct(ys)))),
        "CRPS": float(np.mean([crps(p, y) for p, y in zip(preds, ys)])),
        "cover80": float(np.mean((ys >= lo) & (ys <= hi))),
        "rank_corr": float(pd.Series(med).corr(pd.Series(ys), method="spearman")),
        "hit_big_pop": float(np.mean((med > np.log(1.15)) == (ys > np.log(1.15)))),
    }


def run_first_day(df, ensemble_weights=None):
    rng = np.random.default_rng(42)
    X, y = features(df), target(df)
    makers = {m.name: (lambda m=m: type(m)()) for m in all_models()}
    if ensemble_weights is not None:
        makers["Skill-weighted ensemble"] = lambda: Ensemble(
            [type(m)() for m in all_models()], ensemble_weights)
    res = {}
    for name, make in makers.items():
        loo, wf, wf_y, loo_pred = [], [], [], []
        for i in range(len(df)):
            train = df.drop(index=i)
            p = make().fit(train).sample(X.iloc[[i]], N, rng)[0]
            loo.append(p)
            loo_pred.append(float(np.median(p)))
            if i >= 15:  # walk-forward: only earlier deals
                wf.append(make().fit(df.iloc[:i]).sample(X.iloc[[i]], N, rng)[0])
                wf_y.append(y[i])
        res[name] = {"LOO": score(loo, y), "WalkForward": score(wf, wf_y),
                     "loo_median_pct": [float(np.expm1(v) * 100) for v in loo_pred]}
    return res


def run_paths(df):
    """PIT calibration of 1-year paths vs history (only rows with ret_1y_from_close)."""
    rng = np.random.default_rng(7)
    h = df.dropna(subset=["ret_1y_from_close"])
    ys = np.log1p(h["ret_1y_from_close"].to_numpy())
    out = {}
    mega = (h["deal_bn"] >= 5).to_numpy()
    for model in PATH_VARIANTS:
        label = f"{model.name} ({'vol=%.2f' % model.vol if hasattr(model, 'vol') else 'idio=%.2f, drift=%.2f' % (model.idio_vol, model.abn_drift)})"
        pits, preds = [], []
        for vix, yv in zip(h["vix"], ys):
            end = model.simulate(3000, rng, TD, vix=vix)[:, -1]
            pits.append(float(np.mean(end <= yv)))
            preds.append(end)
        pits = np.array(pits)
        out[label] = {
            "n": int(len(ys)),
            "cover50": float(np.mean((pits > 0.25) & (pits < 0.75))),
            "cover80": float(np.mean((pits > 0.10) & (pits < 0.90))),
            "mean_PIT": float(pits.mean()),  # 0.5 = unbiased
            "CRPS": float(np.mean([crps(p, y) for p, y in zip(preds, ys)])),
            "mega_cover80": float(np.mean((pits[mega] > 0.10) & (pits[mega] < 0.90))),
            "mega_mean_PIT": float(pits[mega].mean()),
        }
    out["_historical"] = {"median_1y_pct": float(np.median(np.expm1(ys)) * 100),
                          "sd_log": float(np.std(ys))}
    return out


if __name__ == "__main__":
    df = load()
    first = run_first_day(df)
    names = [m.name for m in all_models()]
    w = np.array([1 / first[n]["WalkForward"]["CRPS"] for n in names]) ** 2
    first = run_first_day(df, ensemble_weights=w)
    paths = run_paths(df)
    OUT.mkdir(exist_ok=True)
    json.dump({"first_day": first, "paths": paths, "ensemble_weights": dict(zip(names, (w / w.sum()).round(3).tolist()))},
              open(OUT / "backtest.json", "w"), indent=2)
    rows = [{"model": k, **{f"LOO_{a}": b for a, b in v["LOO"].items()},
             **{f"WF_{a}": b for a, b in v["WalkForward"].items()}} for k, v in first.items()]
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print()
    print(pd.DataFrame(paths).T.round(3).to_string())
    print("ensemble weights:", dict(zip(names, (w / w.sum()).round(3))))
