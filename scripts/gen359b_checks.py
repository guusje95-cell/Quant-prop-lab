"""Gen359b (config/gen359b_protocol.json): checks of the final stress book. Writes results/gen359b.json."""
import json
import numpy as np
import pandas as pd
import stressbook as SB
btc = SB.D["BTC"]; up = btc > btc.rolling(200).mean()
out = {}


def book(th_p=3.0, k_c=3.0, cost_mult=1.0, ret=None):
    bc0 = SB.BCOST.copy(); SB.BCOST = SB.BCOST * cost_mult; R0 = SB.R
    if ret is not None:
        SB.R = ret
    try:
        s = {"premium spike": SB.pnl(SB.spike_positions(SB.premium_z(), th_p, 4, 1), maker=True),
             "crash reversal": SB.crash_reversal(k=k_c, filt=up, maker=True), "negative funding": SB.negative_funding(maker=True)}
    finally:
        SB.BCOST = bc0; SB.R = R0
    return SB.build(s)


base = book(); out["base"] = SB.evaluate(base)
NM = {"1000PEPE": "PEPE", "1000SHIB": "SHIB"}; ro = {}
for c in SB.coins:
    f = SB.ROOT / f"data/raw/okx/{NM.get(c, c)}-USDT-SWAP_1H.parquet"
    if f.exists():
        x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index); x = x[~x.index.duplicated()]; ro[c] = x.reindex(SB.idx).pct_change(fill_method=None)
RO = pd.DataFrame(ro).reindex(columns=SB.coins).fillna(0.0)
out["1 OKX"] = SB.evaluate(book(ret=RO)); print("OKX", out["1 OKX"]["EXPECTED LIVE (0.6 x 2020-26)"], flush=True)
grid = {}
for a in (2.5, 3.0, 3.5):
    for b in (2.5, 3.0, 3.5):
        e = SB.evaluate(book(a, b)); grid[f"premium {a} crash {b}"] = [e["EXPECTED LIVE (0.6 x 2020-26)"]] + e["Sharpe 2020-22 / 2023-24 / 2025-26"]
        print(a, b, grid[f"premium {a} crash {b}"], flush=True)
out["2 neighbourhood (expected live, periods)"] = grid; med = float(np.median([v[0] for v in grid.values()])); out["2 median expected live"] = round(med, 3)
eq = (1 + base).cumprod(); m = base.resample("ME").sum()
out["3 risk"] = {"max drawdown": round(float((eq / eq.cummax() - 1).min()), 3), "worst day": round(float(base.min()), 4), "worst month": round(float(m.min()), 4)}
v = SB.v86_daily().loc["2022":SB.END]; bk = base.loc["2022":]; Dm = pd.concat([v.rename("v"), bk.rename("b")], axis=1).dropna(); rho = float(Dm.corr().iloc[0, 1])
sv, sb = 1.78, out["base"]["EXPECTED LIVE (0.6 x 2020-26)"]
mix = lambda w: (sv + w * sb) / np.sqrt(1 + w * w + 2 * w * rho)
ws = np.arange(0, 2.01, 0.05); best = max(ws, key=mix)
out["4 with v8.6 at planning levels"] = {"corr": round(rho, 3), "v8.6 alone": sv, "equal risk": round(mix(1.0), 3), "best weight": round(float(best), 2), "best": round(mix(best), 3)}
import v7lab as L
import crypto_sleeves as CS
hb = sum(SB.pnl(SB.spike_positions(SB.premium_z(), 3.0, 4, 1), maker=True) * 0 for _ in [0])  # placeholder to keep names
s = {"premium spike": SB.pnl(SB.spike_positions(SB.premium_z(), 3.0, 4, 1), maker=True), "crash reversal": SB.crash_reversal(filt=up, maker=True), "negative funding": SB.negative_funding(maker=True)}
sd = pd.DataFrame({k: SB.daily(x) for k, x in s.items()}).loc[:"2024"].std()
hb = sum(x / sd[k] for k, x in s.items()).reindex(L.H6.index).fillna(0.0).rename("stress book")
H = pd.concat([L.H6, L.RIDGE] + L.ALTK, axis=1).fillna(0.0); R0 = [round(L.REF[0], 3)] + np.round(L.REF[1], 3).tolist(); res = {}
for mlt in (0.25, 0.5, 1.0):
    Dh = pd.concat([H, hb], axis=1).fillna(0.0); Dd = Dh.groupby(Dh.index.floor("D")).sum(); W = CS.v5_weights(Dd, list(Dh.columns)); W["stress book"] *= mlt
    Wh = W.reindex(Dh.index.floor("D")).set_axis(Dh.index); raw = (Dh * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
    tgt = (0.15 / (x1.rolling(30).std() * np.sqrt(365))).clip(upper=1.5).shift(1); mult = (lvl * tgt).loc["2022-01-01":]
    b = (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna()
    res[mlt] = {"D/T/H": [round(L.sh(b, "2022-01-01", L.END), 3)] + np.round(L.per(b, "2022-01-01"), 3).tolist(), "2022-24": round(L.sh(b, "2022-01-01", "2024-12-31"), 3)}
bm = max(res, key=lambda q: res[q]["2022-24"]); k = res[bm]["D/T/H"]
out["5 inside v8.6"] = {"by multiplier": res, "chosen on 2022-24": bm, "reference": R0, "strict pass": bool(all(a >= q for a, q in zip(k[1:], R0[1:])) and k[0] >= R0[0] + 0.05)}
out["6 costs x2"] = SB.evaluate(book(cost_mult=2.0))["EXPECTED LIVE (0.6 x 2020-26)"]
out["PASS (median >= 0.9 and OKX >= 0.9)"] = bool(med >= 0.9 and out["1 OKX"]["EXPECTED LIVE (0.6 x 2020-26)"] >= 0.9)
print(json.dumps({k: out[k] for k in out if k not in ("base", "1 OKX", "2 neighbourhood (expected live, periods)")}, indent=0))
json.dump(out, open(SB.ROOT / "results/gen359b.json", "w"), indent=1)
