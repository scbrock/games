# NVDA: return simulation after the Huang resignation

*As of the 13 Nov 2026 close ($162.85). This is a research exercise, not investment advice. All prices, earnings dates and options data come from Yahoo Finance via yfinance.*

## 1. Situation

| | |
|---|---|
| **CEO exit** | Jensen Huang resigned on 12 Nov as president, CEO and director, effective immediately. Coverage cites a personal scandal, and Congress has asked him to testify. CFO Colette Kress is interim CEO. The FT reports Arm's Rene Haas has been approached. NVDA closed −4.3% that day after falling as much as −14% intraday ([CNBC](https://www.cnbc.com/2026/11/12/nvidia-nvda-jensen-huang-second-affair.html), [CNN](https://www.cnn.com/2026/11/11/business/live-news/nvidia-jensen-huang-investigation-fallout), [Yahoo](https://finance.yahoo.com/markets/stocks/articles/nvidia-jensen-huang-resigns-ceo-140115697.html)) |
| **Price state** | $162.85, −32% from the $239.24 close on 6 Oct. Nasdaq −5.9% over one month after the 5 Nov AI selloff (−5.5% day) ([Open](https://openthemagazine.com/technology/quick-take-why-did-the-nasdaq-fall-55-seven-things-to-know-about-wall-streets-ai-sell-off)) |
| **Earnings** | FQ3 results due 17 Nov after the close. Guide ~$108bn, consensus ~$109bn and EPS $2.47. Q4 guidance will be the "first test of the post-Huang era" ([StoneX](https://www.stonex.com/en-gb/news-and-analysis/nvidia-earnings-preview-nvda-s-first-test-of-the-post-jenson-huang-era/), [Benzinga](https://www.benzinga.com/opinion/26/11/63240720/options-traders-expect-nvidia-biggest-earnings-move-since-2024)) |
| **Options** | ATM IV is 58% (Dec), 50% (Feb) and 47% (May). The Nov-20 straddle is 9.6% of spot and covers 5 sessions. Report-day-only estimates are ~6–7% ([Equibles](https://equibles.com/research/nvidia-nvda-earnings-implied-move-options-price-about-6-to-7-for-the-report-itself)) |
| **NVDA earnings history** | Mean absolute reaction is 7.7% (2002–26) and 5.5% over the last 12 reports. 46% of the last 24 reactions were down |

## 2. "Has this happened before?" Three sets of analogs

**a) CEO departures** (`event_study.py`, 22 events from 2000–2025: founder exits such as Jobs, Gates, Bezos, Ellison and Page/Brin; scandal exits such as Hurd, Krzanich, Easterbrook and Wynn; and abrupt firings such as Muilenburg, Chapek, Gelsinger and Witty). The table shows the abnormal return versus the Nasdaq, adjusted for beta, measured from the close of day 1, which is where NVDA is now.

| | +1 month | +3 months | +6 months |
|---|---|---|---|
| All 22: mean / median | **−4.5% / −4.6%** (t = −3.2) | −5.7% / −2.5% (t = −1.7) | −6.4% / −6.1% (t = −1.3) |
| Scandal exits (n=5) | −0.6% | +5.3% | +5.6% |
| Abrupt firings (n=8) | −5.6% | −11.8% | −14.6% |

The leadership overhang is real in the first month and fades statistically after that.

**a2) Comparable exits, *including companies that failed*** (`comparable_events.py`). Survivorship bias matters here because Yahoo has no data for delisted companies. The non-survivors were therefore hand-compiled from news reports, with the source and confidence level recorded for each row (`data/comparable_ceo_events.csv`). The terminal outcomes (bankruptcy, seizure, rescue price) are certain; interim prices are approximate.

Selection rules, applied to every candidate:
1. The exit was abrupt, forced, scandal-driven, or a founder transition.
2. The stock was at least 20% below its 52-week high at exit.
3. The company was a large or high-profile leader in its sector.

That gives 29 comparable cases, 12 of which no longer trade (Enron, WorldCom, Lucent, Nortel, Merrill, Bear Stearns, WaMu, Wirecard, Nikola, Lordstown, Twitter, Bed Bath & Beyond). Abnormal returns are versus the index with beta = 1, measured from day 1.

| Group | n | Median abnormal return 1m / 3m / 6m | P(raw 6m ≤ −50%) | Equity eventually wiped out |
|---|---|---|---|---|
| **All comparable, including failures** | 29 | −8% / −17% / **−23%** | **38%** | **28%** |
| Survivors only (the biased view) | 17 | −7% / −13% / −14% | 18% | 0% |
| S1 leadership transition, business intact | 13 | −8% / −10% / −14% | 31% | 8% |
| S2 legal/regulatory crisis, real business (VW, Boeing, UNH, Tyco, Valeant) | 5 | −7% / −22% / −9% | 0% | 0% |
| S3 solvency failure / fraudulent business (Enron, WorldCom, Wirecard, Nikola, 2008 banks…) | 11 | −15% / −75% / −88% | 64% | 73% |
| *Not* comparable: stock near its high at exit | 15 | −3% / −2% / −6% | 0% | 0% |

Two things stand out. First, dropping the failures **understates the 6-month damage by about 9 points and halves the crash probability**. Second, the *cause* of the exit dominates the outcome. CEO exits from stocks that were already falling did much worse than exits near a high, which is the NVDA situation.

**Which scenario is NVDA?** Reporting since 8 Nov ties Huang's exit to affairs *and* to a relationship with an alleged Chinese intelligence operative linked to Megaspeed, an Nvidia customer accused of channelling restricted chips to China. The board hired Wachtell Lipton, Nvidia is reviewing its export-control compliance, and Congress is probing ([CNBC](https://www.cnbc.com/2026/11/08/nvidia-jensen-huang-investigation-china-spy.html), [Al Jazeera](https://www.aljazeera.com/news/2026/11/12/why-did-nvidia-ceo-jensen-huang-resign-and-who-is-colette-kress), [Wikipedia](https://en.wikipedia.org/wiki/Jensen_Huang_spying_scandal)). Huang denies compromising national security, and no proof has been presented. That makes S2 a live possibility. S3, solvency failure or a fake business, is implausible for a company with Nvidia's cash flow, but it is kept as a small tail weight for unknown unknowns.

**b) NVDA's own fast drops of 30%** (8 prior episodes). The 6-month outcomes ranged from −75% (2002) to +128% (2020): 4 were up and 4 were down. The 2018 and 2022 episodes, which were also post-boom cool-downs, went down another 10–20%. See `output/nvda_drawdown_analogs.png`.

**c) Mega-cap tech stocks falling 25% or more from a 52-week high within 30 trading days** (96 episodes, 22 stocks, 1996–2026; now includes JDS Uniphase via VIAV's history):

| | 1 month | 3 months | 6 months |
|---|---|---|---|
| Median forward return | +5.6% | +12.0% | +20.3% |
| P(up) | 59% | 66% | 60% |
| 10th / 90th percentile | −18% / +26% | −25% / +53% | −32% / +102% |

⚠️ This universe is still mostly *today's* survivors. Dot-com giants that later collapsed (Lucent, Nortel, WorldCom, Sun) have no Yahoo data, so these rebound statistics are biased upward. The same bias applies to the backtest universe in section 3.

## 3. Models and walk-forward backtest

The models are a stationary block bootstrap of NVDA's own returns; a **GJR-GARCH(1,1)-t**; a **factor + regime + earnings-jump** model (Nasdaq calm/stress regimes keyed off VIX, beta, fat-tailed idiosyncratic noise, and bootstrapped earnings-day jumps on known dates); and **state analogs** (k-NN on drawdown, momentum, realised volatility and VIX across the mega-cap universe, scaled to current volatility). The ensemble weights were fitted on pre-2017 data. These are the backtested models. In addition, `forecast.py` adds:

- the CEO-exit drift adjustment, tested separately with each event left out in turn;
- the **options-implied risk-neutral distribution** (Breeden–Litzenberger on the smoothed smile), used as a benchmark.

Backtest: 13 mega-cap tech stocks, a forecast every quarter from 2007, scored out-of-sample on 2017+ (494 forecasts). Lower CRPS is better.

| Model | CRPS 1m | CRPS 3m | CRPS 6m | 80% cover (1/3/6m) | After ≥20% drawdowns, CRPS 6m / cover |
|---|---|---|---|---|---|
| Block bootstrap | 0.064 | 0.102 | 0.152 | 72 / 74 / 74% | 0.213 / 63% |
| **GJR-GARCH-t** | **0.063** | **0.101** | 0.146 | 73 / 76 / 78% | **0.196** / 72% |
| Factor + regime + jumps | 0.065 | 0.103 | 0.152 | **81 / 83 / 80%** | 0.210 / 67% |
| State analogs | 0.064 | 0.102 | 0.148 | 75 / 78 / 77% | 0.211 / 75% |
| **Ensemble** | **0.063** | **0.101** | **0.145** | 76 / 80 / 80% | 0.203 / 73% |

- The models score within ~5% of each other. The ensemble is best or tied, and calibrated to 80% at 3 and 6 months.
- **After drawdowns, every model's intervals are too narrow** (coverage ~65–75% instead of 80%), and mean PIT is about 0.55–0.60, meaning realised returns beat the forecasts. Rebounds were under-predicted, partly because 2017–2026 was a bull market.
- **CEO-exit adjustment** (half the mean CAR of the *other* events): it improves CRPS by 7% at 1 month, 0% at 3 months, and makes it 2% worse at 6 months. It is therefore applied at 1 month only (−2.1%) and tapered to zero by 3 months.

## 4. Forecast

| Date (trading days) | | Ensemble + CEO adj. | Options-implied |
|---|---|---|---|
| **18 Dec 2026** (24) | median | **$164** | $162 |
| | 5–95% | $126–214 | $115–214 |
| | P(< $130) / P(> $200) | 7% / 11% | 12% / 11% |
| **19 Feb 2027** (65) | median | **$175** | $162 |
| | 5–95% | $113–264 | $93–239 |
| | P(< $130) / P(> $200) | 13% / 30% | 21% / 18% |
| **21 May 2027** (129) | median | **$190** | $159 |
| | 5–95% | $102–344 | $70–269 |
| | P(< $130) / P(back above $239 ATH) | 16% / 26% | 28% / 10% |

Individual models at 6 months, by median: state analogs $157, factor model $186, bootstrap $194, GARCH $221. Full table: `output/nvda_forecast_table.csv`.

### Scenario mix, including failed-company analogs (preferred view)

The scenario weights are a judgment call; edit `SCENARIO_WEIGHTS` in `forecast.py`. Defaults are **S1 70%, S2 27%, S3 3%**.
- **S1** = the backtested ensemble plus 50%-shrunk median S1 drift.
- **S2 and S3** = NVDA beta (1.39) × a bootstrapped Nasdaq move plus abnormal returns drawn from those cases.

| Date | Median | 5–95% | P(< $130) | P(< $100) | P(≤ −50%) | P(> $239 ATH) |
|---|---|---|---|---|---|---|
| 18 Dec 2026 | **$160** | $123–205 | 9% | 1% | 0.6% | 0.6% |
| 19 Feb 2027 | **$159** | $93–244 | 27% | 7% | 2.8% | 6% |
| 21 May 2027 | **$168** | $76–304 | 26% | **13%** | **6%** | 16% |
| *Options-implied, 21 May* | *$159* | *$68–269* | *28%* | *12%* | *7%* | *10%* |

Once the failed-company analogs are included, **the model's downside tail almost exactly matches what the options market prices** (P < $100 by May: 12.6% vs 12.2%). The survivor-only ensemble had it at 4.5%. That independent agreement is the strongest evidence that the earlier view was too rosy.

Sensitivity at 6 months:

| w(S2) | w(S3) | Median | 5th pct | P(< $100) | P(≤ −50%) |
|---|---|---|---|---|---|
| 10% | 0% | $175 | $91 | 8% | 3% |
| 10% | 3% | $173 | $82 | 10% | 5% |
| **27%** | **3%** | **$168** | **$77** | **13%** | **6%** |
| 27% | 10% | $164 | $22 | 17% | 11% |
| 50% | 3% | $165 | $72 | 15% | 8% |
| 50% | 10% | $160 | $23 | 20% | 12% |

**How to read the gap between the ensemble and options.** The two agree on the next month. They diverge later almost entirely because of *drift*:
- Options are risk-neutral, so they carry no equity risk premium; their median sits below spot because of volatility drag.
- The bootstrap and GARCH models carry NVDA's extraordinary 5–10-year average return forward.
- The state-analog model, which conditions on "fast drawdown, high volatility, high VIX", is the most cautious and lands close to the options.

The backtest favours the ensemble overall, but it also shows that history-based drift is NVDA's best-case past rather than a law. A reasonable central range for May is **$160–190**, with very wide tails both ways.

**Near-term event: the 18 Nov earnings reaction.** NVDA's recent reactions average ±5.5%, and options price roughly ±6–7% for the report itself. The factor model's simulated draw for that day comes from NVDA's last 24 reactions.

## 5. Caveats

- **There is no clean precedent** for a scandal-driven exit by the founder-CEO of a ~$4T company in the middle of an AI-capex scare. The event set mixes very different situations: founder retirements, scandals and firings.
- **Unmodelled jumps:** the naming of a permanent CEO (Haas would likely be read positively), Huang's congressional testimony and any further revelations, hyperscaler capex guidance, and export controls.
- **Survivorship:** the comparable-exit set includes 12 delisted or failed companies, hand-compiled from news reports. Interim prices for some of them are low-confidence (flagged per row), and betas are set to 1. The drawdown-analog universe and the backtest universe still contain only companies Yahoo carries, i.e. survivors.
- **Small samples:** S2 has only 5 cases, so its distribution is coarse. The scenario weights are judgment, not estimates.
- The CEO event dates were entered by hand, then verified against the day-0 price reactions. The options snapshot is from the 13 Nov close, and the 4% risk-free rate is an assumption.

## Reproduce

```bash
pip install yfinance arch numpy pandas scipy matplotlib
python fetch_data.py    # needs Yahoo Finance hosts allowed
python event_study.py
python comparable_events.py
python backtest.py      # ~1-2 min on 4 cores
python forecast.py
```
