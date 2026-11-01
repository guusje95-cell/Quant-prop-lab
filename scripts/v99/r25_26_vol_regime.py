"""v9.9 R25 (GARCH vol target) and R26 (HMM regime overlay), research/v99/r24_26_protocol.json. Writes results/v99/r25_26_vol_regime.json."""
import json
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import event_live as EL
from qpl.lab import binance_pack as B
warnings.filterwarnings("ignore")


def garch_forecast(x: pd.Series, refit=30, min_obs=365) -> pd.Series:
    """one-day-ahead GARCH(1,1) daily sd for day t from data up to t-1 (index t)"""
    from arch import arch_model
    x = x.dropna(); out = pd.Series(np.nan, index=x.index); par = None; s = 100.0
    for i in range(min_obs, len(x)):
        if par is None or (i - min_obs) % refit == 0:
            r = arch_model(x.iloc[:i] * s, mean="Zero", vol="GARCH", p=1, q=1).fit(disp="off"); par = r.params
            var = float(r.conditional_volatility.iloc[-1]) ** 2; last = float(x.iloc[i - 1] * s)
        else:
            last = float(x.iloc[i - 1] * s)
        var = par["omega"] + par["alpha[1]"] * last ** 2 + par["beta[1]"] * var
        out.iloc[i] = np.sqrt(var) / s
    return out


def portfolio_alt(H, vol=0.15, start="2022-01-01", kind="garch"):
    D = H.groupby(H.index.floor("D")).sum(); W = CS.v5_weights(D, list(H.columns)); Wh = W.reindex(H.index.floor("D")).set_axis(H.index)
    raw = (H * Wh).sum(axis=1); rawd = raw.groupby(raw.index.floor("D")).sum()
    lvl = (vol / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = (rawd * lvl).replace([np.inf, -np.inf], np.nan).dropna()
    g = garch_forecast(x1)                                                    # index t: forecast for day t+1 made with data to t
    sd30 = x1.rolling(30).std()
    est = g if kind == "garch" else (g + sd30) / 2
    tgt = (vol / (est * np.sqrt(365))).clip(upper=1.5).shift(1)                # used on the next day (same lag as portfolio_v5)
    mult = (lvl * tgt.reindex(lvl.index)).loc[start:]
    return (raw * mult.reindex(raw.index.floor("D")).set_axis(raw.index)).loc[start:].dropna()


def hmm_stress(index_days: pd.DatetimeIndex, refit=30, min_obs=730) -> pd.Series:
    from hmmlearn.hmm import GaussianHMM
    btc = B.k5("BTC").close.resample("1D").last(); r = np.log(btc).diff(); v = r.rolling(30).std()
    F = pd.concat([r, v], axis=1).dropna(); F.columns = ["r", "v"]; out = pd.Series(np.nan, index=F.index); model = None
    for i in range(min_obs, len(F)):
        if model is None or (i - min_obs) % refit == 0:
            Z = F.iloc[:i].to_numpy(); mu, sd = Z.mean(0), Z.std(0)
            model = GaussianHMM(n_components=2, covariance_type="full", n_iter=200, random_state=0).fit((Z - mu) / sd)
            stress = int(np.argmax(model.means_[:, 1]))
        Z = (F.iloc[max(0, i - 400):i].to_numpy() - mu) / sd                   # filtered probability with data to day i-1
        out.iloc[i] = model.predict_proba(Z)[-1, stress]
    return out.reindex(index_days).ffill()


def main():
    V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index; V7 = V.drop(columns="cascade limit strict")
    s8, _, _ = EL.pnl(idx); V8 = V7.assign(**{"listing short": s8})
    dd = lambda x: x.groupby(x.index.floor("D")).sum()
    unit = lambda x: x * 0.15 / (dd(x.loc["2022":"2024"]).std() * np.sqrt(365))
    def shp(x, a, z):
        d = dd(x.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3) if d.std() > 0 else None
    per = lambda x: [shp(x, "2022", "2022"), shp(x, "2023", "2024"), shp(x, "2025", "2026-09-30")]
    full = lambda b: [shp(b, "2022", "2026-09-30"), per(b)]
    ps = lambda r, ref: bool(r[0] >= ref[0] + 0.05 and all(r[1][i] >= ref[1][i] for i in range(3)))
    b0 = CS.portfolio_v5(V8)[0]; ref = full(unit(b0)); out = {"reference v9.8": ref}
    for k, name in (("garch", "R25 A GARCH(1,1) vol target"), ("avg", "R25 B mean of GARCH and 30-day std")):
        r = full(unit(portfolio_alt(V8, kind=k))); out[name] = {"book": r, "pass": ps(r, ref)}; print(name, out[name], flush=True)
    days = pd.DatetimeIndex(sorted(set(b0.index.floor("D")))); P = hmm_stress(days).shift(1)            # known the day before
    ph = P.reindex(b0.index.floor("D")).set_axis(b0.index).fillna(0.0)
    out["R26 share of days in stress"] = round(float((P.loc["2022":] > 0.5).mean()), 3)
    for name, m in (("R26 A x0.5 when P(stress) > 0.5", np.where(ph > 0.5, 0.5, 1.0)), ("R26 B x(1 - 0.5 P)", 1 - 0.5 * ph)):
        r = full(unit(b0 * m)); out[name] = {"book": r, "pass": ps(r, ref)}; print(name, out[name], flush=True)
    (ROOT / "results/v99/r25_26_vol_regime.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
