"""Crypto Fund Trader evaluation simulation on DAILY (UTC) strategy returns. Rules UNCERTAIN (config/crypto_zoo_protocol.json).

2PHASE: targets 8% then 5% (fresh account each phase), daily loss 5%, max loss 10% static of initial.
1PHASE: target 10%, daily loss 4%, max loss trailing 6% below peak balance, stops trailing once the floor reaches the initial
        balance (floor = min(peak - 0.06, 1.0)).
Daily loss: equity must stay above B - d, B = balance at 00:05 UTC:
  optimistic   B = previous close equity (P&L effectively realised daily)
  conservative B = max close equity of the last 10 days (floating losses of positions held for days count against B)
Intraday low proxy = E_{t-1} * (1 + k * min(r_t, 0)), k = 1.5. Funded: monthly withdrawal of split * profit, reset."""
from __future__ import annotations

import numpy as np

PASS, FAIL_MAX, FAIL_DAILY, OPEN = 1, -1, -2, 0
PROGRAMS = {"2PHASE": {"targets": [0.08, 0.05], "daily": 0.05, "max": 0.10, "trailing": False},
            "1PHASE": {"targets": [0.10], "daily": 0.04, "max": 0.06, "trailing": True}}


def _run(r, s, target, daily, mx, trailing, k, mode, max_days, min_days=0):
    E = 1.0; hist = [1.0]; peak = 1.0
    for j in range(s, min(len(r), s + max_days)):
        x = r[j] if np.isfinite(r[j]) else 0.0
        B = E if mode == "optimistic" else max(hist[-10:])
        low = E * (1 + k * min(x, 0.0))
        if low < B - daily:
            return FAIL_DAILY, j - s + 1
        floor = min(peak - mx, 1.0) if trailing else 1.0 - mx
        if low < floor:
            return FAIL_MAX, j - s + 1
        E *= 1 + x; hist.append(E); peak = max(peak, E)
        if E >= 1 + target and (j - s + 1) >= min_days:
            return PASS, j - s + 1
    return OPEN, min(len(r) - s, max_days)


def simulate_start(r, s, program="2PHASE", k=1.5, mode="conservative", max_days=730, funded_months=12, split=0.8):
    P = PROGRAMS[program]; off = s; days = 0; out = {}
    for i, tgt in enumerate(P["targets"]):
        code, d = _run(r, off, tgt, P["daily"], P["max"], P["trailing"], k, mode, max_days - days)
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
            low = E * (1 + k * min(x, 0.0))
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
