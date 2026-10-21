"""Gen247 A checks (descriptive, no re-selection): thresholds, entry delay, FX lagged 2 days, 2x costs, per coin, 30-day block placebo.
Writes results/gen247_check.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
B, END = L.B, L.END
MORE = L.ROOT / "research_data/more"; days = pd.date_range("2020-01-01", END)
fx = RL.usdkrw()
alts = [c for c in B.coins() if c not in ("BTC", "ETH") and (MORE / f"upbit_KRW-{c}_1h.parquet").exists()]
Z = {}
for lag in (1, 2):
    zz = {}
    for c in alts:
        up = pd.read_parquet(MORE / f"upbit_KRW-{c}_1h.parquet")["close"]; up.index = pd.DatetimeIndex(up.index)
        bn = B.k5(c).close.resample("1h").last()
        fxh = fx.shift(lag).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
        kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
        zz[c] = ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(days)
    Z[lag] = pd.DataFrame(zz)
W = lambda z, th: pd.DataFrame(np.where(z > th, 0.1, np.where(z < -th, -0.1, 0.0)), index=z.index, columns=z.columns)
out = {}; rows = {}
def run(name, w, cost=5, shift=0):
    h = L.perp(w.shift(shift).fillna(0.0) if shift else w, cost)
    r = L.judge(name, h, out); rows[name] = r
run("adopted rule z>1", W(Z[1], 1.0))
for th in (0.75, 1.25, 1.5):
    run(f"z>{th}", W(Z[1], th))
run("entry 1 day later", W(Z[1], 1.0), shift=1)
run("FX lagged 2 days", W(Z[2], 1.0))
run("2x costs (10 bp)", W(Z[1], 1.0), cost=10)
run("long side only", W(Z[1], 1.0).clip(lower=0))
run("short side only", W(Z[1], 1.0).clip(upper=0))
# per coin (sleeve 2020-26 Sharpe)
pc = {}
for c in alts:
    h = L.perp(W(Z[1][[c]], 1.0)); d = h.groupby(h.index.floor("D")).sum().loc["2020":END]; pc[c] = round(float(d.mean() / d.std() * np.sqrt(365)), 2)
out["per coin 2020-26"] = pc; out["coins positive"] = f"{sum(v > 0 for v in pc.values())} of {len(pc)}"
# placebo: shuffle 30-day blocks of the signal (same for all coins), 100 times
base = L.perp(W(Z[1], 1.0)); bd = base.groupby(base.index.floor("D")).sum().loc["2020":END]; b0 = float(bd.mean() / bd.std() * np.sqrt(365))
rng = np.random.default_rng(7); w0 = W(Z[1], 1.0); n = len(w0); sims = []
for _ in range(100):
    blocks = np.arange(n) // 30; order = rng.permutation(blocks.max() + 1)
    perm = np.concatenate([np.flatnonzero(blocks == b) for b in order])[:n]
    ws = pd.DataFrame(w0.to_numpy()[perm], index=w0.index, columns=w0.columns)
    h = L.perp(ws); d = h.groupby(h.index.floor("D")).sum().loc["2020":END]; sims.append(float(d.mean() / d.std() * np.sqrt(365)))
out["placebo"] = {"actual 2020-26": round(b0, 3), "placebo mean": round(float(np.mean(sims)), 3), "placebo p95": round(float(np.percentile(sims, 95)), 3),
                  "p-value": float((np.array(sims) >= b0).mean())}
print(out["per coin 2020-26"], out["coins positive"], out["placebo"], flush=True)
json.dump(out, open(L.ROOT / "results/gen247_check.json", "w"), indent=1)
