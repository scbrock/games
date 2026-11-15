"""CEO exits under conditions comparable to NVDA's, including companies that later failed.

Selection rules (applied to every candidate, survivors and non-survivors alike):
  1. Exit was abrupt/forced, scandal-driven, or a founder/iconic-leader transition.
  2. Stock was >= 20% below its 52-week high on the exit date.
  3. Large or high-profile sector leader.

Sources: Yahoo Finance for companies still listed; hand-compiled prices (with source and
confidence per row, data/comparable_ceo_events.csv) for delisted / bankrupt companies,
which Yahoo no longer carries. Abnormal return = stock log return - index log return
(beta = 1 for all cases, because daily data is unavailable for the hand-compiled ones).
Returns are measured from the close of day 1 (or the exit-day close for hand data).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent
OFFS = {"1m": 21, "3m": 63, "6m": 126}
CATEGORY_MAP = {  # earlier event_study.py set, re-labelled by cause of exit
    "HPQ 2010-08-09": "personal_conduct", "INTC 2018-06-21": "personal_conduct",
    "MCD 2019-11-04": "personal_conduct", "WYNN 2018-02-07": "personal_conduct",
    "KSS 2025-05-02": "personal_conduct", "BA 2019-12-23": "company_crisis",
    "UNH 2025-05-13": "company_crisis", "GE 2018-10-01": "performance", "DIS 2022-11-21": "performance",
    "SBUX 2024-08-13": "performance", "NKE 2024-09-20": "performance", "INTC 2024-12-02": "performance",
    "MSFT 2013-08-23": "performance",
}


def load_prices(tickers):
    base = pd.read_csv(HERE / "data" / "prices.csv", index_col=0, parse_dates=True)
    extra_f = HERE / "data" / "prices_extra.csv"
    missing = [t for t in tickers if t not in base.columns]
    if extra_f.exists():
        extra = pd.read_csv(extra_f, index_col=0, parse_dates=True)
        missing = [t for t in missing if t not in extra.columns]
    else:
        extra = pd.DataFrame()
    if missing:
        new = yf.download(missing, start="1995-01-01", auto_adjust=True, progress=False)["Close"]
        new = new.to_frame(missing[0]) if isinstance(new, pd.Series) else new
        extra = new if extra.empty else extra.join(new, how="outer")
        extra.to_csv(extra_f)
    return base.join(extra, how="outer")


def yahoo_rows(px, cand):
    out = []
    for _, e in cand.iterrows():
        c = px[e.yahoo].dropna()
        m = px[e["index"]].dropna()
        i0 = c.index.searchsorted(pd.Timestamp(e.day0))
        if i0 >= len(c) or abs((c.index[i0] - pd.Timestamp(e.day0)).days) > 3:
            continue
        hi = c.iloc[max(0, i0 - 252):i0].max()
        dd = c.iloc[i0 - 1] / hi - 1  # before the announcement
        b = i0 + 1
        row = {"company": e.company, "day0": str(c.index[i0].date()), "category": e.category,
               "survived": e.survived, "dd_at_exit": dd, "source": "yahoo",
               "long_run_outcome": e.get("long_run_outcome", "")}
        for k, h in OFFS.items():
            if b + h < len(c):
                d0, d1 = c.index[b], c.index[b + h]
                row[f"raw_{k}"] = np.log(c.iloc[b + h] / c.iloc[b])
                row[f"ab_{k}"] = row[f"raw_{k}"] - np.log(m.asof(d1) / m.asof(d0))
        out.append(row)
    return out


def hand_rows(px, cand):
    out = []
    for _, e in cand.iterrows():
        m = px[e["index"]].dropna()
        d0 = m.index[m.index.searchsorted(pd.Timestamp(e.day0))]
        i = m.index.get_loc(d0)
        row = {"company": e.company, "day0": e.day0, "category": e.category, "survived": e.survived,
               "dd_at_exit": e.dd_at_exit, "source": "hand: " + e.quality, "long_run_outcome": e.long_run_outcome}
        for k, h in OFFS.items():
            row[f"raw_{k}"] = np.log(e[f"px_{k}"] / e.base_px)
            row[f"ab_{k}"] = row[f"raw_{k}"] - np.log(m.iloc[i + h] / m.iloc[i])
        out.append(row)
    return out


def build():
    cand = pd.read_csv(HERE / "data" / "comparable_ceo_events.csv")
    prev = pd.read_csv(HERE / "data" / "ceo_events.csv")
    prev["company"] = prev.ticker + " (" + prev.description.str.split(" ").str[:2].str.join(" ") + ")"
    prev["yahoo"] = prev.ticker
    prev["category"] = [CATEGORY_MAP.get(f"{t} {d}", "founder") for t, d in zip(prev.ticker, prev.day0)]
    prev["survived"], prev["index"], prev["long_run_outcome"] = 1, "^IXIC", ""
    ycand = pd.concat([cand[cand.yahoo.notna()], prev[["company", "yahoo", "day0", "category", "survived", "index", "long_run_outcome"]]])
    px = load_prices(sorted(set(ycand.yahoo)) + ["^GSPC", "^IXIC", "^GDAXI"])
    rows = yahoo_rows(px, ycand) + hand_rows(px, cand[cand.yahoo.isna()])
    df = pd.DataFrame(rows)
    df["comparable"] = df.dd_at_exit <= -0.20
    df["scenario"] = df.apply(scenario, axis=1)
    return df


LEGAL_REGULATORY = {"Volkswagen (Winterkorn)", "BA (Dennis Muilenburg)", "UNH (Andrew Witty)", "Tyco",
                    "Valeant (Pearson)", "Wells Fargo (Stumpf)"}


def scenario(row):
    """Map each case to the NVDA scenario it informs."""
    if row.category == "company_crisis":
        return "S2 legal/regulatory crisis, real business" if row.company in LEGAL_REGULATORY else "S3 solvency failure / fraudulent business"
    return "S1 leadership transition, business intact"


def summarize(df):
    pct = lambda x: 100 * np.expm1(x)
    out = []
    groups = [("ALL comparable (incl. failures)", df[df.comparable]),
              ("comparable, survivors only (= the survivor-biased view)", df[df.comparable & (df.survived == 1)]),
              ("comparable, failed/delisted only", df[df.comparable & (df.survived == 0)]),
              *[(f"comparable, {c}", g) for c, g in df[df.comparable].groupby("category")],
              *[(f"comparable, {c}", g) for c, g in df[df.comparable].groupby("scenario")],
              ("NOT comparable (stock near its high at exit)", df[~df.comparable])]
    for name, g in groups:
        r = {"group": name, "n": len(g)}
        for k in OFFS:
            x = g[f"ab_{k}"].dropna()
            r[f"mean_ab_{k}_%"] = round(100 * np.expm1(x).mean(), 1) if len(x) else np.nan  # arithmetic mean
            r[f"median_ab_{k}_%"] = round(pct(x.median()), 1) if len(x) else np.nan
        r["P(raw 6m <= -50%)"] = round(float((g["raw_6m"] <= np.log(0.5)).mean()), 2)
        r["P(equity eventually wiped out/bankrupt)"] = round(float(g.long_run_outcome.fillna("").str.contains("wiped|Chapter 11|Insolvency|Seized").mean()), 2)
        out.append(r)
    return pd.DataFrame(out)


if __name__ == "__main__":
    df = build()
    s = summarize(df)
    pd.set_option("display.width", 260)
    show = df.copy()
    for c in [c for c in df if c.startswith(("raw_", "ab_"))] + ["dd_at_exit"]:
        show[c] = (100 * (np.expm1(df[c]) if c != "dd_at_exit" else df[c])).round(1)
    print(show[["company", "day0", "category", "survived", "dd_at_exit", "comparable", "ab_1m", "ab_3m", "ab_6m", "raw_6m"]]
          .sort_values(["comparable", "category"], ascending=[False, True]).to_string(index=False))
    print()
    print(s.to_string(index=False))
    (HERE / "output").mkdir(exist_ok=True)
    df.to_csv(HERE / "output" / "comparable_ceo_events.csv", index=False)
    s.to_csv(HERE / "output" / "comparable_ceo_summary.csv", index=False)
