"""v9.9 R38 (research/v99/r38_protocol.json): alt-kimchi rule on the extra Upbit coins, merged into the sleeve or separate.
Writes results/v99/r38_kimchi_wide.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
import ridge_live as RL
from qpl.lab import extra_pack as X
MORE = ROOT / "research_data/more"; XD = ROOT / "research_data/binance_extra"; END = "2026-09-30"


def extra_sleeve(idx):
    days = pd.date_range("2020-01-01", END); fx = RL.usdkrw(); W, C, F = {}, {}, {}
    for p in sorted(XD.glob("*USDT_1h.parquet")):
        perp = p.name.split("USDT_")[0]; c = perp.replace("1000", ""); mult = 1000.0 if perp.startswith("1000") else 1.0
        f = MORE / f"upbit_KRW-{c}_1h.parquet"
        if not f.exists():
            continue
        up = pd.read_parquet(f)["close"]; up.index = pd.DatetimeIndex(up.index)
        bn = pd.read_parquet(p)["close"].astype(float); bn.index = pd.DatetimeIndex(bn.index); bn = bn[~bn.index.duplicated()].loc[:END + " 23:00"]
        fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
        kp = (up * mult / fxh / bn.reindex(up.index) - 1).dropna(); kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
        z = ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(days)
        W[perp] = np.where(z > 1, 0.1, np.where(z < -1, -0.1, 0.0)); C[perp] = bn
        try:
            fu = X.funding(perp); fu.index = pd.DatetimeIndex(fu.index).floor("h"); F[perp] = fu.groupby(level=0).sum()
        except Exception:                                                  # noqa: BLE001 - no funding file
            pass
    W = pd.DataFrame(W, index=days); H = pd.DataFrame(C).sort_index(); r = H.pct_change(fill_method=None).fillna(0.0)
    held = W.reindex(W.index.append(pd.DatetimeIndex([W.index[-1] + pd.Timedelta(days=1)]))).shift(1).reindex(r.index.floor("D")).set_axis(r.index).fillna(0.0)
    fund = pd.DataFrame({c: F[c].reindex(r.index).fillna(0.0) if c in F else pd.Series(0.0, index=r.index) for c in held.columns})
    turn = held.diff().abs().sum(axis=1).where(r.index.hour == 0, 0.0)
    pnl = (held * r).sum(axis=1) - (held * fund).sum(axis=1) - turn * 5 / 1e4
    pnl.index = pnl.index + pd.Timedelta(hours=1)                           # stamp = bar close (as the pack sleeves)
    return pnl.reindex(idx).fillna(0.0), list(W.columns), sorted(F)


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    book = lambda H: (lambda b: [shp(b, "2022", "2026-09-30"), per(b)])(unit(CS.portfolio_v5(H)[0]))
    ref = book(V8); h, coins, withf = extra_sleeve(idx)
    out = {"reference v9.8": ref, "extra coins": coins, "with funding": len(withf), "extra sleeve 2022 / 23-24 / 25-26": per(h),
           "v9.8 alt kimchi": per(V8["alt kimchi"]), "merged alt kimchi": per(V8["alt kimchi"] + h),
           "corr extra vs alt kimchi (daily)": round(float(dd(h.loc["2022":]).corr(dd(V8["alt kimchi"].loc["2022":]))), 3)}
    for name, H in (("A wider alt-kimchi sleeve", V8.assign(**{"alt kimchi": V8["alt kimchi"] + h})), ("B separate sleeve", V8.assign(**{"alt kimchi extra": h}))):
        r = book(H); out[name] = {"book": r, "pass": bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))}
    print(json.dumps(out, indent=1)); (ROOT / "results/v99/r38_kimchi_wide.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
