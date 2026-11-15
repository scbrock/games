"""Forecast models for a stock's forward log return at several horizons.

Every model: forecast(ctx, horizons, n, rng) -> {h: array of n simulated log returns}
`ctx` (built by make_context) holds only information available at the origin date,
so the same code serves the walk-forward backtest and the live NVDA forecast.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from arch import arch_model


@dataclass
class Context:
    ticker: str
    origin: pd.Timestamp
    r: pd.Series            # stock daily log returns up to origin (inclusive)
    m: pd.Series            # Nasdaq daily log returns up to origin
    vix: pd.Series          # VIX closes up to origin
    earn_hist: list         # past earnings reaction days (Timestamps) for this stock
    earn_future: list = field(default_factory=list)  # trading-day offsets (1-based) of upcoming earnings reactions
    library: pd.DataFrame = None  # analog library rows with fwd returns realised before origin


def reaction_days(ts_list, index):
    """Map earnings timestamps to the trading day the market reacts (after-close -> next day)."""
    out = []
    for ts in ts_list:
        ts = pd.Timestamp(ts)
        # after-close reports (timestamp >= noon) react the next session; pre-market the same day
        d = ts.normalize() + pd.Timedelta(days=1 if ts.hour >= 12 else 0)
        i = index.searchsorted(d)
        if i < len(index):
            out.append(index[i])
    return sorted(set(out))


# ---------------------------------------------------------------- M1
class BlockBootstrap:
    name = "Block bootstrap (5y own history)"

    def forecast(self, ctx, horizons, n, rng):
        x = ctx.r.iloc[-1260:].to_numpy()
        H = max(horizons)
        L = len(x)
        idx = np.empty((n, H), dtype=int)
        idx[:, 0] = rng.integers(0, L, n)
        for t in range(1, H):
            jump = rng.random(n) < 1 / 10  # mean block length 10
            idx[:, t] = np.where(jump, rng.integers(0, L, n), (idx[:, t - 1] + 1) % L)
        cum = np.cumsum(x[idx], axis=1)
        return {h: cum[:, h - 1] for h in horizons}


# ---------------------------------------------------------------- M2
class GJRGarch:
    name = "GJR-GARCH(1,1)-t"

    def __init__(self, zero_mean=False):
        self.zero_mean = zero_mean

    def forecast(self, ctx, horizons, n, rng):
        y = 100 * ctx.r.iloc[-2520:]
        am = arch_model(y, mean="Zero" if self.zero_mean else "Constant", vol="GARCH", p=1, o=1, q=1, dist="t")
        res = am.fit(disp="off", options={"maxiter": 200})
        H = max(horizons)
        f = res.forecast(horizon=H, method="simulation", simulations=n, reindex=False,
                         random_state=np.random.RandomState(rng.integers(2**31)))
        sims = f.simulations.values[-1] / 100  # (n, H)
        cum = np.cumsum(sims, axis=1)
        return {h: cum[:, h - 1] for h in horizons}


# ---------------------------------------------------------------- M3
class FactorRegimeJump:
    """Nasdaq factor with VIX-defined calm/stress regimes x beta + idiosyncratic t-noise
    + earnings-day jumps bootstrapped from the stock's own past earnings reactions."""
    name = "Factor + regime + earnings jumps"

    def __init__(self, idio_drift=0.0, extra_drift=None):
        self.idio_drift = idio_drift
        self.extra_drift = extra_drift or {}  # {h: additive log-return shift}, used by the event model

    def _regimes(self, ctx):
        m = ctx.m.iloc[-5040:]
        v = ctx.vix.reindex(m.index).ffill()
        stress = (v > 25).to_numpy()
        p = {}
        for s in (False, True):
            x = m[stress == s]
            p[s] = (x.mean(), x.std())
        a, b = stress[:-1], stress[1:]
        p_cs = np.mean(b[~a]) if (~a).any() else 0.01
        p_sc = np.mean(~b[a]) if a.any() else 0.05
        return p, p_cs, p_sc, bool(v.iloc[-1] > 25)

    def forecast(self, ctx, horizons, n, rng):
        H = max(horizons)
        p, p_cs, p_sc, s0 = self._regimes(ctx)
        rs, ms = ctx.r.iloc[-250:], ctx.m.reindex(ctx.r.index).iloc[-250:]
        beta = np.cov(rs, ms)[0, 1] / ms.var()
        ab = (ctx.r - beta * ctx.m.reindex(ctx.r.index)).dropna()
        earn = set(ctx.earn_hist)
        recent = ab.iloc[-126:]
        idio_sd = recent[~recent.index.isin(earn)].std()
        jumps = ab[ab.index.isin(earn)].iloc[-24:].to_numpy()  # last ~6 years of reactions
        state = np.full(n, s0)
        cum = np.zeros(n)
        out = {}
        for t in range(1, H + 1):
            mu = np.where(state, p[True][0], p[False][0])
            sd = np.where(state, p[True][1], p[False][1])
            mk = mu + sd * rng.standard_t(5, n) / np.sqrt(5 / 3)
            idio = self.idio_drift / 252 + idio_sd * rng.standard_t(4, n) / np.sqrt(2)
            cum += beta * mk + idio
            if t in ctx.earn_future:
                cum += rng.choice(jumps, n) if len(jumps) >= 6 else 3 * idio_sd * rng.standard_normal(n)
            u = rng.random(n)
            state = np.where(state, u > p_sc, u < p_cs)
            if t in horizons:
                out[t] = cum.copy() + self.extra_drift.get(t, 0.0)
        return out


# ---------------------------------------------------------------- M4
STATE_COLS = ["dd", "ret63", "lvol21", "ret252", "vix"]


def state_features(close: pd.Series, vix: pd.Series) -> pd.DataFrame:
    lr = np.log(close).diff()
    f = pd.DataFrame(index=close.index)
    f["dd"] = np.log(close / close.rolling(252, min_periods=200).max())
    f["ret63"] = np.log(close / close.shift(63))
    f["ret252"] = np.log(close / close.shift(252))
    f["vol21"] = lr.rolling(21).std() * np.sqrt(252)
    f["vol252"] = lr.rolling(252).std() * np.sqrt(252)
    f["lvol21"] = np.log(f["vol21"])
    f["vix"] = vix.reindex(close.index).ffill()
    return f


class StateAnalogs:
    """k-NN over (drawdown, 3m & 12m momentum, realised vol, VIX) across the mega-cap
    universe; forward returns are vol-normalised from analog to current stock."""
    name = "State analogs (k-NN, cross-section)"

    def __init__(self, k=150):
        self.k = k

    def forecast(self, ctx, horizons, n, rng):
        lib = ctx.library
        q = ctx.state
        out = {}
        for h in horizons:
            L = lib[lib[f"end_{h}"] <= ctx.origin].dropna(subset=[f"fwd_{h}"])
            X = L[STATE_COLS].to_numpy()
            mu, sd = X.mean(0), X.std(0)
            w = np.array([2.0, 1.0, 1.0, 0.7, 1.0])
            d = np.sqrt(((((X - mu) / sd - (q[STATE_COLS].to_numpy() - mu) / sd) * w) ** 2).sum(1))
            idx = np.argsort(d)[: self.k]
            vol_now = np.sqrt(0.5 * q["vol21"] ** 2 + 0.5 * q["vol252"] ** 2)
            vol_an = np.sqrt(0.5 * L["vol21"].to_numpy()[idx] ** 2 + 0.5 * L["vol252"].to_numpy()[idx] ** 2)
            z = L[f"fwd_{h}"].to_numpy()[idx] / vol_an
            out[h] = rng.choice(z, n) * vol_now + rng.normal(0, 0.02 * np.sqrt(h / 21), n)
        return out


def build_library(prices, vix, tickers, horizons, step=5):
    rows = []
    for tkr in tickers:
        c = prices[tkr].dropna()
        if len(c) < 400:
            continue
        f = state_features(c, vix)
        lc = np.log(c)
        for h in horizons:
            f[f"fwd_{h}"] = lc.shift(-h) - lc
            end = pd.Series(c.index, index=c.index).shift(-h)
            f[f"end_{h}"] = end
        f["ticker"] = tkr
        rows.append(f.iloc[260::step].dropna(subset=STATE_COLS))
    return pd.concat(rows)


class Ensemble:
    def __init__(self, models, weights, name="Skill-weighted ensemble"):
        self.models, self.name = models, name
        self.w = np.asarray(weights, float) / np.sum(weights)

    def forecast(self, ctx, horizons, n, rng):
        counts = rng.multinomial(n, self.w)
        parts = [m.forecast(ctx, horizons, c, rng) for m, c in zip(self.models, counts) if c]
        return {h: rng.permutation(np.concatenate([p[h] for p in parts])) for h in horizons}
