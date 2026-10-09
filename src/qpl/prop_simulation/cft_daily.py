"""Crypto Fund Trader evaluation simulation on DAILY (UTC) strategy returns. Rules UNCERTAIN (config/crypto_zoo_protocol.json).

2PHASE: targets 8% then 5% (fresh account each phase), daily loss 5%, max loss 10% static of initial.
1PHASE: target 10%, daily loss 4%, max loss trailing 6% below peak balance, stops trailing once the floor reaches the initial
        balance (floor = min(peak - 0.06, 1.0)).
Daily loss: equity must stay above B - d, B = balance at 00:05 UTC:
  optimistic   B = previous close equity (P&L effectively realised daily)
  conservative B = max close equity of the last 10 days (floating losses of positions held for days count against B)
Intraday low proxy = E_{t-1} * (1 + k * min(r_t, 0)), k = 1.5, unless real intraday worst/best returns (lo, hi) are given;
with hi, the trailing peak is raised by the intraday high BEFORE the low is checked (conservative). Funded: monthly withdrawal of split * profit, reset."""
from __future__ import annotations

import numpy as np

PASS, FAIL_MAX, FAIL_DAILY, OPEN = 1, -1, -2, 0
PROGRAMS = {"2PHASE": {"targets": [0.08, 0.05], "daily": 0.05, "max": 0.10, "trailing": False},
            "1PHASE": {"targets": [0.10], "daily": 0.04, "max": 0.06, "trailing": True}}


def _run(r, s, target, daily, mx, trailing, k, mode, max_days, min_days=0, lo=None, hi=None):
    E = 1.0; hist = [1.0]; peak = 1.0
    for j in range(s, min(len(r), s + max_days)):
        x = r[j] if np.isfinite(r[j]) else 0.0
        B = E if mode == "optimistic" else max(hist[-10:])
        low = E * (1 + (lo[j] if lo is not None else k * min(x, 0.0)))
        if hi is not None and trailing:
            peak = max(peak, E * (1 + hi[j]))
        if low < B - daily:
            return FAIL_DAILY, j - s + 1
        floor = min(peak - mx, 1.0) if trailing else 1.0 - mx
        if low < floor:
            return FAIL_MAX, j - s + 1
        E *= 1 + x; hist.append(E); peak = max(peak, E)
        if E >= 1 + target and (j - s + 1) >= min_days:
            return PASS, j - s + 1
    return OPEN, min(len(r) - s, max_days)


def simulate_start(r, s, program="2PHASE", k=1.5, mode="conservative", max_days=730, funded_months=12, split=0.8, lo=None, hi=None):
    P = PROGRAMS[program]; off = s; days = 0; out = {}
    for i, tgt in enumerate(P["targets"]):
        code, d = _run(r, off, tgt, P["daily"], P["max"], P["trailing"], k, mode, max_days - days, lo=lo, hi=hi)
        out[f"p{i + 1}"] = code; days += d; off += d
        if code != PASS:
            out["result"] = code; out["days"] = days; return out
    out["result"] = PASS; out["days"] = days
    # funded (static-style max loss of the program, monthly payouts)
    E = 1.0; hist = [1.0]; peak = 1.0; paid = 0.0; status = "survived"
    for m in range(funded_months):
        for j in range(off + 30 * m, off + 30 * (m + 1)):
            if j >= len(r):
                status = "data_end"; break
            x = r[j] if np.isfinite(r[j]) else 0.0
            B = E if mode == "optimistic" else max(hist[-10:])
            low = E * (1 + (lo[j] if lo is not None else k * min(x, 0.0)))
            if hi is not None and P["trailing"]:
                peak = max(peak, E * (1 + hi[j]))
            floor = min(peak - P["max"], 1.0) if P["trailing"] else 1.0 - P["max"]
            if low < B - P["daily"] or low < floor:
                status = "failed"; break
            E *= 1 + x; hist.append(E); peak = max(peak, E)
        if status != "survived":
            break
        if E > 1.0:
            paid += split * (E - 1.0); E = 1.0; hist = [1.0]; peak = 1.0
    out.update({"payout_frac_12m": paid, "funded_status": status})
    return out


def summarize(res):
    code = np.array([x["result"] for x in res]); days = np.array([x["days"] for x in res])
    ok = code == PASS
    pay = np.array([x.get("payout_frac_12m", 0.0) for x in res])
    return {"n": len(res), "P_pass": round(float(ok.mean()), 3), "P_fail_daily": round(float((code == FAIL_DAILY).mean()), 3),
            "P_fail_max": round(float((code == FAIL_MAX).mean()), 3), "P_unresolved": round(float((code == OPEN).mean()), 3),
            "median_days_to_pass": float(np.median(days[ok])) if ok.any() else None,
            "p25_p75_days_to_pass": [float(np.percentile(days[ok], 25)), float(np.percentile(days[ok], 75))] if ok.any() else None,
            "funded_survive_12m": round(float(np.mean([x.get("funded_status") == "survived" for x in res if x["result"] == PASS])), 3) if ok.any() else None,
            "E_payout_frac_12m_per_attempt": round(float(pay.mean()), 4)}


def pipeline(rc, loc, hic, rf, lof, hif, s, program="2PHASE", fee=0.009, horizon=730, split=0.8, proc=0.05):
    """Gen34 two-speed pipeline from day s for `horizon` days: buy a challenge (fee), trade the challenge series
    (rc, loc, hic) until pass/fail, re-buy after a fail; once funded trade the funded series (rf, lof, hif), withdraw
    split*(1-proc)*profit every 30 days (reset), go back to buying challenges after a funded breach."""
    P = PROGRAMS[program]; mx, daily, trailing = P["max"], P["daily"], P["trailing"]
    end = min(len(rc), s + horizon); t = s; cash = 0.0; attempts = 0; first_funded = None; paid = 0.0; funded_days = 0
    while t < end:
        cash -= fee; attempts += 1; ok = True
        for tgt in P["targets"]:
            code, d = _run(rc, t, tgt, daily, mx, trailing, 1.5, "optimistic", end - t, lo=loc, hi=hic)
            t += d
            if code != PASS:
                ok = False; break
        if not ok:
            continue
        if first_funded is None:
            first_funded = t - s
        E = 1.0; peak = 1.0; alive = True
        while t < end and alive:
            stop = min(t + 30, end)
            for j in range(t, stop):
                x = rf[j] if np.isfinite(rf[j]) else 0.0
                low = E * (1 + lof[j])
                if trailing:
                    peak = max(peak, E * (1 + hif[j]))
                floor = min(peak - mx, 1.0) if trailing else 1.0 - mx
                if low < E - daily or low < floor:
                    alive = False; funded_days += j + 1 - t; t = j + 1; break
                E *= 1 + x; peak = max(peak, E)
            if alive:
                funded_days += stop - t; t = stop
                if E > 1.0:
                    pay = split * (1 - proc) * (E - 1.0); cash += pay; paid += pay; E = 1.0; peak = 1.0
    return {"net": cash, "paid": paid, "attempts": attempts, "first_funded_days": first_funded, "funded_days": funded_days,
            "horizon_days": end - s}


def summarize_pipeline(res):
    net = np.array([x["net"] for x in res]); ff = [x["first_funded_days"] for x in res]
    got = np.array([f is not None for f in ff]); ffd = np.array([f for f in ff if f is not None], float)
    return {"n": len(res), "mean_net": round(float(net.mean()), 4), "median_net": round(float(np.median(net)), 4),
            "p10_net": round(float(np.percentile(net, 10)), 4), "P_net_pos": round(float((net > 0).mean()), 3),
            "mean_attempts": round(float(np.mean([x["attempts"] for x in res])), 2),
            "P_funded_ever": round(float(got.mean()), 3),
            "median_months_to_funded": round(float(np.median(ffd)) / 30.4, 1) if got.any() else None,
            "P_funded_within_90d": round(float(np.mean([f is not None and f <= 90 for f in ff])), 3),
            "P_funded_within_180d": round(float(np.mean([f is not None and f <= 180 for f in ff])), 3),
            "mean_paid": round(float(np.mean([x["paid"] for x in res])), 4)}
