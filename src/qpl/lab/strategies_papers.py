"""Strategies implemented from two papers supplied by the user (built into the Lab).

1. KalmanPairs - Yang Shuo et al., "Hierarchical futures pair trading: DTW + k-means clustering, Engle-Granger cointegration,
   Kalman-filter hedge ratio, half-life z-score" (SSRN 5017127). Paper data: Chinese dominant continuous futures 2016-2023,
   daily closes. Reported: Sharpe 4.35, max DD -2.4% (in sample incl. threshold tuning), Sharpe 4.19 out of sample.
2. MaxAIQLearning - Huber, "MaxAI: GA-tuned Q-learning for intraday NASDAQ futures" (preprint, not peer reviewed).
   Paper data: CME NQ 1-minute bars (FirstRate Data, paid), train 2021, test 2022. Final NQ34 rules partly proprietary.

What could NOT be reproduced exactly (also shown in the app):
- Pairs: the Chinese futures data; the exact Kalman noise settings (delta, tau) and clustering k; paper thresholds were
  chosen in sample. Everything else follows the text: DTW distance -> k-medoids clusters (k by silhouette) -> Engle-Granger
  (p < 0.05) within clusters -> scalar Kalman hedge ratio -> spread z-score over a half-life window -> delayed entry at
  1.25 sigma, exit at 0.08 sigma past the mean.
- MaxAI: the money-flow indicator of NQ34 is proprietary ("custom derivative of Chaikin Money Flow"), the GA search ranges
  are withheld, and TradeStation fills intrabar stops. Here: standard 20-bar Chaikin Money Flow as the state, tabular
  Q-learning with the paper's GA-final hyper-parameters (alpha 0.12, gamma 0.85, epsilon 0.08), stop-loss / profit target
  checked on bar closes, US cash session only, retrained walk-forward so nothing is learnt from the future.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qpl.lab.data import BPD
from qpl.lab.strategy_base import Param, Strategy

try:                                                   # optional speed-up; pure-python fallback below
    from numba import njit
except Exception:                                      # pragma: no cover
    njit = None


# =====================================================================================================================
# Pairs: DTW, k-medoids, Engle-Granger, Kalman, half-life
# =====================================================================================================================
def _dtw_py(a, b):
    n, m = len(a), len(b)
    D = np.full((n + 1, m + 1), np.inf); D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = abs(a[i - 1] - b[j - 1]) + min(D[i - 1, j - 1], D[i - 1, j], D[i, j - 1])
    return D[n, m]


_dtw = njit(cache=False)(_dtw_py) if njit else _dtw_py


def dtw_matrix(X: np.ndarray) -> np.ndarray:
    """X: (time, assets) normalised prices -> symmetric DTW distance matrix. Long series are averaged down to ~260 points."""
    step = max(1, len(X) // 260)
    if step > 1:
        X = X[: len(X) // step * step].reshape(-1, step, X.shape[1]).mean(axis=1)
    if not njit:
        X = X[:: max(1, len(X) // 120)]
    k = X.shape[1]; Dm = np.zeros((k, k))
    for i in range(k):
        for j in range(i + 1, k):
            Dm[i, j] = Dm[j, i] = _dtw(np.ascontiguousarray(X[:, i]), np.ascontiguousarray(X[:, j]))
    return Dm


def kmedoids(Dm: np.ndarray, k: int, n_init: int = 20, seed: int = 0) -> np.ndarray:
    """k-means on a precomputed distance matrix (k-medoids / Voronoi iteration, several random starts)."""
    rng = np.random.default_rng(seed); n = len(Dm); best, best_cost = None, np.inf
    for _ in range(n_init):
        med = rng.choice(n, k, replace=False)
        for _ in range(100):
            lab = np.argmin(Dm[:, med], axis=1)
            new = med.copy()
            for c in range(k):
                idx = np.where(lab == c)[0]
                if len(idx):
                    new[c] = idx[np.argmin(Dm[np.ix_(idx, idx)].sum(axis=1))]
            if set(new) == set(med):
                break
            med = new
        lab = np.argmin(Dm[:, med], axis=1); cost = Dm[np.arange(n), med[lab]].sum()
        if cost < best_cost:
            best, best_cost = lab, cost
    return best


def silhouette(Dm: np.ndarray, lab: np.ndarray) -> float:
    s = []
    for i in range(len(Dm)):
        same = (lab == lab[i]); same[i] = False
        if not same.any():
            s.append(0.0); continue
        a = Dm[i, same].mean()
        b = min(Dm[i, lab == c].mean() for c in set(lab) if c != lab[i]) if len(set(lab)) > 1 else 0.0
        s.append((b - a) / max(a, b) if max(a, b) > 0 else 0.0)
    return float(np.mean(s))


def cluster_assets(P: pd.DataFrame, k_max: int = 6):
    """DTW + k-medoids, k chosen by the silhouette score (as in the paper). Returns (labels, k, silhouette)."""
    n = P.shape[1]
    if n < 4:
        return np.zeros(n, dtype=int), 1, np.nan
    Dm = dtw_matrix(P.to_numpy())
    best = (np.zeros(n, dtype=int), 1, -np.inf)
    for k in range(2, min(k_max, n - 1) + 1):
        lab = kmedoids(Dm, k); sc = silhouette(Dm, lab)
        if sc > best[2]:
            best = (lab, k, sc)
    return best


def engle_granger(y: np.ndarray, x: np.ndarray) -> float:
    """Engle-Granger cointegration p-value (same test as statsmodels.coint: OLS y on x + constant, ADF on the residual with
    the lag length chosen by AIC, MacKinnon p-value), written with numpy so hundreds of pairs run in seconds."""
    from statsmodels.tsa.adfvalues import mackinnonp
    n = len(y)
    A = np.column_stack([np.ones(n), x])
    e = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
    de = np.diff(e)
    maxlag = int(np.ceil(12 * (n / 100) ** 0.25))
    maxlag = min(maxlag, n // 2 - 3)
    if maxlag < 0:
        return 1.0
    nobs = len(de) - maxlag
    lagmat = np.column_stack([de[maxlag - i - 1: len(de) - i - 1] for i in range(maxlag)]) if maxlag else np.empty((nobs, 0))
    yy, lev = de[maxlag:], e[maxlag:-1]
    best = (np.inf, None)
    for L in range(maxlag + 1):                          # AIC over lag lengths on a common sample (statsmodels autolag)
        X = np.column_stack([lev, lagmat[:, :L]])
        b, res, *_ = np.linalg.lstsq(X, yy, rcond=None)
        ssr = float(res[0]) if len(res) else float(((yy - X @ b) ** 2).sum())
        aic = nobs * np.log(ssr / nobs) + 2 * (L + 1)
        if aic < best[0]:
            best = (aic, L)
    L = best[1]                                          # re-estimate with the chosen lag on the full available sample
    nobs = len(de) - L
    X = np.column_stack([e[L:-1]] + [de[L - i - 1: len(de) - i - 1] for i in range(L)])
    yy = de[L:]
    b = np.linalg.lstsq(X, yy, rcond=None)[0]
    r = yy - X @ b
    s2 = (r @ r) / (nobs - X.shape[1])
    se = np.sqrt(s2 * np.linalg.inv(X.T @ X)[0, 0])
    if not np.isfinite(se) or se == 0:
        return 1.0
    return float(mackinnonp(b[0] / se, regression="c", N=2))


def kalman_beta(y: np.ndarray, x: np.ndarray, delta: float, tau: float) -> np.ndarray:
    """Scalar Kalman filter for the hedge ratio in y_t = beta_t * x_t + n_t, beta_t = beta_{t-1} + m_t (paper eq. 13-21).
    Returns beta_{t|t}, i.e. known at the close of t."""
    vw = delta / (1 - delta)
    beta, P = (y[0] / x[0] if x[0] else 1.0), 1.0
    out = np.empty(len(y))
    for t in range(len(y)):
        R = P + vw                                       # state covariance prediction
        F = x[t] * R * x[t] + tau                        # measurement variance prediction
        e = y[t] - x[t] * beta                           # forecast error
        K = R * x[t] / F                                 # Kalman gain
        beta = beta + K * e
        P = R - K * x[t] * R
        out[t] = beta
    return out


def kalman_level(p: np.ndarray, q_ratio: float) -> np.ndarray:
    """Causal local-level Kalman smoothing of a price series (the paper's 'Kalman filter smoothing' preprocessing step)."""
    m, P, out = p[0], 1.0, np.empty(len(p))
    for t in range(len(p)):
        R = P + q_ratio; K = R / (R + 1.0)
        m = m + K * (p[t] - m); P = (1 - K) * R; out[t] = m
    return out


def half_life(s: np.ndarray) -> float:
    s = s[~np.isnan(s)]
    if len(s) < 20:
        return np.nan
    lag, d = s[:-1], np.diff(s)
    A = np.column_stack([lag, np.ones_like(lag)])
    b = np.linalg.lstsq(A, d, rcond=None)[0][0]
    return float(-np.log(2) / b) if b < 0 else np.inf


def pair_positions(z: np.ndarray, z0: float, zc: float, delayed: bool, stop_z: float) -> np.ndarray:
    """+1 = long spread (long y, short beta*x), -1 = short spread. Paper rules:
    delayed entry: long when z crosses back UP through -z0, short when it crosses back DOWN through +z0;
    immediate: long when z crosses DOWN through -z0, short when it crosses UP through +z0.
    Exit long when z >= +zc, exit short when z <= -zc (paper: z_c = -0.08 -> close 0.08 sigma past the mean)."""
    pos = np.zeros(len(z)); cur = 0.0
    for t in range(1, len(z)):
        a, b = z[t - 1], z[t]
        if np.isnan(a) or np.isnan(b):
            pos[t] = cur; continue
        if cur == 1 and (b >= zc or (stop_z > 0 and b < -stop_z)):
            cur = 0.0
        elif cur == -1 and (b <= -zc or (stop_z > 0 and b > stop_z)):
            cur = 0.0
        if cur == 0:
            if delayed:
                cur = 1.0 if (a < -z0 <= b) else (-1.0 if (a > z0 >= b) else 0.0)
            else:
                cur = 1.0 if (a > -z0 >= b) else (-1.0 if (a < z0 <= b) else 0.0)
        pos[t] = cur
    return pos


class KalmanPairs(Strategy):
    name = "Paper: Kalman pairs (DTW + cointegration)"
    description = ("Pair trading from the SSRN 5017127 paper. On a formation window: Dynamic-Time-Warping distance between all "
                   "assets -> k-means style clustering (k by silhouette) -> Engle-Granger cointegration test inside each cluster "
                   "(p < 0.05) -> best pairs. Then per pair: Kalman-filter hedge ratio, spread z-score over a half-life window, "
                   "delayed entry at ±1.25σ, exit 0.08σ past the mean. Each pair gets an equal share of capital, dollar-neutral-ish "
                   "(long y, short β·x). Needs several related assets on daily bars, e.g. 'Futures daily, 250 markets'. "
                   "Pick assets that could plausibly move together (metals, grains, energy, equity indices). "
                   "Set 'Per-asset volatility target' irrelevant: positions are sized by the strategy itself.")
    sizing = "raw"
    params = {
        "formation_days": Param(730, 120, 3650, 30, "calendar days used to choose pairs (no trading in the first window)"),
        "reselect_days": Param(365, 0, 3650, 30, "re-run pair selection every N days on the trailing window (0 = choose once, as in the paper)"),
        "max_pairs": Param(10, 1, 50, 1, "trade at most this many pairs (lowest cointegration p-value first)"),
        "p_value": Param(0.05, 0.001, 0.2, 0.005, "Engle-Granger significance level"),
        "use_clustering": Param(True, help="DTW + k-medoids clustering first (paper); off = test every pair"),
        "k_max": Param(6, 2, 12, 1, "largest number of clusters tried (silhouette picks k)"),
        "z_entry": Param(1.25, 0.25, 4.0, 0.05, "paper: 1.25"),
        "z_exit": Param(0.08, -1.0, 1.0, 0.02, "close when z passes this far beyond the mean (paper: 0.08)"),
        "entry_mode": Param("delayed (paper)", choices=("delayed (paper)", "immediate")),
        "stop_z": Param(0.0, 0.0, 10.0, 0.5, "close if the spread runs further than this many sigma (0 = no stop, as in the paper)"),
        "kalman_delta": Param(0.0001, 0.000001, 0.1, 0.0001, "hedge-ratio adaptation speed (paper does not publish it)"),
        "kalman_tau": Param(0.001, 0.000001, 1.0, 0.0005, "measurement noise of the hedge regression (normalised prices)"),
        "smooth_prices": Param(True, help="causal Kalman smoothing of prices before the regression (paper flowchart)"),
        "min_window": Param(5, 2, 60, 1, "minimum z-score window when the half-life is very short"),
        "max_window": Param(120, 10, 500, 5, "maximum z-score window when the half-life is very long"),
    }

    def signal(self, bars, p):
        C = bars.close.ffill(limit=5)
        idx = C.index
        out = pd.DataFrame(0.0, index=idx, columns=bars.symbols)
        F = pd.Timedelta(days=int(p["formation_days"]))
        first = idx[0] + F
        if first > idx[-1]:
            self.info = pd.DataFrame(); return out
        R = int(p["reselect_days"])
        epochs = [first] if R <= 0 else list(pd.date_range(first, idx[-1], freq=pd.Timedelta(days=R)))
        rows = []
        for k, T in enumerate(epochs):
            T_end = epochs[k + 1] if k + 1 < len(epochs) else idx[-1] + pd.Timedelta(seconds=1)
            form = C.loc[(idx >= T - F) & (idx < T)]
            ok = form.columns[(form.notna().mean() > 0.95) & (form.iloc[0].notna()) & (form.iloc[-1].notna())]
            if len(ok) < 2:
                continue
            Pn = (form[ok].ffill().bfill() / form[ok].ffill().bfill().iloc[0])
            labels, kk, sil = cluster_assets(Pn, int(p["k_max"])) if p["use_clustering"] else (np.zeros(len(ok), dtype=int), 1, np.nan)
            cand = []
            for c in set(labels):
                mem = [ok[i] for i in np.where(labels == c)[0]]
                for i in range(len(mem)):
                    for j in range(i + 1, len(mem)):
                        a, b = mem[i], mem[j]
                        p1 = engle_granger(Pn[a].to_numpy(), Pn[b].to_numpy()); p2 = engle_granger(Pn[b].to_numpy(), Pn[a].to_numpy())
                        y, x, pv = (a, b, p1) if p1 <= p2 else (b, a, p2)
                        if pv < p["p_value"]:
                            cand.append((pv, y, x, int(c)))
            cand = sorted(cand)[: int(p["max_pairs"])]
            if not cand:
                rows.append({"epoch": T.date(), "pair": "(no cointegrated pair)", "p_value": np.nan, "cluster": np.nan, "half_life": np.nan,
                             "clusters_k": kk})
                continue
            seg = (idx >= T - F) & (idx < T_end)
            trade = (idx[seg] >= T)
            for pv, y, x, c in cand:
                ys = C.loc[seg, y].ffill().to_numpy(); xs = C.loc[seg, x].ffill().to_numpy()
                y0, x0 = ys[0], xs[0]
                yn, xn = ys / y0, xs / x0
                if p["smooth_prices"]:
                    yk, xk = kalman_level(yn, 0.01), kalman_level(xn, 0.01)
                else:
                    yk, xk = yn, xn
                beta = kalman_beta(yk, xk, float(p["kalman_delta"]), float(p["kalman_tau"]))
                spread = yk - beta * xk
                hl = half_life(spread[~trade])
                win = int(np.clip(round(hl) if np.isfinite(hl) else p["max_window"], p["min_window"], p["max_window"]))
                s = pd.Series(spread)
                z = ((s - s.rolling(win).mean()) / s.rolling(win).std()).to_numpy()
                pos = pair_positions(z, float(p["z_entry"]), float(p["z_exit"]), p["entry_mode"].startswith("delayed"), float(p["stop_z"]))
                pos[~trade] = 0.0
                if k + 1 < len(epochs):
                    pos[-1] = 0.0                                          # flat at the end of each selection epoch
                gross = yn + np.abs(beta) * xn
                wy, wx = pos * yn / gross, -pos * beta * xn / gross
                sl = idx[seg]
                out.loc[sl, y] += wy / len(cand)
                out.loc[sl, x] += wx / len(cand)
                rows.append({"epoch": T.date(), "pair": f"{y} / {x}", "p_value": round(pv, 4), "cluster": c, "half_life": round(hl, 1),
                             "z_window": win, "clusters_k": kk, "trades": int(((np.diff(pos) != 0) & (pos[1:] != 0)).sum())})
        self.info = pd.DataFrame(rows)
        return out.fillna(0.0)


# =====================================================================================================================
# MaxAI: Chaikin money flow state + tabular Q-learning, stop-loss / profit-target, cash session
# =====================================================================================================================
ACTS = np.array([0.0, 1.0, -1.0])          # index 0 = neutral, so ties (untrained states) default to flat


def chaikin_money_flow(h, lo, c, v, n=20):
    rng = (h - lo)
    mfm = (((c - lo) - (h - c)) / rng.where(rng > 0)).fillna(0.0)
    v = v.where(v > 0)
    v = v.fillna(1.0) if v.notna().sum() > 0.5 * len(v) else pd.Series(1.0, index=c.index)
    return (mfm * v).rolling(n).sum() / v.rolling(n).sum()


def _q_train(states, rets, tradable, n_states, alpha, gamma, eps, iters, cost_bps, seed):
    rng = np.random.default_rng(seed)
    Q = np.zeros((n_states, 3)); visits = np.zeros(n_states)
    n = len(states)
    for _ in range(iters):
        u, ra = rng.random(n), rng.integers(0, 3, n)
        prev = 0.0
        for t in range(n - 1):
            if not tradable[t]:
                prev = 0.0; continue
            s, s2 = states[t], states[t + 1]
            a = ra[t] if u[t] < eps else int(np.argmax(Q[s]))
            pos = ACTS[a]
            r = pos * rets[t + 1] * 1e4 - cost_bps * abs(pos - prev)          # reward in basis points, net of costs
            target = r + (gamma * Q[s2].max() if tradable[t + 1] else 0.0)
            Q[s, a] += alpha * (target - Q[s, a])
            visits[s] += 1; prev = pos
    return Q, visits


class MaxAIQLearning(Strategy):
    name = "Paper: MaxAI Q-learning (intraday, money flow)"
    description = ("Intraday strategy from the MaxAI paper (NASDAQ futures). State = 20-bar Chaikin Money Flow rounded to 2 decimals; "
                   "actions buy / sell / flat; a tabular Q-learning agent (paper's GA-tuned α=0.12, γ=0.85, ε=0.08) learns which "
                   "action pays in each state from the next bar's return minus costs. It is trained on the first year and then "
                   "only trades data it has never seen (optionally retrained walk-forward). Each trade has a stop-loss and a profit "
                   "target (paper: $900 / $1,500 on one NQ ≈ 0.30% / 0.50%), and only the US cash session 9:30-16:00 New York "
                   "is traded. Use 1- to 15-minute bars (e.g. 'US100 CFD, Dukascopy (5-min)'). The paper's own indicator is "
                   "proprietary, so this is a faithful re-implementation, not their exact system. Real NQ cost ≈ 0.2-0.5 bp per side; "
                   "set the cost box accordingly. Leverage 1 = one dollar of index per dollar of equity (1 NQ on $83k ≈ 3.6x).")
    sizing = "raw"
    params = {
        "cmf_n": Param(20, 5, 100, 1, "Chaikin money flow lookback (bars), paper: 20"),
        "state_decimals": Param(2, 1, 2, 1, "rounding of the money-flow state (paper: 2 decimals = 201 states)"),
        "alpha": Param(0.12, 0.01, 1.0, 0.01, "learning rate (paper GA result 0.12)"),
        "gamma": Param(0.85, 0.0, 0.99, 0.01, "discount factor (paper 0.85)"),
        "epsilon": Param(0.08, 0.0, 1.0, 0.01, "exploration probability (paper 0.08)"),
        "iterations": Param(1, 1, 20, 1, "passes over the training data (paper: 1)"),
        "train_cost_bps": Param(0.3, 0.0, 20.0, 0.1, "cost per side used inside the reward while learning (paper: $5 per side on NQ ≈ 0.2-0.3 bp)"),
        "min_visits": Param(30, 0, 1000, 5, "states seen fewer times than this in training stay flat"),
        "train_days": Param(365, 30, 2000, 30, "length of each training window (paper: one year, 2021)"),
        "retrain_days": Param(0, 0, 730, 30, "retrain every N days on the trailing window (0 = train once, as in the paper)"),
        "stop_loss_pct": Param(0.30, 0.0, 10.0, 0.05, "exit when the trade loses this % (0 = off). Paper $900 on NQ ≈ 0.30%"),
        "profit_target_pct": Param(0.50, 0.0, 10.0, 0.05, "exit when the trade gains this % (0 = off). Paper $1,500 ≈ 0.50%"),
        "exit_on_neutral": Param(True, help="close the trade when the policy says 'flat' (otherwise only stop / target / reversal / session end)"),
        "session": Param("US cash 9:30-16:00 ET", choices=("US cash 9:30-16:00 ET", "all hours")),
        "allow_short": Param(True, help="paper trades both directions"),
        "seed": Param(7, 0, 10_000, 1, "random seed of the exploration (results vary a little with it)"),
    }

    def signal(self, bars, p):
        out = pd.DataFrame(0.0, index=bars.close.index, columns=bars.symbols)
        info = []
        for s in bars.symbols:
            c = bars.close[s].dropna()
            if len(c) < 100:
                continue
            res = self._one(c, bars.high[s].reindex(c.index), bars.low[s].reindex(c.index), bars.volume[s].reindex(c.index), bars.freq, p)
            out.loc[c.index, s] = res[0]
            info += [{"asset": s, **r} for r in res[1]]
        self.info = pd.DataFrame(info)
        return out / max(1, len(bars.symbols))

    def _one(self, c, h, lo, v, freq, p):
        idx = c.index
        m = chaikin_money_flow(h.fillna(c), lo.fillna(c), c, v, int(p["cmf_n"]))
        scale = 10 ** int(p["state_decimals"])
        states = np.nan_to_num((m.clip(-1, 1).round(int(p["state_decimals"])) * scale + scale).to_numpy(), nan=scale).astype(int)
        n_states = 2 * scale + 1
        rets = c.pct_change().fillna(0).to_numpy()
        # tradable[t]: a position decided at the close of t may be held over bar t+1
        if p["session"].startswith("US") and freq != "1d":
            bar_min = 1440 // BPD.get(freq, 24)
            ny = idx.tz_localize("UTC").tz_convert("America/New_York")
            mins = ny.hour * 60 + ny.minute
            insess = (mins >= 570) & (mins + bar_min <= 960) & (ny.weekday < 5)
            nxt = np.append(insess[1:], False)
            same_day = np.append(ny.date[1:] == ny.date[:-1], False)
            tradable = insess & nxt & same_day
        else:
            tradable = np.ones(len(idx), bool); tradable[-1] = False
        tradable &= ~np.isnan(m.to_numpy())

        T = pd.Timedelta(days=int(p["train_days"])); Rd = int(p["retrain_days"])
        starts = [idx[0] + T] if Rd <= 0 else list(pd.date_range(idx[0] + T, idx[-1], freq=pd.Timedelta(days=Rd)))
        action = np.zeros(len(idx)); info = []
        for k, t0 in enumerate(starts):
            if t0 > idx[-1]:
                break
            t1 = starts[k + 1] if k + 1 < len(starts) else idx[-1] + pd.Timedelta(seconds=1)
            tr = (idx >= t0 - T) & (idx < t0)
            ii = np.where(tr)[0]
            if len(ii) < 200:
                continue
            Q, vis = _q_train(states[ii], rets[ii], tradable[ii] & (np.arange(len(ii)) < len(ii) - 1), n_states, float(p["alpha"]),
                              float(p["gamma"]), float(p["epsilon"]), int(p["iterations"]), float(p["train_cost_bps"]), int(p["seed"]) + k)
            pol = ACTS[np.argmax(Q, axis=1)]
            pol[vis < p["min_visits"]] = 0.0
            if not p["allow_short"]:
                pol[pol < 0] = 0.0
            ap = (idx >= t0) & (idx < t1)
            action[ap] = pol[states[ap]]
            lv = np.round(np.arange(n_states) / scale - 1, 2)
            info.append({"trained_on": f"{(t0 - T).date()} .. {t0.date()}", "traded": f"{t0.date()} .. {min(t1, idx[-1]).date()}",
                         "buy_states": int((pol > 0).sum()), "sell_states": int((pol < 0).sum()),
                         "buy_money_flow_range": f"{lv[pol > 0].min():+.2f} .. {lv[pol > 0].max():+.2f}" if (pol > 0).any() else "-",
                         "sell_money_flow_range": f"{lv[pol < 0].min():+.2f} .. {lv[pol < 0].max():+.2f}" if (pol < 0).any() else "-"})
        pos = _with_exits(action, c.to_numpy(), tradable, float(p["stop_loss_pct"]) / 100, float(p["profit_target_pct"]) / 100,
                          bool(p["exit_on_neutral"]))
        return pos, info


def _with_exits(action, close, tradable, sl, pt, exit_on_neutral):
    """Turn the per-bar policy into positions with stop-loss / profit-target (checked on bar closes) and session exits.
    After a stop or target the strategy waits until the policy changes its mind before entering again."""
    pos = np.zeros(len(action)); cur, entry, locked = 0.0, np.nan, 0.0
    for t in range(len(action)):
        a = action[t]
        if not tradable[t]:
            cur, locked = 0.0, 0.0; continue
        if a != locked:
            locked = 0.0
        if cur != 0:
            r = cur * (close[t] / entry - 1)
            if (sl > 0 and r <= -sl) or (pt > 0 and r >= pt):
                locked, cur = cur, 0.0
            elif a == -cur:
                cur, entry = a, close[t]
            elif a == 0 and exit_on_neutral:
                cur = 0.0
        if cur == 0 and a != 0 and a != locked:
            cur, entry = a, close[t]
        pos[t] = cur
    return pos


# =====================================================================================================================
# Intraday momentum papers on US index futures / ETFs (US cash session, New York time)
# =====================================================================================================================
def ny_session(idx: pd.DatetimeIndex, freq: str) -> pd.DataFrame:
    """Per bar (UTC-naive, labelled by open time): New York date, bar end in minutes after midnight, cash-session flag,
    and whether it is the day's last session bar (a position must be flat after it)."""
    bar_min = 1440 // BPD.get(freq, 24)
    ny = idx.tz_localize("UTC").tz_convert("America/New_York")
    start = ny.hour * 60 + ny.minute
    end = start + bar_min
    f = pd.DataFrame({"date": ny.date, "end": end, "insess": (start >= 570) & (end <= 960) & (ny.weekday < 5)}, index=idx)
    s = f[f.insess]
    last = s.groupby("date")["end"].transform("max") == s["end"]
    f["last"] = False; f.loc[s.index, "last"] = last.to_numpy()
    f["bar_min"] = bar_min
    return f


def _prev_session_close(c: pd.Series, f: pd.DataFrame) -> pd.Series:
    """Per NY date: the previous trading day's last cash-session close (16:00)."""
    s = f[f.insess]
    close_by_day = c.loc[s.index][s["last"].to_numpy()].groupby(s["date"][s["last"]].to_numpy()).last()
    return close_by_day.shift(1)


class IntradayMomentumGao(Strategy):
    name = "Paper: Market intraday momentum (Gao et al. 2018)"
    description = ("Gao, Han, Li & Zhou (2018), 'Market Intraday Momentum', Journal of Financial Economics. The first half hour's "
                   "return (yesterday's 16:00 close -> today 10:00 New York, so it includes the overnight move) predicts the "
                   "last half hour. At 15:30 go long if that return was positive, short if negative; close at 16:00. Optional: "
                   "only trade when the 15:00-15:30 return points the same way (the paper's second predictor). One trade per "
                   "day of 30 minutes. Needs 5-, 15- or 30-minute bars of a US index (e.g. 'US500 CFD, Dukascopy (15-min)'). "
                   "Paper: SPY 1993-2013, about 6.7% a year, Sharpe ~1.08 before costs; weaker after 2008 in later studies.")
    sizing = "raw"
    params = {
        "mode": Param("first half hour", choices=("first half hour", "first + 12th half hour agree")),
        "min_move_pct": Param(0.0, 0.0, 2.0, 0.05, "skip days when the first-half-hour move is smaller than this (%)"),
        "allow_short": Param(True),
    }

    def signal(self, bars, p):
        out = pd.DataFrame(0.0, index=bars.close.index, columns=bars.symbols); info = []
        if 30 % (1440 // BPD.get(bars.freq, 24)) != 0:
            self.info = pd.DataFrame([{"note": "needs 5-, 15- or 30-minute bars"}]); return out
        f = ny_session(bars.close.index, bars.freq)
        for s in bars.symbols:
            c = bars.close[s]
            pc = _prev_session_close(c, f)
            ses = f[f.insess]
            at = lambda m: c.loc[ses.index][(ses["end"] == m).to_numpy()].groupby(ses["date"][ses["end"] == m].to_numpy()).last()
            r1 = at(600) / pc.reindex(at(600).index) - 1
            r12 = at(930) / at(900).reindex(at(930).index) - 1
            sig = np.sign(r1).where(r1.abs() * 100 >= p["min_move_pct"], 0.0)
            if p["mode"].startswith("first +"):
                sig = sig.where(np.sign(r12.reindex(sig.index)) == sig, 0.0)
            if not p["allow_short"]:
                sig = sig.clip(lower=0)
            hold = f.insess & (f["end"] >= 930) & ~f["last"]                 # decided at the 15:30 close, flat after 16:00
            out.loc[hold, s] = pd.Series(f.loc[hold, "date"].map(sig).to_numpy(), index=f.index[hold]).fillna(0.0).to_numpy()
            info.append({"asset": s, "days": int(sig.notna().sum()), "long_days": int((sig > 0).sum()), "short_days": int((sig < 0).sum()),
                         "hit_rate_of_r1_sign": round(float((np.sign(r1) == np.sign(at(960) / at(930).reindex(at(960).index) - 1)
                                                           .reindex(r1.index)).mean()), 3)})
        self.info = pd.DataFrame(info)
        return out / max(1, len(bars.symbols))


class NoiseAreaMomentum(Strategy):
    name = "Paper: Beat the Market noise-area breakout (Zarattini et al. 2024)"
    description = ("Zarattini, Aziz & Barbon (2024), 'Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)', "
                   "SSRN 4824172. Each day a 'noise area' is drawn around the open: for every time of day, the average absolute "
                   "move from the open at that time over the last 14 days. Every 30 minutes from 10:00 New York: go long when "
                   "price closes above the upper boundary, short below the lower one. Exit at the opposite trailing stop "
                   "(boundary or VWAP, whichever is tighter) or at 16:00. Position size targets 2% daily volatility (max 4x). "
                   "Paper: SPY 2007-2024, Sharpe 1.33 after costs. Use 5- or 15-minute bars of a US index "
                   "(e.g. 'US500 CFD, Dukascopy (15-min)'). Leverage 1 in the sidebar = the paper's sizing.")
    sizing = "raw"
    params = {
        "lookback_days": Param(14, 5, 60, 1, "days averaged for the noise area (paper: 14)"),
        "band_mult": Param(1.0, 0.25, 3.0, 0.05, "noise-area width multiplier (paper: 1.0)"),
        "check_minutes": Param(30, 5, 60, 5, "check for entries / exits every N minutes (paper: 30)"),
        "vwap_stop": Param(True, help="trail the stop at VWAP when it is tighter than the boundary (paper: yes)"),
        "vol_sizing": Param(True, help="size = 2% / daily volatility (14 days), capped (paper: yes); off = always 1x"),
        "target_daily_vol_pct": Param(2.0, 0.25, 5.0, 0.25, "paper: 2%"),
        "max_leverage": Param(4.0, 0.5, 10.0, 0.5, "paper: 4"),
        "allow_short": Param(True),
    }

    def signal(self, bars, p):
        out = pd.DataFrame(0.0, index=bars.close.index, columns=bars.symbols); info = []
        bm = 1440 // BPD.get(bars.freq, 24)
        if bm > 30 or int(p["check_minutes"]) % bm:
            self.info = pd.DataFrame([{"note": "needs bars of 30 minutes or less that divide the check interval"}]); return out
        f = ny_session(bars.close.index, bars.freq)
        for s in bars.symbols:
            pos, n_tr = self._one(bars, s, f, p)
            out[s] = pos
            info.append({"asset": s, "trades": n_tr, "avg_abs_position": round(float(np.abs(pos[pos != 0]).mean()), 2) if (pos != 0).any() else 0})
        self.info = pd.DataFrame(info)
        return out / max(1, len(bars.symbols))

    def _one(self, bars, s, f, p):
        c, o, h, lo, v = (getattr(bars, k)[s] for k in ("close", "open", "high", "low", "volume"))
        ses = f[f.insess & c.notna()]
        idx = ses.index
        cc = c.loc[idx].to_numpy(); date = ses["date"].to_numpy(); end = ses["end"].to_numpy(); bm = int(ses["bar_min"].iloc[0])
        first = ses["end"] == 570 + bm
        day_open = pd.Series(o.loc[idx][first.to_numpy()].to_numpy(), index=date[first.to_numpy()])
        day_open = day_open[~day_open.index.duplicated()]
        pc = _prev_session_close(c, f)
        dopen = pd.Series(date).map(day_open).to_numpy(); dprev = pd.Series(date).map(pc).to_numpy()
        # noise area: mean |close/open - 1| at the same time of day over the previous N days
        move = pd.DataFrame({"d": date, "t": end, "m": np.abs(cc / dopen - 1)})
        piv = move.pivot_table(index="d", columns="t", values="m", aggfunc="last")
        sig = piv.rolling(int(p["lookback_days"]), min_periods=int(p["lookback_days"])).mean().shift(1)
        sigma = sig.stack().reindex(pd.MultiIndex.from_arrays([date, end])).to_numpy()
        ub = np.maximum(dopen, dprev) * (1 + p["band_mult"] * sigma)
        lb = np.minimum(dopen, dprev) * (1 - p["band_mult"] * sigma)
        # VWAP since the open (tick volume for CFDs; equal weights if no volume)
        tp = ((h + lo + c) / 3).loc[idx].to_numpy()
        vv = v.loc[idx].to_numpy(); vv = np.where(np.isfinite(vv) & (vv > 0), vv, 1.0)
        g = pd.Series(date)
        vwap = (pd.Series(tp * vv).groupby(g).cumsum() / pd.Series(vv).groupby(g).cumsum()).to_numpy()
        # size: target daily vol / 14-day realised daily vol (session closes), known before the day starts
        dclose = pd.Series(cc[ses["last"].to_numpy()], index=date[ses["last"].to_numpy()])
        dvol = dclose.pct_change().rolling(14).std().shift(1)
        lev = (p["target_daily_vol_pct"] / 100 / dvol).clip(upper=p["max_leverage"]) if p["vol_sizing"] else dvol * 0 + 1.0
        dlev = pd.Series(date).map(lev).to_numpy()
        last = ses["last"].to_numpy(); chk = ((end - 570) % int(p["check_minutes"]) == 0) & (end >= 600)
        pos = np.zeros(len(idx)); cur = 0.0; trades = 0
        for t in range(len(idx)):
            if np.isnan(sigma[t]) or np.isnan(dprev[t]) or np.isnan(dlev[t]):
                cur = 0.0
            elif chk[t]:
                up, dn = (max(ub[t], vwap[t]), min(lb[t], vwap[t])) if p["vwap_stop"] else (ub[t], lb[t])
                if cur > 0 and cc[t] < up:
                    cur = 0.0
                elif cur < 0 and cc[t] > dn:
                    cur = 0.0
                if cur == 0:
                    if cc[t] > ub[t]:
                        cur = 1.0; trades += 1
                    elif cc[t] < lb[t] and p["allow_short"]:
                        cur = -1.0; trades += 1
            if last[t]:
                cur = 0.0
            pos[t] = cur * (dlev[t] if np.isfinite(dlev[t]) else 0.0)
        return pd.Series(pos, index=idx).reindex(bars.close.index).fillna(0.0), trades
