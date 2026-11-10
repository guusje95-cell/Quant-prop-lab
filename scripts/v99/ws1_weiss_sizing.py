"""WS-1 (protocol research/v99/ws1_protocol.json): Weiss exposure cap under a daily stop that is monitored inside the trade.
Writes results/v99/ws1_weiss_sizing.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS  # noqa: E402

CACHE = ROOT / "research_data/binance_1m_weiss"
STOP, LIMIT = 0.025, 0.05
GRID = ("research", 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0)
PER = (("2022", "2022"), ("2023", "2024"), ("2025", "2026-09-30"))


def weiss_paths() -> dict:
    """day -> (close path, adverse path) per unit gross from the 08:01 open to the 09:59 bar, and the final value at the 10:00 open"""
    days = pd.date_range("2022-01-07", "2026-09-30", freq="W-FRI"); days = days[(days + pd.Timedelta(days=7)).month != days.month]; out = {}
    for d in days:
        t7, t8, te, t10 = (d + pd.Timedelta(hours=7), d + pd.Timedelta(hours=8), d + pd.Timedelta(hours=8, minutes=1), d + pd.Timedelta(hours=10))
        pc = pw = 0.0; fin = 0.0; ok = True
        for sym in ("BTCUSDT", "ETHUSDT"):
            f = CACHE / f"{sym}_{d.date()}.parquet"
            if not f.exists():
                ok = False; break
            x = pd.read_parquet(f)
            if not all(t in x.index for t in (t7, t8, te, t10)) or x.open[t8] == x.open[t7]:
                ok = False; break
            side = -np.sign(x.open[t8] / x.open[t7] - 1); e = x.open[te]; seg = x.loc[te:t10 - pd.Timedelta(minutes=1)]
            pc = pc + side * 0.5 * (seg.close / e - 1); pw = pw + side * 0.5 * ((seg.low if side > 0 else seg.high) / e - 1)
            fin += side * 0.5 * (x.open[t10] / e - 1)
        if ok:
            out[d] = (pc.to_numpy(), pw.to_numpy(), float(fin))
    return out


def simulate(nonw: pd.Series, e_day: pd.Series, res_w: pd.Series, paths: dict, cap, chk: int, cost: float, view: str = "live", leg_stop: float | None = None):
    """nonw: hourly ACCOUNT returns without Weiss; e_day: Weiss gross (x equity) per day; res_w: research Weiss account P&L per hour at
    the research size. view 'research': Weiss booked at 10:00, hourly stop only. Returns (daily returns, stats)."""
    days = pd.date_range("2022-01-01", "2026-09-30"); N = nonw.reindex(pd.date_range(days[0], days[-1] + pd.Timedelta(hours=23), freq="h")).fillna(0.0).to_numpy().reshape(-1, 24)
    RW = res_w.reindex(pd.date_range(days[0], days[-1] + pd.Timedelta(hours=23), freq="h")).fillna(0.0).to_numpy().reshape(-1, 24)
    out = np.zeros(len(days)); stops = breaches = wstops = 0; worst_intraday = 0.0; w_lo = 0.0; w_br = 0
    for i, d in enumerate(days):
        E0 = float(e_day.get(d, 0.0)); E = E0 if cap == "research" else min(E0, float(cap)); k = (E / E0) if E0 > 0 else 0.0
        wd = d in paths and E0 > 0; eq = 0.0; stopped = False; h = 0
        while h < 24:
            if wd and view == "live" and h == 8 and E > 0:
                pc, pw, fin = paths[d]; n = len(pc); fr = (np.arange(n) + 2) / 120.0
                base = eq + N[i, 8] * np.minimum(1.0, fr * 2) + N[i, 9] * np.clip(fr * 2 - 1, 0, 1)
                w_c = E * pc - E * cost; w_w = E * pw - E * cost; hit = None; legout = None
                for j in range(chk - 1, n, chk):
                    if leg_stop is not None and legout is None and w_c[j] <= -leg_stop:
                        legout = j; lv = w_c[j] - E * (cost + 0.001); w_c = np.where(np.arange(n) >= j, lv, w_c); w_w = np.where(np.arange(n) > j, lv, w_w)
                    if base[j] + w_c[j] <= -STOP:
                        hit = j; break
                upto = (hit if hit is not None else n - 1) + 1
                lo = float((base[:upto] + w_w[:upto]).min()); worst_intraday = min(worst_intraday, lo); breaches += lo <= -LIMIT; w_lo = min(w_lo, lo); w_br += lo <= -LIMIT
                if hit is not None:
                    eq = base[hit] + w_c[hit] - (0.0 if legout is not None else E * (cost + 0.001)) - 0.001 * 1.5; stopped = True; wstops += 1; break
                eq = eq + N[i, 8] + N[i, 9] + (w_c[-1] if legout is not None else E * fin - 2 * E * cost); h = 10
                if eq <= -STOP:
                    eq -= 0.001 * 1.5; stopped = True; break
                continue
            eq += N[i, h] + (RW[i, h] * k if (view == "research" or not wd) else 0.0)
            worst_intraday = min(worst_intraday, eq)
            if eq <= -STOP:
                eq -= 0.001 * 1.5; stopped = True; break
            h += 1
        out[i] = eq; stops += stopped
    r = pd.Series(out, index=days); sh = lambda x: float(x.mean() / x.std() * np.sqrt(365))
    return r, {"sharpe": round(sh(r), 3), "periods": [round(sh(r.loc[a:b]), 3) for a, b in PER], "annual return %": round(float(r.mean() * 365 * 100), 1),
               "worst day %": round(float(r.min() * 100), 2), "stop days": int(stops), "stops inside the Weiss trade": int(wstops),
               "breach days (<= -5% intraday)": int(breaches), "worst intraday %": round(worst_intraday * 100, 2),
               "Weiss window: worst intraday equity %": round(w_lo * 100, 2), "Weiss window: breaches": int(w_br)}


def table(name, book, wterm, e_unit, risk, cost, research_cap):
    """book: hourly book returns; wterm: hourly Weiss term of the book; e_unit: Weiss gross per day at risk 1 (x equity)"""
    paths = weiss_paths(); nonw = (book - wterm) * risk; e_day = e_unit * risk; res_w = wterm * risk
    if research_cap:                                           # BrightFunded research: cap on the Weiss gross
        f = (research_cap / e_day).clip(upper=1.0).fillna(1.0); res_w = res_w * f.reindex(res_w.index.floor("D")).set_axis(res_w.index).fillna(1.0); e_day = e_day.clip(upper=research_cap)
    act = e_day[[d for d in paths if d in e_day.index]]
    res = {"risk": risk, "Weiss days with 1-minute data": len(paths), "Weiss gross on those days (x equity): median / max": [round(float(act.median()), 2), round(float(act.max()), 2)]}
    res["research view (Weiss booked at 10:00, hourly stop)"] = simulate(nonw, e_day, res_w, paths, "research", 60, cost, view="research")[1]
    for chk in (1, 5, 60):
        res[f"stop checked every {chk} min"] = {str(K): simulate(nonw, e_day, res_w, paths, K, chk, cost)[1] for K in GRID}
    res["descriptive: Weiss-only stop at -1.25% of the account (1 min)"] = {str(K): simulate(nonw, e_day, res_w, paths, K, 1, cost, leg_stop=0.0125)[1] for K in ("research", 2.0, 1.5, 1.0)}
    return res


def hyro():
    from qpl.lab.erc import erc_weights
    from qpl.live import v99_book as VB
    H = VB.sleeve_hours().loc[:"2026-09-30 23:00"]; scale = json.loads((ROOT / "config/paper_v98.json").read_text())["frozen"]["v98_scale"]
    orig = CS.v5_weights; CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: erc_weights(D, sleeves, weiss_scale, 0.5)
    try:
        ph, W, mult = CS.portfolio_v5(H, start=str(H.index[0].date()))
    finally:
        CS.v5_weights = orig
    wd = (W["Weiss expiry"] * mult.reindex(W.index) * scale).fillna(0.0)
    wterm = wd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0) * H["Weiss expiry"]
    return table("hyro", (ph * scale).reindex(H.index).fillna(0.0), wterm, wd, 1.5, 5e-4, None)


def bf():
    g0 = {"__file__": str(ROOT / "scripts/v99/ex1_delay.py"), "__name__": "ex1"}
    exec((ROOT / "scripts/v99/ex1_delay.py").read_text().split("\nout = {}\n")[0], g0)
    g2 = g0["run"]("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
    H, ph, W, M, k = g2["H"], g2["ph"], g2["W"], g2["M"], g2["k"]
    wd = (W["Weiss expiry"] * M.reindex(W.index) * k).fillna(0.0)
    wterm = wd.reindex(H.index.floor("D")).set_axis(H.index).fillna(0.0) * H["Weiss expiry"]
    return table("bf", (ph * k).reindex(H.index).fillna(0.0), wterm, wd, 1.75, 2.75e-4, 4.0)


if __name__ == "__main__":
    f = ROOT / "results/v99/ws1_weiss_sizing.json"; out = json.loads(f.read_text()) if f.exists() else {}
    for name, fn in (("HyroTrader v9.9e @ 1.5", hyro), ("BrightFunded bf2.8 @ 1.75", bf)):
        if len(sys.argv) > 1 and sys.argv[1] not in name.lower():
            continue
        out[name] = fn(); f.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
