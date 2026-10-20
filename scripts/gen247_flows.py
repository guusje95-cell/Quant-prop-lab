"""Gen247 (config/gen247_protocol.json): (A) kimchi premium on altcoins, (B) ridge + spot taker flow, (C) spot-led XS sleeve.
Needs research_data/more/upbit_KRW-<ALT>_1h.parquet and research_data/binance_spot/ (get_flow_data2.bat). Writes results/gen247.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import ridge_live as RL
END = "2026-09-30"; MORE = ROOT / "research_data/more"; SPOT = ROOT / "research_data/binance_spot"
g = {"__file__": str(ROOT / "scripts/gen196_bf_ridge.py")}; exec(open(ROOT / "scripts/gen196_bf_ridge.py").read().split("\nIS = (P6 + R1)")[0], g)
CS, HB0, per, sh, hb, P6, R1, CB, IDXbf, sleeve = (g[k] for k in ("CS", "HB0", "per", "sh", "hb", "P6", "R1", "CB", "IDXbf", "sleeve"))
q = {"__file__": str(ROOT / "scripts/gen232_bf_p1.py")}; exec(open(ROOT / "scripts/gen232_bf_p1.py").read().split("\nP6, R1, P1 =")[0], q)
P1 = q["p1"]()
v = {"__file__": str(ROOT / "scripts/gen109_ml_v6.py")}; exec(open(ROOT / "scripts/gen109_ml_v6.py").read().split("# X1")[0], v)
H6, B = v["H6"], v["B"]
IDX1 = IDXbf.append(pd.DatetimeIndex([IDXbf[-1] + pd.Timedelta(hours=1)]))
days = pd.date_range("2020-01-01", END)
ridge_ref = RL.predictions(END).pivot(index="day", columns="coin", values="ridge").fillna(0.0) * 0.5
perp = lambda w, coins: CS._from_daily_weights(w, list(coins), 5).loc[:END + " 23:00"]
cfd = lambda w: sleeve(CB.d2h(w.reindex(columns=CB.CFD).fillna(0.0), IDX1))
book = lambda cols: CS.portfolio_v5(pd.concat(cols, axis=1).fillna(0.0))[0]
hr_v7 = perp(ridge_ref, ["BTC", "ETH"]).rename("ridge ML"); IS0 = (P6 + R1 + P1).rename("vol-managed indices")
v7 = book([H6, hr_v7]); bf2 = book([HB0, IS0, hb.rename("ridge ML")])
ref = {"v7": (sh(v7, "2022-01-01", END), per(v7, "2022-01-01")), "bf2": (sh(bf2, "2022-01-01", END), per(bf2, "2022-01-01"))}
out = {"reference": {k: [round(a, 3), np.round(b, 3).tolist()] for k, (a, b) in ref.items()}}; print(out, flush=True)
cst = H6["C*"].groupby(H6.index.floor("D")).sum()
corr_c = lambda h: float(pd.concat([cst, h.groupby(h.index.floor("D")).sum()], axis=1).loc["2020":].corr().iloc[0, 1])


def strict(name, b):
    B1, k1 = sh(b, "2022-01-01", END), per(b, "2022-01-01"); B0, k0 = ref[name]
    return {"book": [round(B1, 3), np.round(k1, 3).tolist()], "strict": bool(B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}


def save():
    json.dump(out, open(ROOT / "results/gen247.json", "w"), indent=1)


# ---- A: kimchi premium on altcoins
fx = RL.usdkrw()
alts = [c for c in B.coins() if c not in ("BTC", "ETH") and (MORE / f"upbit_KRW-{c}_1h.parquet").exists()]
W = pd.DataFrame(0.0, index=days, columns=alts)
for c in alts:
    up = pd.read_parquet(MORE / f"upbit_KRW-{c}_1h.parquet")["close"]; up.index = pd.DatetimeIndex(up.index)
    bn = B.k5(c).close.resample("1h").last()
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:END]; kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    z = ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(days)
    W[c] = np.where(z > 1, 0.1, np.where(z < -1, -0.1, 0.0))
if alts:
    hA = perp(W, alts); sA = per(hA, "2020-01-01")
    Wc = W.reindex(columns=[c for c in CB.CFD if c in alts]); hAc = cfd(Wc); sAc = per(hAc, "2020-01-01")
    A = {"coins": alts, "sleeve perp D/T/H": np.round(sA, 3).tolist(), "corr C*": round(corr_c(hA), 3), "sleeve CFD D/T/H": np.round(sAc, 3).tolist(),
         "v7": strict("v7", book([H6, hr_v7, hA.rename("alt kimchi")])), "bf2": strict("bf2", book([HB0, IS0, hb.rename("ridge ML"), hAc.rename("alt kimchi")]))}
    A["pass v7"] = bool(sA[0] > 0 and sA[1] >= 0.8 and sA[2] >= 0.5 and A["corr C*"] <= 0.3 and A["v7"]["strict"])
    A["pass bf2"] = bool(sAc[0] > 0 and sAc[1] >= 0.5 and sAc[2] >= 0.3 and A["bf2"]["strict"])
    out["A alt kimchi"] = A; print("A", json.dumps(A), flush=True); save()


# ---- spot / perp daily taker imbalance
def imbalance(c):
    s = pd.read_parquet(SPOT / f"{c}USDT_1h.parquet").loc[:END + " 23:00"]
    sd = s.resample("1D").sum(); simb = (2 * sd["taker_buy_volume"] - sd["volume"]) / sd["volume"]
    k = B.k5(c).loc[:END + " 23:55"]; tb = k["taker_buy_volume"].resample("1D").sum(); vv = k["volume"].resample("1D").sum()
    return simb.replace([np.inf, -np.inf], np.nan).reindex(days), ((2 * tb - vv) / vv).replace([np.inf, -np.inf], np.nan).reindex(days)


if (SPOT / "BTCUSDT_1h.parquet").exists():
    # ---- B: ridge + spot flow
    D = RL.features(END)
    for c in ("BTC", "ETH"):
        si, pi = imbalance(c); m = D["coin"] == c
        D.loc[m, "simb"] = D.loc[m, "day"].map(si).to_numpy(); D.loc[m, "sdiv"] = D.loc[m, "day"].map(si - pi).to_numpy()
    feats = [x for x in D.columns if x not in ("day", "target", "coin")]; pred = pd.Series(np.nan, index=D.index)
    for mo in pd.date_range("2021-01-01", END, freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < mo - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D["day"] >= mo) & (D["day"] < mo + pd.offsets.MonthBegin(1))]
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
        pred.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    D["p"] = pred; wp = D.pivot(index="day", columns="coin", values="p").fillna(0.0) * 0.5
    hp, hc = perp(wp, ["BTC", "ETH"]), cfd(wp); sp, sc = per(hp, "2021-01-01"), per(hc, "2021-01-01")
    Bres = {"sleeve perp D/T/H": np.round(sp, 3).tolist(), "sleeve CFD D/T/H": np.round(sc, 3).tolist(),
            "v7": strict("v7", book([H6, hp.rename("ridge ML")])), "bf2": strict("bf2", book([HB0, IS0, hc.rename("ridge ML")]))}
    Bres["pass v7"] = bool(sp[0] > 0 and sp[1] >= 0.8 and sp[2] >= 0.5 and Bres["v7"]["strict"])
    Bres["pass bf2"] = bool(sc[0] > 0 and sc[1] >= 0.5 and sc[2] >= 0.3 and Bres["bf2"]["strict"])
    out["B ridge + spot flow"] = Bres; print("B", json.dumps(Bres), flush=True); save()
    # ---- C: spot-led cross-section
    coins = [c for c in B.coins() if (SPOT / f"{c}USDT_1h.parquet").exists()]
    S = pd.DataFrame({c: (lambda a: (a[0] - a[1]).rolling(7, min_periods=5).mean())(imbalance(c)) for c in coins})
    rk = S.rank(axis=1, ascending=False); n = S.notna().sum(axis=1)
    WC = (0.125 * rk.le(4).astype(float) - 0.125 * rk.gt(n - 4, axis=0).astype(float)).mul((n >= 10).astype(float), axis=0).fillna(0.0)
    hC = perp(WC, coins); sC = per(hC, "2020-01-01")
    C = {"coins": len(coins), "sleeve D/T/H": np.round(sC, 3).tolist(), "corr C*": round(corr_c(hC), 3), "v7": strict("v7", book([H6, hr_v7, hC.rename("spot-led XS")]))}
    C["pass"] = bool(sC[0] > 0 and sC[1] >= 0.8 and sC[2] >= 0.5 and C["corr C*"] <= 0.3 and C["v7"]["strict"])
    out["C spot-led XS"] = C; print("C", json.dumps(C), flush=True); save()
