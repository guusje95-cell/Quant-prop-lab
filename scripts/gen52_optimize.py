"""Gen52 prop optimisation (config/gen52_optimization_protocol.json). Stage 1 signal/sizing, stage 2 prop settings, then
TEST + hourly check. Writes results/gen52_stage1.csv, gen52_stage2.csv, gen52_final.csv."""
import itertools, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, engine as EN, propfirms as PF, strategies as S

SRC = D.list_sources()
CR = SRC["Binance spot majors (daily, 2017+)"]()
DEV = ("2018-03-05", "2022-12-31"); TEST = ("2023-01-01", "2026-12-31")
FIRMS = {"CFT1": PF.PRESETS["Crypto Fund Trader 1-Phase $100k"], "FTMO": PF.PRESETS["FTMO 2-Step $100k"]}

VARIANTS = [
    ("C* default", S.CStarTrend, {"stablecoin_filter": True, "long_only": True}),
    ("C* no stablecoin filter", S.CStarTrend, {"stablecoin_filter": False, "long_only": True}),
    ("C* long-short", S.CStarTrend, {"stablecoin_filter": True, "long_only": False}),
    ("C* long-short no filter", S.CStarTrend, {"stablecoin_filter": False, "long_only": False}),
    ("CCT 5..360", S.CryptoTrendEnsemble, {"long_only": True, "lookbacks": "5,10,20,30,60,90,150,250,360"}),
    ("CCT 20,60,150,360", S.CryptoTrendEnsemble, {"long_only": True, "lookbacks": "20,60,150,360"}),
    ("CCT 5,10,20,30", S.CryptoTrendEnsemble, {"long_only": True, "lookbacks": "5,10,20,30"}),
    ("Donchian 10", S.Donchian, {"n": 10, "long_only": True}), ("Donchian 20", S.Donchian, {"n": 20, "long_only": True}),
    ("Donchian 55", S.Donchian, {"n": 55, "long_only": True}),
    ("TSMOM 30", S.TSMOM, {"lookback": 30, "long_only": True}), ("TSMOM 60", S.TSMOM, {"lookback": 60, "long_only": True}),
    ("TSMOM 90", S.TSMOM, {"lookback": 90, "long_only": True}),
    ("MA 20/100", S.SMACross, {"fast": 20, "slow": 100, "long_only": True}), ("MA 50/200", S.SMACross, {"fast": 50, "slow": 200, "long_only": True}),
]


def ndays_high(n):
    c = CR.close
    return ((c >= c.rolling(n).max()).astype(float).where(c.notna(), 0.0)
            .replace(0, np.nan).ffill(limit=n // 2).fillna(0.0))           # hold n/2 days after a new n-day high


def band(w, b):
    if b <= 0:
        return w
    W = w.to_numpy().copy()
    for t in range(1, len(W)):
        prev = W[t - 1]; cur = W[t]
        keep = (np.abs(cur - prev) <= b * np.abs(prev)) & (np.sign(cur) == np.sign(prev)) & (prev != 0)
        W[t] = np.where(keep, prev, cur)
    return pd.DataFrame(W, index=w.index, columns=w.columns)


def backtest(sig, look, b):
    cfg = EN.Config(cost_bps=7.5, vol_lookback_days=look, leverage=1.0)
    w = band(EN.size(CR, sig, cfg), b)
    d = EN.to_daily(EN.run(CR, w, cfg)["bars"], "1d").loc[DEV[0]:]
    k = 0.15 / (d.loc[DEV[0]:DEV[1], "net"].std() * np.sqrt(365))              # 15% vol, DEV volatility only
    w = w * k
    d = EN.to_daily(EN.run(CR, w, cfg)["bars"], "1d").loc[DEV[0]:]
    return w, d


def prop_eval(d, firm, sc, sf, horizon=730, step_att=3, step_pipe=5):
    a = PF.attempts(d, firm, sc, step=step_att)
    p = PF.pipeline(d, firm, 5, 1, sc, sf, horizon_days=horizon, step=step_pipe)
    return {"pass": a["P_pass"], "fail_daily": a["P_fail_daily"], "fail_max": a["P_fail_max"], "days_to_pass": a["median_days_to_pass"],
            "funded": p.get("P_funded"), "bought": p.get("bought"), "net": p.get("net_mean"), "net_p50": p.get("net_p50"),
            "net_p10": p.get("net_p10"), "p_profit": p.get("P_profit"), "paths": p.get("n")}


BT = {}


def stage2_job(args):
    key, firm_name, sc, sf, stop, tp, cush = args
    d = BT[key][1].loc[DEV[0]:DEV[1]]
    f = PF.replace(FIRMS[firm_name], stop_frac=stop, take_profit=tp, cushion_scale=cush)
    return {"config": key, "firm": firm_name, "risk_challenge": sc, "risk_funded": sf, "daily_stop": stop, "take_profit": tp,
            "cushion": cush, **prop_eval(d, f, sc, sf)}


def stage1_job(key):
    d = BT[key][1].loc[DEV[0]:DEV[1]]
    out = {"config": key}
    x = d["net"]; out["dev_sharpe"] = x.mean() / x.std() * np.sqrt(365); out["dev_cagr"] = (1 + x).prod() ** (365 / len(x)) - 1
    dd = (1 + x).cumprod(); out["dev_maxdd"] = (dd / dd.cummax() - 1).min()
    for fn in FIRMS:
        r = prop_eval(d, FIRMS[fn], 1.0, 0.4)
        out.update({f"{fn}_{k}": v for k, v in r.items()})
    return out


if __name__ == "__main__":
    t = time.time()
    sigs = {nm: cls().signal(CR, p) for nm, cls, p in VARIANTS}
    sigs["N-day high 20"] = ndays_high(20); sigs["N-day high 50"] = ndays_high(50)
    sigs["C* + CCT 50/50"] = (sigs["C* default"] + sigs["CCT 5..360"]) / 2
    for nm, sg in sigs.items():
        for look, b in itertools.product((20, 30, 60), (0.0, 0.2)):
            BT[f"{nm} | vol{look} | band{b}"] = backtest(sg, look, b)
    print(f"stage1 backtests: {len(BT)} in {time.time() - t:.0f}s", flush=True)
    with Pool(4) as pool:
        s1 = pd.DataFrame(pool.map(stage1_job, list(BT)))
    s1.to_csv(ROOT / "results/gen52_stage1.csv", index=False)
    print(s1.sort_values("CFT1_net", ascending=False).head(12)[["config", "dev_sharpe", "CFT1_pass", "CFT1_net", "CFT1_p_profit", "FTMO_net"]].round(3).to_string(), flush=True)
    jobs, top = [], {}
    for fn in FIRMS:
        top[fn] = list(s1.sort_values(f"{fn}_net", ascending=False)["config"].head(8))
        for key in top[fn]:
            for sc, sf, stop, tp, cush in itertools.product((0.5, 0.75, 1.0, 1.25, 1.5), (0.25, 0.4, 0.6), (0.0, 0.5, 0.75, 0.9), (0.0, 0.02, 0.04), (False, True)):
                jobs.append((key, fn, sc, sf, stop, tp, cush))
    print(f"stage2 jobs: {len(jobs)}", flush=True)
    with Pool(4) as pool:
        s2 = pd.DataFrame(pool.map(stage2_job, jobs, chunksize=20))
    s2.to_csv(ROOT / "results/gen52_stage2.csv", index=False)
    print(f"stage2 done {time.time() - t:.0f}s", flush=True)
    # ---------------- TEST + hourly check for the top 10 per firm + plain C*
    ch = SRC["Binance spot majors (hourly, 2022+)"]()
    hret = ch.close[CR.symbols].sort_index().pct_change(fill_method=None).fillna(0.0); hday = hret.index.floor("D")

    def hourly_daily(w, scale, stop, tp, daily_limit):
        held = (w * scale).shift(1).fillna(0.0)
        H = pd.DataFrame(held.reindex(hday).to_numpy(), index=hret.index, columns=w.columns).fillna(0.0)
        turn = held.diff().abs().sum(axis=1) * 7.5 / 1e4
        port = (H * hret).sum(axis=1); rows = []
        for dd, g in port.groupby(hday):
            if dd not in turn.index:
                continue
            path = np.concatenate([[1.0], np.cumprod(1 + g.to_numpy())]) * (1 - turn.loc[dd])
            k = None
            if stop > 0 and (path <= 1 - stop * daily_limit).any():
                k = int(np.argmax(path <= 1 - stop * daily_limit))
            if tp > 0 and (path >= 1 + tp).any():
                k2 = int(np.argmax(path >= 1 + tp))
                k = k2 if k is None or k2 < k else k
            if k is not None:
                close = path[k] - 0.001
                rows.append((dd, close - 1, min(path[:k + 1].min(), close) - 1, path[:k + 1].max() - 1))
            else:
                rows.append((dd, path[-1] - 1, path.min() - 1, path.max() - 1))
        return pd.DataFrame(rows, columns=["day", "net", "worst", "best"]).set_index("day")

    final = []
    for fn in FIRMS:
        cand = s2[s2.firm == fn].sort_values("net", ascending=False).head(10).to_dict("records")
        cand.append({"config": "C* default | vol30 | band0.0", "firm": fn, "risk_challenge": 1.0, "risk_funded": 0.4, "daily_stop": 0.0,
                     "take_profit": 0.0, "cushion": False, "net": np.nan, "_baseline": True})
        for c in cand:
            w, d = BT[c["config"]]
            f = PF.replace(FIRMS[fn], stop_frac=c["daily_stop"], take_profit=c["take_profit"], cushion_scale=c["cushion"])
            dev = prop_eval(d.loc[DEV[0]:DEV[1]], f, c["risk_challenge"], c["risk_funded"])
            tst = prop_eval(d.loc[TEST[0]:TEST[1]], f, c["risk_challenge"], c["risk_funded"])
            lim = FIRMS[fn].daily_loss
            hc = hourly_daily(w, c["risk_challenge"], c["daily_stop"], c["take_profit"], lim)
            hf = hourly_daily(w, c["risk_funded"], c["daily_stop"], c["take_profit"], lim)
            fh = PF.replace(FIRMS[fn], cushion_scale=c["cushion"])
            hh = prop_eval(hc, fh, 1.0, 1.0) if False else None
            a = PF.attempts(hc, fh, 1.0); p = PF.pipeline(hc, fh, 5, 1, 1.0, 1.0, daily_fd=hf, horizon_days=730, step=5)
            row = {"firm": fn, "baseline": bool(c.get("_baseline")), "config": c["config"], "risk_challenge": c["risk_challenge"],
                   "risk_funded": c["risk_funded"], "daily_stop": c["daily_stop"], "take_profit": c["take_profit"], "cushion": c["cushion"],
                   **{f"DEV_{k}": v for k, v in dev.items()}, **{f"TEST_{k}": v for k, v in tst.items()},
                   "HOURLY_pass": a["P_pass"], "HOURLY_net": p.get("net_mean"), "HOURLY_p_profit": p.get("P_profit"), "HOURLY_paths": p.get("n")}
            final.append(row)
            print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items() if k in ("firm", "config", "risk_challenge", "risk_funded", "daily_stop", "take_profit", "cushion", "DEV_net", "TEST_pass", "TEST_net", "TEST_p_profit", "HOURLY_pass", "HOURLY_net", "HOURLY_p_profit")}, flush=True)
    pd.DataFrame(final).to_csv(ROOT / "results/gen52_final.csv", index=False)
    print(f"done {time.time() - t:.0f}s")
