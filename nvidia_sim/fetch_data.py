"""Download everything the NVDA simulation needs from Yahoo Finance (yfinance).

data/prices.csv          daily split/dividend-adjusted closes, universe + ^IXIC + ^VIX
data/earnings_dates.csv  historical earnings announcement timestamps per ticker
data/nvda_options.csv    current NVDA option chain (all expiries <= ~8 months)
"""
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).parent
DATA = HERE / "data"

UNIVERSE = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "CSCO", "INTC", "ORCL", "AMD",
            "AVGO", "TSM", "QCOM", "TSLA", "IBM", "TXN", "ADBE", "NFLX", "MU", "ASML", "CRM"]
# CEO-event tickers not already in the universe
EVENT_EXTRA = ["HPQ", "MCD", "BA", "WYNN", "DIS", "SBUX", "NKE", "KSS", "UNH", "GE",
               "VIAV"]  # VIAV carries JDS Uniphase (dot-com casualty) history
INDEX = ["^IXIC", "^VIX", "^GSPC"]
EARNINGS_FOR = ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD", "AVGO", "INTC", "CSCO", "ORCL", "QCOM", "MU"]


def main():
    DATA.mkdir(exist_ok=True)
    px = yf.download(UNIVERSE + EVENT_EXTRA + INDEX, start="1995-01-01", auto_adjust=True,
                     progress=False)["Close"]
    px.to_csv(DATA / "prices.csv")
    print("prices", px.shape, px.index[-1].date())

    rows = []
    for s in EARNINGS_FOR:
        try:
            e = yf.Ticker(s).get_earnings_dates(limit=100)
            for ts in e.index:
                rows.append({"ticker": s, "ts": ts.tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M")})
        except Exception as ex:  # noqa: BLE001
            print("earnings fail", s, ex)
    pd.DataFrame(rows).to_csv(DATA / "earnings_dates.csv", index=False)
    print("earnings rows", len(rows))

    t = yf.Ticker("NVDA")
    spot = float(px["NVDA"].dropna().iloc[-1])
    chains = []
    for exp in t.options:
        if pd.Timestamp(exp) > px.index[-1] + pd.Timedelta(days=250):
            break
        oc = t.option_chain(exp)
        for kind, df in (("call", oc.calls), ("put", oc.puts)):
            d = df[["strike", "bid", "ask", "lastPrice", "impliedVolatility", "openInterest", "volume"]].copy()
            d["type"], d["expiry"] = kind, exp
            chains.append(d)
    oc = pd.concat(chains)
    oc["spot"] = spot
    oc["asof"] = str(px.index[-1].date())
    oc.to_csv(DATA / "nvda_options.csv", index=False)
    print("options rows", len(oc), "expiries", oc.expiry.nunique())


if __name__ == "__main__":
    main()
