"""Monte Carlo simulation of the Anthropic (ANT) IPO.

Chain, per simulated world:
  1. Market drift until first trade (Nov 16-18, incl. Nvidia earnings Nov 17): Nasdaq move
     with VIX-implied vol + event jump, fat tails. Updates VIX and the 1-month Nasdaq return.
  2. Pricing decision: revision vs. $74 midpoint driven by reported book strength
     (~6x covered, banks weighing > $78) plus partial pass-through of the market move.
  3. First-day return: skill-weighted ensemble of the backtested models.
  4. Post-listing path to 1 year: regime-switching market + idiosyncratic vol + earnings
     jumps + new-issue drift + lock-up expiry dip (backtest-selected parameters).

All inputs are in ASSUMPTIONS; edit and re-run. Sources/caveats are in REPORT.md.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from backtest import load
from models import Ensemble, all_models
from paths import LOCKUP_DAY, RegimeJumpModel

HERE = Path(__file__).parent
OUT = HERE / "output"

ASSUMPTIONS = dict(
    range_low=70.0, range_high=78.0,
    shares_offered_m=825.0,
    shares_basic_bn=13.09,          # S-1/A, Class A+B outstanding post-offer (reported)
    shares_fd_bn=18.6,              # implied by reported $1.30-1.45T fully-diluted at $70-78
    vix_now=20.0,                   # ~19.5 on Nov 10, tech sold off Nov 13
    ndx_1m_now=-5.0,                # Nasdaq in/near correction after Nov 5 (-5.5% day)
    days_to_listing=3,
    nvda_event_sd=0.015,            # extra Nasdaq move sd from Nvidia earnings (Nov 17)
    rev_mean=np.log(80 / 74),       # strong book -> median price ~ $80 (above range)
    rev_sd=0.05,
    rev_market_passthrough=0.8,     # bankers pass most of a pre-pricing market move into price
    rev_floor=np.log(62 / 74), rev_cap=np.log(92 / 74),
    path_model=dict(idio_vol=0.50, abn_drift=-0.10),
    n_sims=40000,
)


def simulate(a=ASSUMPTIONS, seed=2026, first_day_model=None):
    rng = np.random.default_rng(seed)
    n = a["n_sims"]
    mid = (a["range_low"] + a["range_high"]) / 2

    # 1. market until listing
    daily_sd = a["vix_now"] * 1.2 / 100 / np.sqrt(252)
    mkt = (daily_sd * np.sqrt(a["days_to_listing"]) * rng.standard_t(4, n) / np.sqrt(2)
           + a["nvda_event_sd"] * rng.standard_normal(n))
    vix = np.clip(a["vix_now"] * np.exp(-5 * mkt), 10, 60)
    ndx_1m = a["ndx_1m_now"] + 100 * mkt

    # 2. pricing
    rev = a["rev_mean"] + a["rev_market_passthrough"] * mkt + a["rev_sd"] * rng.standard_normal(n)
    rev = np.clip(rev, a["rev_floor"], a["rev_cap"])
    offer = mid * np.exp(rev)
    deal_bn = offer * a["shares_offered_m"] / 1000
    float_pct = 100 * a["shares_offered_m"] / 1000 / a["shares_basic_bn"]

    # 3. first day
    if first_day_model is None:
        bt = json.load(open(OUT / "backtest.json"))
        comps = all_models()
        first_day_model = Ensemble(comps, [bt["ensemble_weights"][m.name] for m in comps])
    first_day_model.fit(load())
    X = pd.DataFrame({"rev": rev, "ln_size": np.log(deal_bn), "float": float_pct,
                      "vix": vix, "ndx_1m": ndx_1m})
    # sample one first-day outcome per world, in chunks for speed
    fd = np.empty(n)
    for s in range(0, n, 2000):
        fd[s:s + 2000] = first_day_model.sample(X.iloc[s:s + 2000], 1, rng)[:, 0]
    close1 = offer * np.exp(fd)

    # 4. post-listing path
    pm = RegimeJumpModel(**a["path_model"])
    path = pm.simulate(n, rng, 252, vix=float(np.median(vix)))
    price_path = close1[:, None] * np.exp(path)

    return dict(mkt=mkt, offer=offer, first_ret=np.expm1(fd), close1=close1,
                lockup=price_path[:, LOCKUP_DAY], y1=price_path[:, -1], path=price_path)


def summarize(r, a=ASSUMPTIONS):
    q = lambda v: {f"p{int(p*100)}": float(np.quantile(v, p)) for p in (0.05, 0.25, 0.5, 0.75, 0.95)}
    fd_basic = r["close1"] * a["shares_basic_bn"] / 1000
    fd_fd = r["close1"] * a["shares_fd_bn"] / 1000
    return {
        "offer_price": q(r["offer"]),
        "P(priced above $78)": float(np.mean(r["offer"] > 78.0001)),
        "P(priced within range)": float(np.mean((r["offer"] >= 70) & (r["offer"] <= 78.0001))),
        "P(priced below $70)": float(np.mean(r["offer"] < 70)),
        "first_day_return_pct": {k: 100 * v for k, v in q(r["first_ret"]).items()},
        "P(breaks issue on day 1)": float(np.mean(r["first_ret"] < 0)),
        "P(day-1 pop > 25%)": float(np.mean(r["first_ret"] > 0.25)),
        "P(day-1 pop > 50%)": float(np.mean(r["first_ret"] > 0.50)),
        "first_close": q(r["close1"]),
        "mcap_basic_close1_$tn": q(fd_basic),
        "mcap_fd_close1_$tn": q(fd_fd),
        "P(close1 mcap >= $1.5T, fully diluted)": float(np.mean(fd_fd >= 1.5)),
        "P(close1 mcap >= $1.5T, basic shares)": float(np.mean(fd_basic >= 1.5)),
        "lockup_price": q(r["lockup"]),
        "P(below offer at lock-up expiry)": float(np.mean(r["lockup"] < r["offer"])),
        "one_year_price": q(r["y1"]),
        "P(below offer at 1y)": float(np.mean(r["y1"] < r["offer"])),
        "P(below $74 midpoint at 1y)": float(np.mean(r["y1"] < 74)),
    }


def sensitivity(a=ASSUMPTIONS):
    """First-day pop under fixed pricing outcomes and market regimes."""
    rows = []
    bt = json.load(open(OUT / "backtest.json"))
    comps = all_models()
    model = Ensemble(comps, [bt["ensemble_weights"][m.name] for m in comps])
    for price in (70, 74, 78, 82, 86):
        for label, vix, ndx in (("calm (VIX 14, NDX +4%)", 14, 4), ("base (VIX 20, NDX -5%)", 20, -5),
                                ("stress (VIX 30, NDX -12%)", 30, -12)):
            b = dict(a, rev_mean=np.log(price / 74), rev_sd=0.0, rev_market_passthrough=0.0,
                     vix_now=vix, ndx_1m_now=ndx, nvda_event_sd=0.0, days_to_listing=0, n_sims=8000)
            r = simulate(b, seed=1, first_day_model=model)
            rows.append({"offer": price, "market": label,
                         "median_day1_%": round(100 * np.median(r["first_ret"]), 1),
                         "P(break)": round(np.mean(r["first_ret"] < 0), 2),
                         "P(>25%)": round(np.mean(r["first_ret"] > 0.25), 2)})
    return pd.DataFrame(rows)


def per_model(a=ASSUMPTIONS):
    rows = []
    for m in all_models():
        r = simulate(dict(a, n_sims=8000), seed=3, first_day_model=m)
        rows.append({"model": m.name, "median_day1_%": round(100 * np.median(r["first_ret"]), 1),
                     "p10_%": round(100 * np.quantile(r["first_ret"], .1), 1),
                     "p90_%": round(100 * np.quantile(r["first_ret"], .9), 1),
                     "P(break)": round(np.mean(r["first_ret"] < 0), 2)})
    return pd.DataFrame(rows)


def plots(r):
    OUT.mkdir(exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    ax[0].hist(r["offer"], bins=60, color="#4C72B0")
    ax[0].axvspan(70, 78, color="grey", alpha=0.15, label="filed range $70-78")
    ax[0].set(title="Final offer price", xlabel="$ / share"); ax[0].legend()
    fr = np.clip(100 * r["first_ret"], -40, 150)
    ax[1].hist(fr, bins=80, color="#DD8452")
    ax[1].axvline(0, color="k", lw=0.8)
    ax[1].set(title="First-day return vs offer", xlabel="%")
    pp = r["path"]; days = np.arange(1, pp.shape[1] + 1)
    for lo, hi, al in ((5, 95, .15), (25, 75, .3)):
        ax[2].fill_between(days, np.percentile(pp, lo, 0), np.percentile(pp, hi, 0), alpha=al, color="#55A868",
                           label=f"{lo}-{hi}th pct")
    ax[2].plot(days, np.median(pp, 0), color="#55A868", label="median")
    ax[2].axhline(np.median(r["offer"]), color="k", ls="--", lw=0.8, label="median offer")
    ax[2].axvline(LOCKUP_DAY, color="r", ls=":", lw=0.8, label="lock-up expiry")
    ax[2].set(title="Price path, first year", xlabel="trading days after listing", ylabel="$ / share")
    ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "anthropic_ipo_simulation.png", dpi=130)


if __name__ == "__main__":
    r = simulate()
    s = summarize(r)
    json.dump(s, open(OUT / "simulation_summary.json", "w"), indent=2)
    plots(r)
    pd.set_option("display.width", 200)
    for k, v in s.items():
        print(f"{k:45s}", {kk: round(vv, 3) for kk, vv in v.items()} if isinstance(v, dict) else round(v, 3))
    print("\nPer-model (same simulated pricing/market inputs):")
    pm = per_model(); print(pm.to_string(index=False)); pm.to_csv(OUT / "per_model.csv", index=False)
    print("\nSensitivity grid:")
    sg = sensitivity(); print(sg.to_string(index=False)); sg.to_csv(OUT / "sensitivity.csv", index=False)
