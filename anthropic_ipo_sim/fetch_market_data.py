"""Replace hand-compiled market fields with Yahoo Finance data (via yfinance).

For each IPO with a live ticker:
  vix        VIX close on the last trading day before first trade (pricing night)
  ndx_1m     Nasdaq Composite % change over the 21 trading days ending that day
  ret_1y_from_close  close ~252 trading days after listing / first-day close - 1
  check      Yahoo first-day close vs. the hand-entered close (split ratio shown)
Delisted names (Netscape, LinkedIn, Zynga, Twitter, Didi) keep their hand-entered values.
Writes data/historical_ipos.csv in place (original kept as data/historical_ipos_manual.csv)
and output/market_now.json with current VIX / Nasdaq 1-month for the Anthropic inputs.
"""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent
CSV = HERE / "data" / "historical_ipos.csv"
MANUAL = HERE / "data" / "historical_ipos_manual.csv"

TICKERS = {
    "Amazon": "AMZN", "Nvidia": "NVDA", "Google": "GOOGL", "Visa": "V", "GM": "GM",
    "Groupon": "GRPN", "Facebook": "META", "JD.com": "JD", "Alibaba": "BABA", "Shopify": "SHOP",
    "Square": "XYZ", "Snap": "SNAP", "Dropbox": "DBX", "Lyft": "LYFT", "Zoom": "ZM",
    "Pinterest": "PINS", "Uber": "UBER", "Peloton": "PTON", "Snowflake": "SNOW", "Unity": "U",
    "DoorDash": "DASH", "Airbnb": "ABNB", "Affirm": "AFRM", "Bumble": "BMBL", "Coupang": "CPNG",
    "Robinhood": "HOOD", "Rivian": "RIVN", "Arm": "ARM", "Instacart": "CART", "Klaviyo": "KVYO",
    "Reddit": "RDDT", "Astera Labs": "ALAB", "Rubrik": "RBRK", "CoreWeave": "CRWV", "Chime": "CHYM",
    "Circle": "CRCL", "Figma": "FIG", "Klarna": "KLAR", "Cerebras": "CBRS", "SpaceX": "SPCX",
}


def close_series(sym, start, end):
    d = yf.download(sym, start=start, end=end, progress=False, auto_adjust=False)
    if d.empty:
        return pd.Series(dtype=float)
    c = d["Close"]
    return (c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c).dropna()


def main():
    if not MANUAL.exists():
        shutil.copy(CSV, MANUAL)
    df = pd.read_csv(MANUAL, parse_dates=["date"])
    df[["vix", "ndx_1m", "ret_1y_from_close"]] = df[["vix", "ndx_1m", "ret_1y_from_close"]].astype(float)
    df["notes"] = df["notes"].astype(object)
    vix = close_series("^VIX", "1990-01-01", None)
    ndx = close_series("^IXIC", "1990-01-01", None)
    log = []
    for i, r in df.iterrows():
        prev = vix.index[vix.index < r["date"]][-1]
        df.at[i, "vix"] = round(float(vix[prev]), 1)
        k = ndx.index.get_loc(ndx.index[ndx.index < r["date"]][-1])
        df.at[i, "ndx_1m"] = round(100 * (ndx.iloc[k] / ndx.iloc[k - 21] - 1), 1)
        src = "market:yahoo"
        sym = TICKERS.get(r["company"])
        if sym:
            px = close_series(sym, r["date"] - pd.Timedelta(days=3), r["date"] + pd.Timedelta(days=400))
            px = px[px.index >= r["date"]]
            if len(px) and abs((px.index[0] - r["date"]).days) <= 3:
                split = r["first_close"] / px.iloc[0]
                log.append(f"{r['company']:12s} {sym:6s} yahoo day1 {px.iloc[0]:9.2f}  manual {r['first_close']:8.2f}  ratio {split:6.2f}")
                if len(px) > 252:
                    df.at[i, "ret_1y_from_close"] = round(float(px.iloc[252] / px.iloc[0] - 1), 3)
                    src += "+1y:yahoo"
                else:
                    df.at[i, "ret_1y_from_close"] = np.nan  # less than a year of trading
            else:
                log.append(f"{r['company']:12s} {sym:6s} no data near IPO date")
        df.at[i, "notes"] = (str(r["notes"]) + "; " if pd.notna(r["notes"]) else "") + src
    df.to_csv(CSV, index=False, date_format="%Y-%m-%d")
    print("\n".join(log))

    k = len(ndx) - 1
    now = {"date": str(ndx.index[-1].date()), "vix": round(float(vix.iloc[-1]), 2),
           "ndx_1m": round(100 * (ndx.iloc[k] / ndx.iloc[k - 21] - 1), 2),
           "ndx_drawdown_from_52w_high": round(100 * (ndx.iloc[-1] / ndx.iloc[-252:].max() - 1), 2)}
    (HERE / "output").mkdir(exist_ok=True)
    json.dump(now, open(HERE / "output" / "market_now.json", "w"), indent=2)
    print("market now:", now)


if __name__ == "__main__":
    main()
