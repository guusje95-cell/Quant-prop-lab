"""V7: walk-forward L2-logistic model on hourly NQ decision points (reusable module).

Decision points: closes of 15-minute RTH bars ending at 10:00, 11:00, ..., 15:00 ET.
Trade: first decision point of the day where p > 0.5 + thr (long) or p < 0.5 - thr (short);
enter at the next bar open, hold to the 16:00 close (one trade per day). All features use only
information available at the decision bar's close; daily features are as-of the prior session.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..features.intraday import asof_prior
from . import v3_intraday as V

FEATS = ["z_move", "gap", "pret", "eff", "rvr", "rel", "twap_dev", "slot", "dow"]


def features(c: pd.DataFrame, e: pd.DataFrame, bar_min: int = 15) -> pd.DataFrame:
    """c: prepared NQ context, e: prepared ES context (same bar size)."""
    sig, _ = V._tod_sigma(c, 14)
    tw = V._twap(c)
    C, O = c.close.to_numpy(), c.open.to_numpy()
    op, pc, atr = c.rth_open.to_numpy(), c.prev_rth_close.to_numpy(), c.atr_d.to_numpy()
    et = c.et_min.to_numpy(); date = c["date"].to_numpy()
    rthv = (c.rth & c.valid_day).to_numpy()
    ecl = e.close.reindex(c.index).to_numpy(); eop = e.rth_open.reindex(c.index).to_numpy()
    t = V.daily_rth_table(c)
    eff = (t.close.diff(10).abs() / t.close.diff().abs().rolling(10).sum())
    rvr = t.close.pct_change().rolling(5).std() / t.close.pct_change().rolling(20).std()
    pret = t.close.pct_change()
    f_eff, f_rvr, f_pret = (asof_prior(s, date) for s in (eff, rvr, pret))
    last = 960 - bar_min
    close16 = pd.Series(C[(et == last) & rthv], index=date[(et == last) & rthv])
    close16 = close16[~close16.index.duplicated()]
    c16 = pd.Series(date).map(close16).to_numpy()            # LABEL ONLY (future); never a feature
    nxt_open = np.r_[O[1:], np.nan]
    dec = rthv & ((et + bar_min) % 60 == 0) & (et + bar_min >= 600) & (et + bar_min <= 900)
    D = pd.DataFrame({
        "date": date, "slot": (et + bar_min) // 60,
        "z_move": (C / op - 1) / sig, "gap": (op - pc) / atr, "pret": f_pret * 100, "eff": f_eff, "rvr": f_rvr,
        "rel": np.log(C / op) - np.log(ecl / eop), "twap_dev": (C - tw) / (op * sig), "dow": c.dow.to_numpy(),
        "y_ret": (c16 - nxt_open) / nxt_open, "entry": nxt_open}, index=c.index)[dec]
    D["year"] = pd.DatetimeIndex(D["date"]).year
    return D


def model(C: float = 0.1):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=500))


def walk_forward(D: pd.DataFrame, first_year: int = 2016, last_year: int = 2023, C: float = 0.1) -> tuple[pd.Series, dict]:
    """Expanding-window yearly refit (train on all years < Y, whole-year embargo is implicit)."""
    D = D.dropna(subset=FEATS + ["y_ret"])
    preds, coefs = [], {}
    for Y in range(first_year, last_year + 1):
        tr, te = D[D.year < Y], D[D.year == Y]
        if len(te) == 0:
            continue
        m = model(C).fit(tr[FEATS], (tr.y_ret > 0).astype(int))
        preds.append(pd.Series(m.predict_proba(te[FEATS])[:, 1], index=te.index))
        coefs[Y] = dict(zip(FEATS, m[-1].coef_[0].round(3)))
    return pd.concat(preds), coefs


def trades(D: pd.DataFrame, p: pd.Series, thr: float) -> pd.DataFrame:
    Dt = D.loc[p.index].copy()
    Dt["p"] = p
    Dt["pos"] = np.where(Dt.p > 0.5 + thr, 1, np.where(Dt.p < 0.5 - thr, -1, 0))
    return Dt[Dt.pos != 0].groupby("date").head(1)


def daily_usd(first: pd.DataFrame, days, ref=19900.0, pv=20.0, slip_pts=0.25, comm=2.80, cost_mult=1.0) -> pd.Series:
    """Deployment-normalized USD P&L per NQ contract (entry next open, exit 16:00 close, 1 tick/side)."""
    cost_r = cost_mult * (2 * slip_pts + comm / pv) / ref
    pnl = (first.pos * first.y_ret - cost_r) * ref * pv
    return pnl.groupby(pd.DatetimeIndex(first["date"])).sum().reindex(days, fill_value=0.0)
