"""Gen373 (config/gen373_protocol.json): C* on a point-in-time universe, choice of the honest live book, per-firm numbers.
Writes results/gen373.json and results/gen373_book_hourly.parquet.
    cd scripts && python gen373_honest_cstar.py <v86 dump parquet (paper_v5.py _dump, cutoff 2026-10-01, live 0)>"""
import json
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
DUMP = sys.argv[1]; sys.argv = sys.argv[:1]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
exec(open(ROOT / "scripts/gen326_wide_carry.py").read().split("\nimport os\nREF")[0])      # S, H (hourly closes), QV (daily), r, F, coins, sleeve(K)
from qpl.lab import propfirms as PF, strategies as ST
from qpl.lab.data import Bars
src = open(ROOT / "scripts/gen90_books.py").read(); exec(src[src.index("def to_daily_stop"):src.index("P = []")], globals())
END = "2026-09-30"; MAJ10 = B.MAJ10
bad = lambda c: c in ("BTCDOM", "DEFI", "USDC", "BUSD", "TUSD", "FDUSD", "USDP", "BTCST") or "DOM" in c or ("USD" in c and c not in ("BTC", "ETH"))
cand = [c for c in coins if not bad(c)]
Hc = H[cand].loc[:END + " 23:00"]; Dc = Hc.resample("1D").last()
bars = Bars("perps pit", "1d", Dc, Dc, Dc, Dc, QV.reindex(Dc.index)[cand])
cs = ST.CStarTrend(); sig = cs.signal(bars, {**cs.defaults(), "btc_leads": True})
lr = np.log(Dc).diff(); vol = lr.rolling(30, min_periods=20).std() * np.sqrt(365); hist = Dc.notna().cumsum() >= 200
dv = QV.reindex(Dc.index)[cand].rolling(30, min_periods=20).sum().shift(1); elig = Dc.notna().cumsum().shift(1) >= 200
mfirst = ~Dc.index.to_period("M").duplicated()
pit10 = (dv.where(elig).rank(axis=1, ascending=False) <= 10)[mfirst].reindex(Dc.index).ffill().fillna(False).astype(bool)
fixed = pd.DataFrame(False, index=Dc.index, columns=cand); fixed[MAJ10] = True


def own_size(mem, n=10):
    w = (sig.reindex_like(Dc).fillna(0).clip(-2, 2) * (0.40 / vol).clip(upper=1.0)).where(hist, 0.0).fillna(0.0)
    return w.where(mem, 0.0) / n


def hourly(wd, cost=7.5):
    w = wd.reindex(wd.index.append(pd.DatetimeIndex([wd.index[-1] + pd.Timedelta(days=1)]))).shift(1)
    held = w.reindex(Hc.index.floor("D")).set_axis(Hc.index).fillna(0.0).where(Hc.ffill().notna(), 0.0)
    turn = w.fillna(0.0).diff().abs().sum(axis=1).reindex(Hc.index.floor("D")).set_axis(Hc.index).where(Hc.index.hour == 0, 0.0)
    rr = r.loc[Hc.index, cand]; ff = F.loc[Hc.index, cand]
    return (held * rr).sum(axis=1) - (held * ff).sum(axis=1) - turn.fillna(0.0) * cost / 1e4


dd = lambda h: h.groupby(h.index.floor("D")).sum()
shp = lambda h, a, z: round(float(dd(h.loc[a:z]).mean() / dd(h.loc[a:z]).std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
H0 = pd.read_parquet(DUMP).drop(columns="port").loc[:END + " 23:00"]
cf, cp = hourly(own_size(fixed)).reindex(H0.index).fillna(0.0), hourly(own_size(pit10)).reindex(H0.index).fillna(0.0)
out = {"part 1 C*": {"v86 C* sleeve 2022 / 2023-24 / 2025-26": per(H0["C*"]), "own-size fixed MAJ10": per(cf), "own-size point-in-time top-10": per(cp),
                     "corr v86 C* vs own-size fixed (daily)": round(float(pd.concat([dd(H0["C*"]), dd(cf)], axis=1).loc["2022":].corr().iloc[0, 1]), 3),
                     "2022-26 Sharpe fixed / pit": [shp(cf, "2022", END), shp(cp, "2022", END)],
                     "point-in-time top-10 membership share 2022-26": pit10.loc["2022":].mean().sort_values(ascending=False).head(20).round(2).to_dict()}}
print(json.dumps(out, indent=1), flush=True)
p20 = sleeve(20)[0].reindex(H0.index).fillna(0.0)
base = H0.drop(columns=["premium carry 60"]).assign(**{"C*": cp})
CANDS = {"K1 no carry, pit C*": base.drop(columns="premium carry"), "K2 pit 20-carry, pit C*": base.assign(**{"premium carry": p20}),
         "K3 no carry, pit C*, no alt kimchi": base.drop(columns=["premium carry", "alt kimchi"]),
         "K4 BTC/ETH core": H0[["ridge ML", "Weiss expiry", "delev bounce", "cascade limit strict", "trend 4h"]]}
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
HY = PF.PRESETS["HyroTrader Two-Step $200k"]
CFT = replace(PF.PRESETS["Crypto Fund Trader 2-Phase $100k"], name="CFT 2-Phase 200k", account=200000, fee=1200.0, targets=(0.08, 0.05))


def prop(h, f, a, z):
    x = h.loc[a:z]
    pb = PF.pipeline(to_daily_stop(x * 2.0, 0.5 * f.daily_loss), f, 5, 1, 1.0, 1.0, daily_fd=to_daily_stop(x * 1.5, 0.5 * f.daily_loss),
                     horizon_days=730, method="bootstrap", n_boot=400, block=20, seed=11)
    return {"net": round(pb["net_mean"]), "p10": round(pb["net_p10"]), "P_profit": round(pb["P_profit"], 3), "days_to_funded": pb["days_to_funded_median"]}


BK = {}; res = {}
for k, Hk in CANDS.items():
    b = unit(CS.portfolio_v5(Hk)[0]); BK[k] = b
    res[k] = {"Sharpe 2022-26 [2022, 2023-24, 2025-26]": [shp(b, "2022", END), per(b)], "HyroTrader 2022-24": prop(b, HY, "2022-01-01", "2024-12-31 23:00")}
    print(k, res[k], flush=True)
out["part 2 candidates (decision on 2022-24)"] = res
ok = [k for k in res if res[k]["HyroTrader 2022-24"]["P_profit"] >= 0.95]
top = max(res[k]["HyroTrader 2022-24"]["net"] for k in ok)
near = [k for k in ok if res[k]["HyroTrader 2022-24"]["net"] >= top - 5000]
ch = max(near, key=lambda k: res[k]["HyroTrader 2022-24"]["p10"]); b = BK[ch]
d = dd(b).loc["2022":END]; eq = (1 + 2.0 * d).cumprod()
out["part 3 chosen"] = {"book": ch, "sleeves": list(CANDS[ch].columns), "backtest Sharpe 2022-26": shp(b, "2022", END),
                        "planning Sharpe (x 1.78 / 3.11)": round(shp(b, "2022", END) * 1.78 / 3.11, 2),
                        "max DD at risk 2.0 (2022-26)": round(float((eq / eq.cummax() - 1).min()), 4), "worst day at risk 2.0": round(float(2 * d.min()), 4),
                        "HyroTrader 2-Step 200k": {"2022-24": res[ch]["HyroTrader 2022-24"], "2025-26 (holdout, once)": prop(b, HY, "2025-01-01", END + " 23:00")},
                        "CFT 2-Phase 200k": {"2022-24": prop(b, CFT, "2022-01-01", "2024-12-31 23:00"), "2025-26 (holdout, once)": prop(b, CFT, "2025-01-01", END + " 23:00")},
                        "for comparison v86 HyroTrader 2025-26": "net $182,863 / p10 $112,422 (survivorship-inflated)"}
b.to_frame("book").to_parquet(ROOT / "results/gen373_book_hourly.parquet")
(ROOT / "results/gen373.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out["part 3 chosen"], indent=1))
