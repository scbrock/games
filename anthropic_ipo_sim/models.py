"""First-day return models for IPOs.

Every model exposes the same interface:
    fit(df)                 -> self
    sample(X, n, rng)       -> array (len(X), n) of simulated log first-day returns

Target: y = ln(first_close / offer).
Features (see `features`):
    rev     ln(offer / range midpoint)  -- Hanley (1993) partial-adjustment signal
    ln_size ln(deal size, $bn)
    float   % of shares sold in the deal
    vix     VIX at pricing
    ndx_1m  Nasdaq return over prior ~month, %
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

FEATURES = ["rev", "ln_size", "float", "vix", "ndx_1m"]


def features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    mid = (df["range_low"] + df["range_high"]) / 2
    out["rev"] = np.log(df["offer"] / mid)
    out["ln_size"] = np.log(df["deal_bn"])
    out["float"] = df["float_pct"]
    out["vix"] = df["vix"]
    out["ndx_1m"] = df["ndx_1m"]
    return out


def target(df: pd.DataFrame) -> np.ndarray:
    return np.log(df["first_close"] / df["offer"]).to_numpy()


class BaseRate:
    """Unconditional: bootstrap the empirical distribution of past first-day returns."""
    name = "Base rate (all IPOs)"

    def fit(self, df):
        self.y = target(df)
        return self

    def sample(self, X, n, rng):
        return rng.choice(self.y, size=(len(X), n))


class MegaRefClass(BaseRate):
    """Reference class: only large deals (>= $3bn raised)."""
    name = "Reference class (deals >= $3bn)"

    def fit(self, df):
        big = df[df["deal_bn"] >= 3.0]
        self.y = target(big if len(big) >= 5 else df)
        return self


class _ResidualBootstrapLinear:
    cols = FEATURES

    def _design(self, X):
        return X[self.cols].to_numpy()

    def sample(self, X, n, rng):
        mu = self.predict(X)
        eps = rng.choice(self.resid, size=(len(X), n))
        # inflate residuals for parameter uncertainty (LOO-ish correction)
        return mu[:, None] + eps * self.infl


class PartialAdjustment(_ResidualBootstrapLinear):
    """Single-factor model: y = a + b * revision. The best-documented IPO regularity."""
    name = "Partial adjustment (revision only)"
    cols = ["rev"]

    def fit(self, df):
        X, y = self._design(features(df)), target(df)
        A = np.c_[np.ones(len(X)), X]
        self.beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        self.resid = y - A @ self.beta
        self.infl = np.sqrt(len(y) / max(len(y) - A.shape[1], 1))
        return self

    def predict(self, X):
        return np.c_[np.ones(len(X)), self._design(X)] @ self.beta


class OLSMarket(PartialAdjustment):
    """Revision + market conditions + deal structure, OLS."""
    name = "OLS (revision + market + structure)"
    cols = FEATURES


class RidgeMarket(_ResidualBootstrapLinear):
    """Same features, ridge-shrunk (better behaved when extrapolating to a $60bn deal)."""
    name = "Ridge (revision + market + structure)"

    def fit(self, df):
        X, y = self._design(features(df)), target(df)
        self.sc = StandardScaler().fit(X)
        self.m = RidgeCV(alphas=np.logspace(-2, 3, 30)).fit(self.sc.transform(X), y)
        self.resid = y - self.m.predict(self.sc.transform(X))
        self.infl = np.sqrt(len(y) / max(len(y) - 3, 1))
        return self

    def predict(self, X):
        return self.m.predict(self.sc.transform(self._design(X)))


class KNNAnalogs:
    """Nearest historical analogs in standardized feature space (revision weighted x2)."""
    name = "k-NN historical analogs"
    weights = np.array([2.0, 1.0, 0.7, 1.0, 1.0])

    def __init__(self, k=8):
        self.k = k

    def fit(self, df):
        X = features(df)[FEATURES].to_numpy()
        self.sc = StandardScaler().fit(X)
        self.Z = self.sc.transform(X) * self.weights
        self.y = target(df)
        return self

    def sample(self, X, n, rng):
        Zq = self.sc.transform(X[FEATURES].to_numpy()) * self.weights
        out = np.empty((len(X), n))
        for i, z in enumerate(Zq):
            d = np.sqrt(((self.Z - z) ** 2).sum(1))
            idx = np.argsort(d)[: self.k]
            w = 1 / (d[idx] + 0.25)
            w /= w.sum()
            # analog outcome + small kernel jitter so the distribution isn't k spikes
            out[i] = rng.choice(self.y[idx], size=n, p=w) + rng.normal(0, 0.08, n)
        return out


class Ensemble:
    """Mixture of component models, weighted by backtest skill (inverse CRPS)."""
    name = "Skill-weighted ensemble"

    def __init__(self, components, weights):
        self.components = components
        self.weights = np.asarray(weights, float) / np.sum(weights)

    def fit(self, df):
        for m in self.components:
            m.fit(df)
        return self

    def sample(self, X, n, rng):
        counts = rng.multinomial(n, self.weights)
        parts = [m.sample(X, c, rng) for m, c in zip(self.components, counts) if c]
        s = np.concatenate(parts, axis=1)
        return rng.permuted(s, axis=1)


def all_models():
    return [BaseRate(), MegaRefClass(), PartialAdjustment(), OLSMarket(), RidgeMarket(), KNNAnalogs()]
