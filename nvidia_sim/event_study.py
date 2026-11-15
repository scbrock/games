"""Event study: how stocks behaved after abrupt / founder / scandal CEO departures.

Abnormal log return = stock log return - beta * Nasdaq Composite log return,
beta estimated over the 250 trading days ending 10 days before the event.

NVDA's own event: day0 = 2026-11-12 (announced pre-market). The forecast starts at
the close of day 1 (2026-11-13), so the relevant analog quantity is the abnormal
drift from the close of day 1 to day 1 + h.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
H = (21, 63, 126)


def load_prices():
    px = pd.read_csv(HERE / "data" / "prices.csv", index_col=0, parse_dates=True)
    return px


def beta_abnormal(px, ticker, mkt="^IXIC"):
    r = np.log(px[[ticker, mkt]]).diff()
    return r


def run(px=None, events=None):
    px = load_prices() if px is None else px
    ev = pd.read_csv(HERE / "data" / "ceo_events.csv", parse_dates=["day0"]) if events is None else events
    out = []
    for _, e in ev.iterrows():
        r = beta_abnormal(px, e.ticker).dropna()
        i0 = r.index.searchsorted(e.day0)
        if i0 < 260 or r.index[i0] != e.day0:
            print("skip", e.ticker, e.day0.date())
            continue
        est = r.iloc[i0 - 260:i0 - 10]
        beta = np.cov(est.iloc[:, 0], est.iloc[:, 1])[0, 1] / est.iloc[:, 1].var()
        ab = r.iloc[:, 0] - beta * r.iloc[:, 1]
        idio_vol = ab.iloc[i0 - 260:i0 - 10].std() * np.sqrt(252)
        row = {"ticker": e.ticker, "day0": e.day0.date(), "category": e.category, "beta": round(beta, 2),
               "idio_vol": round(idio_vol, 3), "ar_day0": ab.iloc[i0], "ar_day0_1": ab.iloc[i0:i0 + 2].sum()}
        for h in H:
            seg = ab.iloc[i0 + 2:i0 + 2 + h]
            row[f"car_{h}"] = seg.sum() if len(seg) == h else np.nan
            raw = r.iloc[i0 + 2:i0 + 2 + h, 0]
            row[f"raw_{h}"] = raw.sum() if len(raw) == h else np.nan
        out.append(row)
    return pd.DataFrame(out)


if __name__ == "__main__":
    df = run()
    pd.set_option("display.width", 220)
    show = df.copy()
    for c in [c for c in df if c.startswith(("ar_", "car_", "raw_"))]:
        show[c] = (np.expm1(df[c]) * 100).round(1)
    print(show.to_string(index=False))
    print("\nMean / median abnormal drift after day 1 (%), by group:")
    for name, g in [("all", df), *df.groupby("category")]:
        s = {f"car_{h}": f"{100*np.expm1(g[f'car_{h}'].mean()):+.1f} / {100*np.expm1(g[f'car_{h}'].median()):+.1f} (n={g[f'car_{h}'].notna().sum()})" for h in H}
        print(f"{name:8s}", s)
    neg = df[df.ar_day0_1 < -0.03]
    print("\nday0-1 reaction < -3%:", {f"car_{h}": f"{100*np.expm1(neg[f'car_{h}'].mean()):+.1f} mean, hit<0 {np.mean(neg[f'car_{h}']<0):.0%} (n={neg[f'car_{h}'].notna().sum()})" for h in H})
    print("t-stat of mean CAR (all):", {h: round(df[f'car_{h}'].mean() / (df[f'car_{h}'].std() / np.sqrt(df[f'car_{h}'].notna().sum())), 2) for h in H})
    df.to_csv(HERE / "output" / "ceo_event_study.csv", index=False)
