"""Post-listing price-path models (first-day close -> 1 year).

Two approaches, both returning simulated paths of log(price / first_close):

1. ConstantVolGBM      -- textbook geometric Brownian motion, single vol, zero drift.
2. RegimeJumpModel     -- market factor with calm/stress Markov regimes (start state set
                          from VIX), stock beta to market, idiosyncratic vol, earnings-day
                          jumps (fat-tailed), new-issue underperformance drift (Ritter 1991),
                          and the lock-up expiry dip (Field & Hanka 2001) around day ~124.
"""
import numpy as np

TD = 252  # trading days in a year
LOCKUP_DAY = 124  # ~180 calendar days
QUIET_DAY = 18  # ~25 calendar days: analyst initiations


class ConstantVolGBM:
    name = "Constant-vol GBM"

    def __init__(self, vol=0.60, drift=0.0):
        self.vol, self.drift = vol, drift

    def simulate(self, n, rng, days=TD, vix=None):
        dt = 1 / TD
        z = rng.standard_normal((n, days))
        inc = (self.drift - 0.5 * self.vol**2) * dt + self.vol * np.sqrt(dt) * z
        return np.cumsum(inc, axis=1)


class RegimeJumpModel:
    name = "Regime-switching + jumps + lock-up"

    def __init__(self, beta=1.4, idio_vol=0.45, abn_drift=-0.06, jump_sd=0.10,
                 lockup_dip=-0.02, quiet_bump=0.01,
                 calm=(0.10, 0.16), stress=(-0.25, 0.38), p_cs=0.015, p_sc=0.04):
        self.__dict__.update(locals())
        del self.__dict__["self"]

    def simulate(self, n, rng, days=TD, vix=18.0):
        dt = 1 / TD
        # start-state probability of stress rises with VIX (12 -> ~0, 30+ -> ~1)
        p_stress0 = np.clip((vix - 14) / 16, 0.02, 0.95)
        state = rng.random(n) < p_stress0
        logp = np.zeros((n, days))
        acc = np.zeros(n)
        earn_days = {63, 126, 189, 252}
        for t in range(days):
            mu_m = np.where(state, self.stress[0], self.calm[0])
            sd_m = np.where(state, self.stress[1], self.calm[1])
            mkt = (mu_m - 0.5 * sd_m**2) * dt + sd_m * np.sqrt(dt) * rng.standard_t(5, n) / np.sqrt(5 / 3)
            idio = (self.abn_drift - 0.5 * self.idio_vol**2) * dt + self.idio_vol * np.sqrt(dt) * rng.standard_t(4, n) / np.sqrt(2)
            r = self.beta * mkt + idio
            if t + 1 in earn_days:
                r += self.jump_sd * rng.standard_t(3, n) / np.sqrt(3)
            if LOCKUP_DAY - 5 <= t < LOCKUP_DAY + 5:
                r += self.lockup_dip / 10
            if t == QUIET_DAY:
                r += self.quiet_bump
            acc += r
            logp[:, t] = acc
            u = rng.random(n)
            state = np.where(state, u > self.p_sc, u < self.p_cs)
        return logp
