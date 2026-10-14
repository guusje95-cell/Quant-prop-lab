"""Gen55 (config/gen55_protocol.json): C* + BTC leads through every crypto prop firm with that firm's own costs, swap, leverage
cap, day-reset hour and payout rules. DEV (daily candles) picks the risk settings per firm; the hourly replay 2022-2026 reports.
Writes results/gen55_dev_grid.csv and results/gen55_firms.csv."""
import itertools, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
from qpl.lab import engine as EN, propfirms as PF, strategies as S

FIRMS = {k: v for k, v in PF.PRESETS.items() if k not in ("Topstep 50k Combine (futures)", "Apex 50k (futures)", "Custom")}
FIRMS["FTMO 2-Step $100k (swap stress 3.3bp/day)"] = PF.replace(PF.PRESETS["FTMO 2-Step $100k"], swap_bps_day=3.3)
GRID = list(itertools.product((0.5, 0.75, 1.0, 1.5), (0.25, 0.4, 0.6), (0.0, 0.75)))
MAJORS = ["BTC", "ETH"]

cs = S.CStarTrend(); SIG = cs.signal(G.CR, {**cs.defaults(), "btc_leads": True})
W, _ = G.backtest(SIG, 30, 0.0)                                    # 15%-vol weights, decided at each daily close


def cap(w, f):
    if not f.lev_major:
        return w
    maj = [c for c in w.columns if c in MAJORS]; oth = [c for c in w.columns if c not in MAJORS]
    margin = w[maj].abs().sum(axis=1) / f.lev_major + w[oth].abs().sum(axis=1) / f.lev_other
    return w.div(margin.clip(lower=1.0), axis=0)


def dev_daily(f, scale):
    """Daily-candle model with the firm's commission (EN engine) and swap (gross notional x bp/day)."""
    w = cap(W * scale, f)
    cfg = EN.Config(cost_bps=f.cost_bps, leverage=1.0)
    d = EN.to_daily(EN.run(G.CR, w, cfg)["bars"], "1d").loc[G.DEV[0]:G.DEV[1]].copy()
    sw = (w.shift(1).abs().sum(axis=1) * f.swap_bps_day / 1e4).reindex(d.index).fillna(0.0)
    for c in ("net", "worst", "best"):
        d[c] = d[c] - sw
    return d


def dev_job(args):
    name, sc, sf, stop = args
    f = FIRMS[name]
    dc, df_ = dev_daily(f, sc), dev_daily(f, sf)
    fs = PF.replace(f, stop_frac=stop)
    a = PF.attempts(dc, fs, 1.0, step=3)
    p = PF.pipeline(dc, fs, 5, 1, 1.0, 1.0, daily_fd=df_, horizon_days=730, step=5)
    return {"firm": name, "risk_challenge": sc, "risk_funded": sf, "daily_stop": stop, "DEV_pass": a["P_pass"],
            "DEV_net": p.get("net_mean"), "DEV_p_profit": p.get("P_profit"), "DEV_funded": p.get("P_funded")}


# ---------------- hourly replay
CH = G.SRC["Binance spot majors (hourly, 2022+)"]()
HRET = CH.close[G.CR.symbols].sort_index().pct_change(fill_method=None).fillna(0.0)
UTC_DAY = HRET.index.floor("D")


def hourly(f, scale, stop):
    """Daily (firm-day) net / worst / best from the hourly path with the firm's costs. Weights change at 00:00 UTC; the firm's
    day runs from reset_hour_utc. A daily stop closes everything at stop x daily-loss (+0.1% slippage) for the rest of that firm-day."""
    held = cap(W * scale, f).shift(1).fillna(0.0)
    H = pd.DataFrame(held.reindex(UTC_DAY).to_numpy(), index=HRET.index, columns=W.columns).fillna(0.0)
    port = (H * HRET).sum(axis=1).to_numpy()
    turn = (held.diff().abs().sum(axis=1) * f.cost_bps / 1e4).reindex(UTC_DAY).to_numpy()
    gross = held.abs().sum(axis=1).reindex(UTC_DAY).to_numpy()
    first_utc = np.r_[True, UTC_DAY[1:] != UTC_DAY[:-1]]
    at_reset = HRET.index.hour == f.reset_hour_utc
    g = (1 + port) * (1 - np.where(first_utc, np.nan_to_num(turn), 0.0)) * (1 - np.where(at_reset, np.nan_to_num(gross) * f.swap_bps_day / 1e4, 0.0))
    fday = (HRET.index - pd.Timedelta(hours=f.reset_hour_utc)).floor("D")
    lim = f.daily_loss; rows = []
    for dd, gg in pd.Series(g, index=HRET.index).groupby(fday):
        path = np.concatenate([[1.0], np.cumprod(gg.to_numpy())])
        k = int(np.argmax(path <= 1 - stop * lim)) if stop > 0 and (path <= 1 - stop * lim).any() else None
        if k is not None:
            c = path[k] - 0.001; rows.append((dd, c - 1, min(path[:k + 1].min(), c) - 1, path[:k + 1].max() - 1))
        else:
            rows.append((dd, path[-1] - 1, path.min() - 1, path.max() - 1))
    return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day").iloc[1:]


def months_with_income(hc, hf, f, horizon=730, every=15):
    cal = ((hc.index - hc.index[0]).days).to_numpy()
    rc = [hc[c].to_numpy() for c in ("net", "worst", "best")]; rf = [hf.reindex(hc.index).fillna(0.0)[c].to_numpy() for c in ("net", "worst", "best")]
    out = []
    for s in range(0, len(cal), every):
        if cal[-1] - cal[s] < horizon:
            break
        end = int(np.searchsorted(cal, cal[s] + horizon))
        led = PF._ledger(*rc, *rf, cal, s, end, f, 5)
        cash = np.diff(np.r_[0.0, led["wealth"]])
        m = pd.Series(cash).groupby(np.arange(len(cash)) // 30.4).sum().iloc[6:]
        out.append(((m > 0).mean(), m.mean()))
    return (float(np.mean([o[0] for o in out])), float(np.mean([o[1] for o in out]))) if out else (np.nan, np.nan)


def evaluate(name, sc, sf, stop):
    f = FIRMS[name]
    hc, hf = hourly(f, sc, stop), hourly(f, sf, stop)
    a = PF.attempts(hc, f, 1.0)
    p = PF.pipeline(hc, f, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
    mi, avg_m = months_with_income(hc, hf, f)
    return {"pass": a["P_pass"], "fail_daily": a["P_fail_daily"], "fail_max": a["P_fail_max"], "days_to_pass": a["median_days_to_pass"],
            "funded": p.get("P_funded"), "bought": p.get("bought"), "fees": p.get("fees"), "paid": p.get("paid"), "net": p.get("net_mean"),
            "net_p50": p.get("net_p50"), "net_p10": p.get("net_p10"), "p_profit": p.get("P_profit"), "months_with_income": mi,
            "avg_month_m7_24": avg_m, "paths": p.get("n")}


def hourly_job(args):
    name, tag, sc, sf, stop = args
    return {"firm": name, "setting": tag, "risk_challenge": sc, "risk_funded": sf, "daily_stop": stop, **evaluate(name, sc, sf, stop)}


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(n, *g) for n in FIRMS for g in GRID]
    with Pool(4) as pool:
        dev = pd.DataFrame(pool.map(dev_job, jobs, chunksize=4))
    dev.to_csv(ROOT / "results/gen55_dev_grid.csv", index=False)
    print(f"DEV grid {len(dev)} in {time.time() - t0:.0f}s", flush=True)
    hj = []
    for n in FIRMS:
        hj.append((n, "baseline 1.0/0.4", 1.0, 0.4, 0.0))
        b = dev[dev.firm == n].sort_values("DEV_net", ascending=False).iloc[0]
        hj.append((n, "DEV pick", float(b.risk_challenge), float(b.risk_funded), float(b.daily_stop)))
    with Pool(4) as pool:
        res = pd.DataFrame(pool.map(hourly_job, hj))
    f_meta = pd.DataFrame([{"firm": n, "fee": f.fee, "refund": f.refund_fee, "split": f.split, "cost_bps": f.cost_bps, "swap_bps_day": f.swap_bps_day,
                            "note": f.note} for n, f in FIRMS.items()])
    res = res.merge(f_meta, on="firm")
    res.to_csv(ROOT / "results/gen55_firms.csv", index=False)
    pd.set_option("display.width", 250)
    print(res.sort_values("net", ascending=False)[["firm", "setting", "risk_challenge", "risk_funded", "daily_stop", "pass", "funded", "net", "net_p50",
                                                   "net_p10", "p_profit", "months_with_income", "fees"]].round(2).to_string(), flush=True)
    print(f"done {time.time() - t0:.0f}s")
