"""STOP-1 (protocol research/v99/stop1_protocol.json): daily-stop designs on the 5-minute account path, judged with the firm rule
engine (qpl.hub.income.simulate, unchanged). Writes results/v99/stop1_design.json."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
from qpl.hub import income as IN  # noqa: E402
from qpl.hub import prop as PR  # noqa: E402

g0 = {"__file__": str(ROOT / "scripts/v99/ex1_delay.py"), "__name__": "ex1"}
exec((ROOT / "scripts/v99/ex1_delay.py").read_text().split("\nout = {}\n")[0], g0)
run = g0["run"]
ORIG = PR.daily_with_stop


def path5(b: pd.Series, net: pd.DataFrame) -> pd.Series:
    """5-minute returns whose hourly sums equal b: position-implied 5-minute P&L + the hour's residual spread evenly"""
    b = b.loc["2022-01-01":"2026-09-30 23:00"]; ix5 = pd.date_range(b.index[0], b.index[-1] + pd.Timedelta(minutes=55), freq="5min")
    C = {}
    for k in net.columns:
        f = ROOT / f"research_data/binance/{k}USDT_5m.parquet"
        if f.exists():
            x = pd.read_parquet(f, columns=["close"])["close"]; C[k] = x[~x.index.duplicated()]
    C = pd.DataFrame(C).reindex(ix5).ffill(); r = (C / C.shift(1) - 1).fillna(0.0)
    P = net.reindex(ix5.floor("h")).set_axis(ix5).fillna(0.0)[C.columns]
    pp = (P * r).sum(axis=1); hh = pp.groupby(ix5.floor("h")).transform("sum")
    res = (b.reindex(ix5.floor("h")).set_axis(ix5).fillna(0.0) - hh) / 12.0
    return pp + res


def to_sharpe(x: pd.Series, target: float, per_day: int) -> pd.Series:
    d = x.groupby(x.index.floor("D")).sum()
    return x - (d.mean() - target * d.std() / np.sqrt(365)) / per_day


def hybrid(h: pd.Series, stop: float) -> pd.DataFrame:
    """2.5% on the hour marks + 3.75% emergency on every 5-minute close"""
    out = []
    for d, g in h.groupby(h.index.floor("D")):
        p = np.cumprod(1 + g.to_numpy()); marks = np.arange(11, len(p), 12)
        k1 = marks[p[marks] <= 1 - 0.025]; k2 = np.flatnonzero(p <= 1 - 0.0375)
        ks = [int(k[0]) for k in (k1, k2) if len(k)]
        if ks:
            k = min(ks); close = p[k] - 0.001
            out.append((d, close - 1, min(p[:k + 1].min(), close) - 1, max(p[:k + 1].max(), 1.0) - 1))
        else:
            out.append((d, p[-1] - 1, min(p.min(), 1.0) - 1, max(p.max(), 1.0) - 1))
    return pd.DataFrame(out, columns=["day", "net", "worst", "best"]).set_index("day")


def sim(unit, preset, risk, sr, stop_frac, fn=None):
    IN.daily_with_stop = fn or ORIG
    try:
        r = IN.simulate(unit, dict(IN.SCENARIOS["base"], live_sharpe=sr), [{"preset": preset, "start_day": 0, "budget": 3}], risk=risk, stop_frac=stop_frac, n_paths=400)
    finally:
        IN.daily_with_stop = ORIG
    return {"net_2y_mean_eur": round(r["horizon_net_eur_mean"]), "p10": round(r["horizon_net_eur_p10_p50_p90"][0]), "P_loss": round(r["P_net_loss_over_horizon"], 3)}


def firm(name, preset, b, net, risk, levels):
    b = b.loc["2022-01-01":"2026-09-30 23:00"]; p5 = path5(b, net); res = {"risk": risk}
    chk = float((p5.groupby(p5.index.floor("h")).sum() - b).abs().max()); res["check: max |hourly sum - research| "] = chk
    for sr in levels:
        u1 = b; u5 = to_sharpe(p5, sr, 288)
        rows = {"reference: 2.5% on hourly closes (as published)": sim(u1, preset, risk, sr, 0.5)}
        for lv in (2.0, 2.5, 3.0, 3.5, 4.0):
            rows[f"5-min stop {lv}%"] = sim(u5, preset, risk, sr, lv / 5.0)
        rows["hybrid: 2.5% hourly + 3.75% emergency"] = sim(u5, preset, risk, sr, 0.5, hybrid)
        res[f"Sharpe {sr}"] = rows
    return res


if __name__ == "__main__":
    f = ROOT / "results/v99/stop1_design.json"; out = json.loads(f.read_text()) if f.exists() else {}
    if "HyroTrader" not in out:
        g1 = run("cn1_crypto_netting.py", "book = ph.loc"); scale = json.loads((ROOT / "config/paper_v98.json").read_text())["frozen"]["v98_scale"]
        out["HyroTrader"] = firm("hyro", "HyroTrader Two-Step $200k", pd.read_parquet(ROOT / "results/v99/v99e_series.parquet")["v9.9e"], g1["net"] * scale, 1.5, (1.9, 1.6))
        f.write_text(json.dumps(out, indent=1))
    if "BrightFunded" not in out:
        g2 = run("cn2_cfd_netting.py", "sv = C.dd(sep - netc)")
        out["BrightFunded"] = firm("bf", "BrightFunded Two-Step Classic $200k", pd.read_parquet(ROOT / "results/v99/bf28_series.parquet")["bf2.8"],
                                   g2["net"].reindex(columns=g2["coins"]).fillna(0.0), 1.75, (1.45, 1.15))
        f.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
