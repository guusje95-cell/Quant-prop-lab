"""General prop-firm challenge + funded-account simulator for the Backtest Lab.

Input: a strategy's DAILY results (fractions of equity): net, worst (intraday low vs previous close) and best (intraday high).
A firm is a set of rules (`Firm`): profit target per phase, daily loss limit (on start-of-day equity, or a fixed % of the
initial balance), maximum loss (static, trailing, or trailing that stops at the starting balance; trailing from intraday
highs or end-of-day), minimum trading days, fee, profit split, payout cadence. Presets are approximations of public rules
(check the firm's site before buying); every field can be edited in the app.

Two questions are answered:
1. attempts(): if I start a challenge on day X, how often do I pass, fail on the daily loss, fail on the max loss, or not
   finish? (every historical start date, or block-bootstrapped paths)
2. pipeline(): with a budget of N challenges (re-buy after a fail or a funded breach) and K identical accounts in parallel,
   what do I pay, what do I get paid, and what is left after the horizon (distribution over start dates)?

Conservative choices: an intraday-trailing high is taken BEFORE the day's low (high first, then low); the max loss is
checked against the intraday low; a payout happens only on a payout day with equity above the start."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

import numpy as np
import pandas as pd

PASS, FAIL_DAILY, FAIL_MAX, FAIL_TIME, OPEN = "pass", "fail: daily loss", "fail: max loss", "fail: time limit", "not finished"


@dataclass
class Firm:
    name: str = "Custom"
    account: float = 100_000.0
    fee: float = 500.0                     # per challenge attempt (USD)
    targets: tuple = (0.10,)               # profit target per phase, fraction of the account
    daily_loss: float = 0.05               # 0 = no daily loss limit
    daily_basis: str = "day_start"         # "day_start": % of start-of-day equity; "initial": % of initial balance below start of day
    daily_intraday: bool = True            # equity incl. intraday lows (True) or closed day result only
    max_loss: float = 0.10
    max_type: str = "static"               # "static" | "trailing" | "trailing_lock" (stops trailing at the starting balance)
    trailing_intraday: bool = True         # trail from intraday highs (True) or end-of-day equity
    min_days: int = 0                      # minimum trading days per phase
    max_days: int = 0                      # calendar days per phase, 0 = unlimited
    split: float = 0.80
    payout_every: int = 30                 # calendar days between payouts when funded
    payout_fee: float = 0.0                # fraction lost per payout (processing / crypto fees)
    refund_fee: bool = False               # challenge fee refunded with the first payout
    funded_fee: float = 0.0                # one-off activation fee when funded
    note: str = ""
    fee_monthly: bool = False              # fee is a subscription: charged again every 30 days while in the challenge


PRESETS = {
    "Crypto Fund Trader 1-Phase $100k": Firm("CFT 1-Phase", 100_000, 798, (0.10,), 0.04, "initial", True, 0.06, "trailing_lock", True,
                                             0, 0, 0.80, 30, 0.05, False, 0.0, "CFT Bybit route; 6% trailing loss stops at the start balance"),
    "Crypto Fund Trader 2-Phase $100k": Firm("CFT 2-Phase", 100_000, 798, (0.08, 0.05), 0.05, "initial", True, 0.10, "static", True,
                                             0, 0, 0.80, 30, 0.05, False, 0.0, "fee: check the current price"),
    "FTMO 2-Step $100k": Firm("FTMO 2-Step", 100_000, 590, (0.10, 0.05), 0.05, "initial", True, 0.10, "static", True,
                              4, 0, 0.80, 14, 0.0, True, 0.0, "€540 ≈ $590; daily loss 5% of initial balance; fee refunded with 1st payout"),
    "Topstep 50k Combine (futures)": Firm("Topstep 50k", 50_000, 49, (0.06,), 0.0, "initial", True, 0.04, "trailing_lock", False,
                                          2, 0, 0.90, 30, 0.0, False, 149.0, "$3,000 target, $2,000 end-of-day trailing loss; $49/month while in the Combine; consistency rule not modelled", True),
    "Apex 50k (futures)": Firm("Apex 50k", 50_000, 167, (0.06,), 0.0, "initial", True, 0.05, "trailing_lock", True,
                               7, 0, 0.90, 30, 0.0, False, 85.0, "$3,000 target, $2,500 intraday trailing; monthly evaluation fee, frequent discounts; payout rules simplified", True),
    "Custom": Firm(),
}


def _arrays(daily: pd.DataFrame, scale: float):
    d = daily[["net", "worst", "best"]].fillna(0.0)
    return (d["net"].to_numpy() * scale, d["worst"].to_numpy() * scale, d["best"].to_numpy() * scale)


def _days(index) -> np.ndarray:
    return ((pd.DatetimeIndex(index) - pd.DatetimeIndex(index)[0]).days).to_numpy()


def _phase(r, lo, hi, cal, t, end, target, f: Firm):
    """Trade one evaluation phase from row t. Returns (result, next row)."""
    E = 1.0; hwm = 1.0; traded = 0; t0 = cal[t] if t < end else 0
    for j in range(t, end):
        if f.max_days and cal[j] - t0 >= f.max_days:
            return FAIL_TIME, j
        D = E
        if f.max_type != "static" and f.trailing_intraday:
            hwm = max(hwm, D * (1 + hi[j]))
        low, close = D * (1 + lo[j]), D * (1 + r[j])
        if f.daily_loss > 0:
            lvl = D * (1 - f.daily_loss) if f.daily_basis == "day_start" else D - f.daily_loss
            if (low if f.daily_intraday else close) < lvl:
                return FAIL_DAILY, j + 1
        floor = 1 - f.max_loss if f.max_type == "static" else (hwm - f.max_loss if f.max_type == "trailing" else min(hwm - f.max_loss, 1.0))
        if low < floor:
            return FAIL_MAX, j + 1
        E = close
        if f.max_type != "static" and not f.trailing_intraday:
            hwm = max(hwm, E)
        traded += abs(r[j]) > 1e-12 or abs(lo[j]) > 1e-12
        if E >= 1 + target and traded >= f.min_days:
            return PASS, j + 1
    return OPEN, end


def _challenge(r, lo, hi, cal, t, end, f: Firm):
    for tgt in f.targets:
        res, t = _phase(r, lo, hi, cal, t, end, tgt, f)
        if res != PASS:
            return res, t
    return PASS, t


def _paths(daily: pd.DataFrame, method: str, horizon_days: int, step: int, n_boot: int, block: int, seed: int):
    """Yields (start row, end row, arrays-source) definitions: historical start dates or bootstrapped paths."""
    cal = _days(daily.index)
    if method == "historical":
        starts = [s for s in range(0, len(daily), step) if cal[-1] - cal[s] >= min(horizon_days, 180)]
        return [("hist", s) for s in starts], cal
    rng = np.random.default_rng(seed)
    per_day = max(1e-9, len(daily) / max(1, cal[-1]))
    n = int(horizon_days * per_day) + 5
    out = []
    for _ in range(n_boot):
        idx = np.empty(n, dtype=int); i = rng.integers(len(daily))
        for k in range(n):
            idx[k] = i; i = rng.integers(len(daily)) if rng.random() < 1 / block else (i + 1) % len(daily)
        out.append(("boot", idx))
    return out, cal


def attempts(daily: pd.DataFrame, f: Firm, scale: float = 1.0, method="historical", horizon_days=548, step=3, n_boot=500, block=20, seed=1):
    """Outcome of ONE challenge attempt started on many dates."""
    r0, lo0, hi0 = _arrays(daily, scale)
    paths, cal0 = _paths(daily, method, horizon_days, step, n_boot, block, seed)
    res, days = [], []
    per_day = len(daily) / max(1, cal0[-1])
    for kind, x in paths:
        if kind == "hist":
            r, lo, hi, cal, s = r0, lo0, hi0, cal0, x
            end = int(np.searchsorted(cal, cal[s] + horizon_days))
        else:
            r, lo, hi, s = r0[x], lo0[x], hi0[x], 0
            cal = (np.arange(len(x)) / per_day).astype(int); end = len(x)
        out, t = _challenge(r, lo, hi, cal, s, end, f)
        res.append(out); days.append(cal[min(t, len(cal) - 1)] - cal[s] if out == PASS else np.nan)
    res = np.array(res); days = np.array(days, dtype=float)
    n = max(1, len(res))
    return {"n": len(res), "P_pass": float((res == PASS).mean()) if len(res) else np.nan,
            "P_fail_daily": float((res == FAIL_DAILY).sum() / n), "P_fail_max": float((res == FAIL_MAX).sum() / n),
            "P_fail_time": float((res == FAIL_TIME).sum() / n), "P_open": float((res == OPEN).sum() / n),
            "median_days_to_pass": float(np.nanmedian(days)) if np.isfinite(days).any() else np.nan,
            "p75_days_to_pass": float(np.nanpercentile(days, 75)) if np.isfinite(days).any() else np.nan}


def _ledger(rc, loc, hic, rf, lof, hif, cal, s, end, f: Firm, budget: int):
    cash = np.zeros(end - s); t = s; bought = passed = breaches = npay = 0; refunded = False
    first_pass = first_pay = None; funded_days = 0; extra_fees = 0.0
    while t < end and bought < budget:
        cash[t - s] -= f.fee; bought += 1; t_buy = t
        res, t = _challenge(rc, loc, hic, cal, t, end, f)
        if f.fee_monthly:                                          # subscription renewals while the challenge ran
            extra = int((cal[min(t, end - 1)] - cal[t_buy]) // 30)
            cash[min(t, end - 1) - s] -= extra * f.fee; bought_fees_extra = extra * f.fee
        else:
            bought_fees_extra = 0.0
        extra_fees += bought_fees_extra
        if res != PASS or t >= end:
            continue
        passed += 1
        first_pass = cal[t] - cal[s] if first_pass is None else first_pass
        cash[t - s] -= f.funded_fee
        E = 1.0; hwm = 1.0; last = cal[t]; f_start = cal[t]
        while t < end:
            D = E
            if f.max_type != "static" and f.trailing_intraday:
                hwm = max(hwm, D * (1 + hif[t]))
            low, close = D * (1 + lof[t]), D * (1 + rf[t])
            lvl = (D * (1 - f.daily_loss) if f.daily_basis == "day_start" else D - f.daily_loss) if f.daily_loss > 0 else -np.inf
            floor = 1 - f.max_loss if f.max_type == "static" else (hwm - f.max_loss if f.max_type == "trailing" else min(hwm - f.max_loss, 1.0))
            if (low if f.daily_intraday else close) < lvl or low < floor:
                breaches += 1; funded_days += cal[t] - f_start; t += 1; break
            E = close
            if f.max_type != "static" and not f.trailing_intraday:
                hwm = max(hwm, E)
            if cal[t] - last >= f.payout_every:
                last = cal[t]
                if E > 1.0:
                    pay = (E - 1.0) * f.account * f.split * (1 - f.payout_fee)
                    if f.refund_fee and not refunded:
                        pay += f.fee; refunded = True
                    cash[t - s] += pay; npay += 1; first_pay = cal[t] - cal[s] if first_pay is None else first_pay
                    E = 1.0; hwm = 1.0
            t += 1
        else:
            funded_days += cal[end - 1] - f_start
    w = np.cumsum(cash)
    return {"wealth": w, "bought": bought, "passed": passed, "breaches": breaches, "payouts": npay, "fees": bought * f.fee + passed * f.funded_fee + extra_fees,
            "paid": float(cash[cash > 0].sum()), "net": float(w[-1]) if len(w) else 0.0, "first_pass": first_pass, "first_pay": first_pay,
            "funded_days": funded_days}


def pipeline(daily_ch: pd.DataFrame, f: Firm, budget=5, accounts=1, scale_c=1.0, scale_f=0.5, daily_fd: pd.DataFrame | None = None,
             horizon_days=730, method="historical", step=5, n_boot=500, block=20, seed=2):
    """Buy up to `budget` challenges over `horizon_days` (re-buy after any fail or funded breach), trade the funded account at
    `scale_f` x the backtest risk and take payouts. `accounts` identical accounts run in parallel: they trade the same signals,
    so they pass and fail TOGETHER; every money amount is simply multiplied (no diversification)."""
    fd = daily_ch if daily_fd is None else daily_fd.reindex(daily_ch.index).fillna(0.0)
    rc0, loc0, hic0 = _arrays(daily_ch, scale_c); rf0, lof0, hif0 = _arrays(fd, scale_f)
    paths, cal0 = _paths(daily_ch, method, horizon_days, step, n_boot, block, seed)
    per_day = len(daily_ch) / max(1, cal0[-1]); runs = []
    for kind, x in paths:
        if kind == "hist":
            s = x; end = int(np.searchsorted(cal0, cal0[s] + horizon_days))
            if cal0[-1] - cal0[s] < horizon_days * 0.9:
                continue                                             # need (almost) the full horizon of data
            runs.append(_ledger(rc0, loc0, hic0, rf0, lof0, hif0, cal0, s, end, f, budget))
        else:
            cal = (np.arange(len(x)) / per_day).astype(int)
            runs.append(_ledger(rc0[x], loc0[x], hic0[x], rf0[x], lof0[x], hif0[x], cal, 0, len(x), f, budget))
    if not runs:
        return {"n": 0}
    L = max(len(r["wealth"]) for r in runs)
    W = np.vstack([np.pad(r["wealth"], (0, L - len(r["wealth"])), "edge") for r in runs]) * accounts
    net = np.array([r["net"] for r in runs]) * accounts
    months = horizon_days / 30.4
    fp = np.array([r["first_pass"] if r["first_pass"] is not None else np.nan for r in runs], dtype=float)
    fpay = np.array([r["first_pay"] if r["first_pay"] is not None else np.nan for r in runs], dtype=float)
    return {"n": len(runs), "accounts": accounts, "P_funded": float(np.mean([r["passed"] > 0 for r in runs])),
            "P_payout": float(np.mean([r["payouts"] > 0 for r in runs])),
            "bought": float(np.mean([r["bought"] for r in runs])) * accounts, "fees": float(np.mean([r["fees"] for r in runs])) * accounts,
            "paid": float(np.mean([r["paid"] for r in runs])) * accounts, "payouts_n": float(np.mean([r["payouts"] for r in runs])),
            "funded_breaches": float(np.mean([r["breaches"] for r in runs])),
            "net_mean": float(net.mean()), "net_p10": float(np.percentile(net, 10)), "net_p50": float(np.percentile(net, 50)),
            "net_p90": float(np.percentile(net, 90)), "P_profit": float((net > 0).mean()), "P_lose_all_budget": float(np.mean([r["passed"] == 0 for r in runs])),
            "net_per_month": float(net.mean() / months),
            "days_to_funded_median": float(np.nanmedian(fp)) if np.isfinite(fp).any() else np.nan,
            "days_to_first_payout_median": float(np.nanmedian(fpay)) if np.isfinite(fpay).any() else np.nan,
            "curve": pd.DataFrame({"p10": np.percentile(W, 10, axis=0), "p50": np.percentile(W, 50, axis=0),
                                   "p90": np.percentile(W, 90, axis=0), "mean": W.mean(axis=0)}),
            "per_day": per_day}


def firm_from_dict(d: dict) -> Firm:
    d = dict(d); d["targets"] = tuple(d["targets"])
    return Firm(**d)


__all__ = ["Firm", "PRESETS", "attempts", "pipeline", "firm_from_dict", "asdict", "replace", "field"]
