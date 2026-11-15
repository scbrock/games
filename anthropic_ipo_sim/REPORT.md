# Anthropic (ANT) IPO: Monte Carlo simulation and historical backtest

*Prepared 15 Nov 2026, before pricing (expected Nov 18) and first trade (expected Nov 19, Nasdaq).
This is a research exercise, not investment advice.*

## 1. What we know (research inputs)

| Item | Value | Source |
|---|---|---|
| Price range (S-1/A, Nov 10) | $70–78, 825M shares, up to ~$64bn raised | [CNBC](https://www.cnbc.com/2026/11/10/anthropic-sets-price-range-of-70-to-78-in-upcoming-ipo.html), [decodethefuture](https://decodethefuture.org/en/anthropic-s1-ipo-filing-explained/) |
| Shares | ~13.09bn basic (→ $0.92–1.02T); ~$1.30–1.45T fully diluted (≈18.6bn FD shares) | [NBC](https://www.nbcnews.com/business/corporations/anthropic-sets-modest-1-trillion-ipo-valuation-target-rcna608514), [tastytrade](https://tastytrade.com/learn/markets/industry/anthropic-ipo/) |
| Float | ~6.3% of basic shares: very low | derived |
| Demand | Book covered across the range; reportedly ~6x oversubscribed; banks weighing a price above $78 | [CNBC](https://www.cnbc.com/2026/11/10/anthropic-sets-price-range-of-70-to-78-in-upcoming-ipo.html), [Vantage](https://www.vantagemarkets.com/en/market-analysis/anthropic-ipo-what-to-know/) (relaying Bloomberg/FT) |
| Fundamentals | H1-26 revenue ~$16.3bn (vs $1.16bn H1-25); run-rate $47bn (May, company) / ~$65bn (Jul, reported); last private mark $965bn (May) | [FourWeekMBA](https://fourweekmba.com/ai-anthropics-s-1-shows-16-3b-half-year-revenue-up-14x/), [Yahoo](https://finance.yahoo.com/markets/article/anthropic-more-valuable-than-openai-in-latest-funding-round-184115376.html) |
| Market | Nasdaq hit correction territory; −5.5% on Nov 5 with VIX +70% to 28; VIX back to ~19.5 by Nov 10; S&P +2.5% w/e Nov 13 but tech weak Fri (Nvidia CEO exit); Nvidia earnings Nov 17 | [Cboe](https://www.cboe.com/insights/posts/week-of-11-9-2026-no-contagion-yet-equity-vol-spikes-macro-vol-fades), [WaPo/AP](https://www.washingtonpost.com/business/2026/11/13/wall-street-stocks-dow-nasdaq/f15a10e2-dfa7-11f1-912c-4fbb80d73f7f_story.html) |
| Recent comps | SpaceX (Jun-26): $135 fixed price, $75bn, ~3–4x covered, +19% day 1, roughly back at offer by Nov. Cerebras (May-26): priced $60 above range, +68% day 1. 40 largest US IPOs since 2025: median +17.8% day 1, **−12.5%** median from offer to Oct-26 | [NPR](https://www.npr.org/2026/06/12/nx-s1-5855004/stock-ai-spacex-ipo-elon-musk), [MAS Economics](https://maseconomics.com/ai-ipo-wave/), [Renaissance](https://www.renaissancecapital.com/IPO-Center/Winners-Losers/1427) |
| Prediction market | Polymarket P(day-1 close ≥ $1.5T) fell to ~34% on Nov 15 | [FourWeekMBA](https://fourweekmba.com/ai-anthropic-ipo-polymarket-odds-of-a-1-5t-debut-fall-to-34/) |
| Academic base rates | US 1980–2025: mean day-1 +19%, median +7% (Ritter). Very high P/S IPOs pop more but lag over 3 years. Ritter has warned about the valuation | [Ritter](https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf), [TheStreet](https://www.thestreet.com/investing/anthropic-ipo-valuation-risk-1-trillion-ceiling-jay-ritter) |

Established findings built into the models: **partial adjustment** (Hanley 1993: deals priced above range pop more), **market conditions feed into pricing** (Lowry & Schwert 2004), **long-run underperformance of new issues** (Ritter 1991), and the **lock-up expiry dip** of about 1–3% (Field & Hanka 2001).

## 2. Models

**First-day return.** Six approaches, all producing full predictive distributions (`models.py`):

1. **Base rate.** Bootstrap of all historical day-1 returns.
2. **Reference class.** Deals raising $3bn or more only.
3. **Partial adjustment.** `ln(close/offer) = a + b·ln(offer/range mid)`.
4. **OLS.** Revision + VIX + Nasdaq 1-month return + log deal size + float %.
5. **Ridge.** Same features, shrunk (safer when extrapolating to a ~$60bn deal).
6. **k-NN analogs.** Nearest historical deals in feature space.
7. **Ensemble.** Mixture of 1–6, weighted by walk-forward CRPS.

**Post-listing path** (`paths.py`): (a) constant-vol GBM; (b) a regime-switching market (calm/stress, start state from VIX) × beta 1.4 + idiosyncratic vol + fat-tailed earnings jumps + new-issue drift + a lock-up dip at about day 124.

**Simulation chain** (`simulate.py`, 40k worlds): market move to listing (including the Nvidia print) → pricing revision (strong book, median ~$80, partial pass-through of the market move) → day-1 return from the ensemble → one-year path.

## 3. Backtest (45 notable tech/mega IPOs, 1995–2026)

The first-day models were tested two ways: leave-one-out, and walk-forward (each deal predicted using only earlier deals). CRPS is lower-is-better; cover80 is the share of outcomes that fell inside the 80% interval.

| Model | LOO MAE (pts) | LOO CRPS | LOO cover80 | WF MAE | WF CRPS | WF cover80 | WF rank corr |
|---|---|---|---|---|---|---|---|
| Base rate | 35.8 | 0.171 | 0.78 | 38.9 | 0.183 | 0.73 | −0.39 |
| Reference class ≥$3bn | 35.6 | 0.172 | 0.78 | 38.3 | 0.187 | 0.70 | 0.05 |
| Partial adjustment | 28.8 | 0.144 | 0.78 | 31.8 | 0.147 | **0.83** | **0.65** |
| OLS full | 30.7 | 0.151 | 0.73 | 33.2 | 0.155 | 0.77 | 0.51 |
| Ridge full | 31.4 | 0.147 | 0.73 | 34.0 | 0.161 | 0.70 | 0.49 |
| k-NN analogs | **28.4** | **0.134** | 0.84 | **30.9** | **0.140** | 0.73 | 0.64 |
| Ensemble | 29.5 | 0.138 | **0.87** | 32.7 | 0.153 | 0.77 | 0.59 |

Takeaways:
- **Price revision is the signal.** Its coefficient is ~0.74–0.83 (z≈4–4.7). Once revision is known, VIX, size and float are insignificant; the Nasdaq 1-month return is borderline (+1.6 pts of day-1 return per 1% of Nasdaq gain, p≈0.06).
- **Errors are large even for the best models**, about ±30 pts MAE, because day-1 returns are heavy-tailed (Figma +250%, Snowflake +112%). Treat point forecasts with caution and rely on the distributions.

**One-year path calibration** used 33 deals with an approximate 1-year return from the day-1 close; the historical median was −21%.

| Path model | cover80 (all) | cover80 (≥$5bn deals) | mean PIT (0.5 = unbiased) | CRPS |
|---|---|---|---|---|
| GBM vol 40% | 0.55 | 0.83 | 0.45 | 0.500 |
| GBM vol 80% | 0.73 | 1.00 | 0.55 | 0.465 |
| Regime+jumps, idio 45%, drift −6% | 0.58 | 0.83 | 0.51 | 0.468 |
| **Regime+jumps, idio 50%, drift −10% (used)** | 0.67 | 1.00 | 0.53 | **0.464** |
| Regime+jumps, idio 70%, drift −10% | 0.73 | 1.00 | 0.57 | 0.473 |

All the path models under-cover the tails of the broad sample, which is mostly smaller, more volatile names. On the 6 mega deals, mean PIT is ~0.4: their first years were *worse* than the model expected. Visa −3%, GM −39%, Facebook −32%, Alibaba −36%, Uber −25%, Rivian −65%.

## 4. Results for Anthropic (base case)

| Outcome | Median | 25–75% | 5–95% |
|---|---|---|---|
| Final offer price | **$80.0** | $77–83 | $73–88 |
| Day-1 return | **+21%** | +1% to +41% | −13% to +112% |
| Day-1 close | **$97** | $81–114 | $67–165 |
| Day-1 market cap (basic / FD) | $1.27T / $1.80T | $1.06–1.49T / $1.51–2.12T | |
| Price at lock-up expiry (~day 124) | $86 | $61–122 | $37–204 |
| Price at 1 year | **$75** | $47–120 | $24–237 |

- P(priced **above** $78) **68%**; within the range 32%; below $70 ~1%.
- P(breaks issue on day 1) **21%**; P(pop > 25%) 45%; P(pop > 50%) 18%.
- P(below offer at lock-up expiry) 45%; **P(below offer after 1 year) 54%**.
- **Polymarket check:** the model gives P(day-1 close ≥ $1.5T) of **24% on basic shares** and 76% fully diluted. Polymarket's 34% fits the basic-share count, which puts the model slightly more cautious than the crowd.

**Model disagreement is the main uncertainty.** Base-rate approaches give a +29–31% median. Approaches that condition on market and deal structure give +10–15% with ~30% break risk, because this deal is huge, the market just corrected, and the Nasdaq trend is negative.

**Sensitivity of the median day-1 return** (fixed offer price × market state):

| Offer | Calm (VIX 14, NDX +4%) | Base (VIX 20, NDX −5%) | Stress (VIX 30, NDX −12%) |
|---|---|---|---|
| $70 | +21% | +9% | +4% |
| $78 | +25% | +18% | +11% |
| $86 | +29% | +21% | +19% |

Counterintuitively, pricing *above* the range raises the expected pop. Historically, upward revisions signal excess demand that bankers only partially pass through.

## 5. Caveats (read these)

- **The historical data is hand-compiled.** This sandbox can only reach package registries, so price data could not be downloaded. Offer prices, ranges and day-1 closes are well documented. VIX, Nasdaq 1-month and float values are approximate, and 1-year returns are rounded from memory of public price history. Verify them before relying on the numbers (`data/historical_ipos.csv`).
- **Selection bias.** The sample is *notable* IPOs, which skews toward famous successes. Ritter's full-sample median pop is +7%, versus ~+30% here, so the base-rate models likely overstate the pop.
- **Extrapolation.** Only SpaceX ($75bn) is comparable in size, and nothing is comparable in valuation-to-revenue growth. Treat Anthropic-specific factors as unmodelled: AI-capex sentiment, the Nvidia print, Long-Term Benefit Trust governance, and index-inclusion flows.
- The pricing-stage assumptions (median ~$80) rest on press reports of book strength. Change `ASSUMPTIONS` in `simulate.py` and re-run.

## 6. Reproduce

```bash
pip install numpy pandas scipy statsmodels scikit-learn matplotlib
python backtest.py   # writes output/backtest.json (ensemble weights)
python simulate.py   # writes output/simulation_summary.json, sensitivity.csv, per_model.csv, chart
```
