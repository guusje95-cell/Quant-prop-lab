"""Gen262 (config/gen262_protocol.json): alt kimchi on the 40 extra coins; Turkish / Brazilian USDT and BTC premia (vs v8).
Needs get_flow_data3.bat data. Writes results/gen262.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
import ridge_live as RL
B, END = L.B, L.END
MORE = L.ROOT / "research_data/more"; X = L.ROOT / "research_data/binance_extra"; FIAT = L.ROOT / "research_data/binance_fiat"
out = {"reference v8": [round(L.REF[0], 3), np.round(L.REF[1], 3).tolist()]}; save = lambda: json.dump(out, open(L.ROOT / "results/gen262.json", "w"), indent=1)
days = pd.date_range("2020-01-01", END)
zs = lambda s, n=30, m=20: (s - s.rolling(n, min_periods=m).mean()) / s.rolling(n, min_periods=m).std()


def london_fx(name):
    """Yahoo daily FX dated by London day (finished bar wins), as ridge_live.usdkrw (research mode, no cutoff)."""
    fx0 = pd.read_parquet(MORE / f"yahoo_{name}_1d.parquet")["close"]
    lt = pd.DatetimeIndex(fx0.index).tz_localize("UTC").tz_convert("Europe/London"); ld = lt.normalize()
    order = pd.Series(lt == ld).reset_index(drop=True).sort_values(kind="stable").index
    s = pd.Series(fx0.to_numpy()[order], index=ld[order].tz_localize(None)); return s[~s.index.duplicated(keep="last")].sort_index()


def hourly_fx(fx, idx):
    return fx.shift(1).reindex(idx.floor("D"), method="ffill").set_axis(idx)


# ---- A: alt kimchi on the extra coins (sleeve 'alt kimchi extra')
fxk = RL.usdkrw(); W = {}; closes = {}
for p in sorted(X.glob("*USDT_1h.parquet")):
    perp = p.name.split("USDT_")[0]; c = perp.replace("1000", ""); mult = 1000.0 if perp.startswith("1000") else 1.0
    f = MORE / f"upbit_KRW-{c}_1h.parquet"
    if not f.exists():
        continue
    up = pd.read_parquet(f)["close"]; up.index = pd.DatetimeIndex(up.index)
    bn = pd.read_parquet(p)["close"]; bn.index = pd.DatetimeIndex(bn.index); bn = bn[~bn.index.duplicated()].loc[:END + " 23:00"]
    kp = (up * mult / hourly_fx(fxk, up.index) / bn.reindex(up.index) - 1).dropna(); kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    z = zs(kd).reindex(days); W[perp] = np.where(z > 1, 0.1, np.where(z < -1, -0.1, 0.0)); closes[perp] = bn
if W:
    W = pd.DataFrame(W, index=days); H = pd.DataFrame(closes).sort_index(); r = H.pct_change(fill_method=None).fillna(0.0)
    held = W.reindex(W.index.append(pd.DatetimeIndex([W.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
    turn = held.diff().abs().sum(axis=1).where(r.index.hour == 0, 0.0)
    hA = (held * r).sum(axis=1) - turn * 5 / 1e4
    out["A coins"] = list(W.columns); out["A note"] = "no funding (extra funding files incomplete)"
    L.judge("A alt kimchi extra coins", hA, out); save()


# ---- B / C: Turkish and Brazilian premia
def premium_z(pair, fxname, invert_usd=False, btc=False):
    f = FIAT / f"{pair}_1h.parquet"
    if not f.exists() or not (MORE / f"yahoo_{fxname}_1d.parquet").exists():
        return None
    x = pd.read_parquet(f)["close"]; x.index = pd.DatetimeIndex(x.index); fx = hourly_fx(london_fx(fxname), x.index)
    if btc:
        bn = B.k5("BTC").close.resample("1h").last().reindex(x.index); p = x / fx / bn - 1
    else:
        p = x / fx - 1                                                     # USDT priced in local currency vs the USD rate
    p24 = p.rolling(24, min_periods=20).mean(); zz = zs(p24, 720, 480); zd = zz[zz.index.hour == 23]; zd.index = zd.index.floor("D")
    return zd.reindex(days)


for name, key, btc in (("B regional USDT premium (TRY+BRL)", "USDT", False), ("C regional BTC premium (TRY+BRL)", "BTC", True)):
    parts = [premium_z(f"{key}{cur}", f"USD{cur}", btc=btc) for cur in ("TRY", "BRL")]
    parts = [p_ for p_ in parts if p_ is not None]
    if not parts:
        out[name] = "data missing"; continue
    comp = pd.concat(parts, axis=1).mean(axis=1, skipna=False)
    s = pd.Series(np.where(comp > 1, 0.25, np.where(comp < -1, -0.25, 0.0)), index=days)
    L.judge(name, L.perp(pd.DataFrame({"BTC": s, "ETH": s})), out); save()
