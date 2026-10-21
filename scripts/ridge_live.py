"""Gen108 ridge ML (v7 sleeve "ridge ML", Gen109) for paper trading: same features, same monthly walk-forward refit, but every input is
read through a live-aware loader (research copy + QPL_LIVE_PACK/ml overlay, cut at QPL_CUTOFF).

    python scripts/ridge_live.py check     # research data only: must reproduce results/gen108_preds.parquet (ridge) exactly

ridge_weights() -> daily BTC/ETH weights (row d = decided at the close of d, held during d+1), 0.5 x clipped prediction."""
import os
import sys
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
MORE = ROOT / "research_data/more"
COINS = ("BTC", "ETH")


def _live(name):
    p = os.environ.get("QPL_LIVE_PACK")
    return Path(p) / "ml" / name if p else None


def _cut():
    c = os.environ.get("QPL_CUTOFF")
    return pd.Timestamp(c) if c else None


def _overlay(base: Path, name: str) -> pd.DataFrame:
    frames = [pd.read_parquet(base)] if base.exists() else []
    lv = _live(name)
    if lv is not None and lv.exists():
        frames.append(pd.read_parquet(lv))
    d = pd.concat(frames); d.index = pd.DatetimeIndex(d.index)
    if d.index.tz is not None:
        d.index = d.index.tz_localize(None)
    return d[~d.index.duplicated(keep="last")].sort_index()


def upbit(c):
    """Upbit KRW hourly closes (bar stamped at its open, known once the hour is over)."""
    s = _overlay(MORE / f"upbit_KRW-{c}_1h.parquet", f"upbit_KRW-{c}_1h.parquet")["close"]
    cut = _cut()
    return s[s.index + pd.Timedelta(hours=1) <= cut] if cut is not None else s


def usdkrw():
    """Yahoo USD/KRW daily close dated by its London day (Gen105 strict dating). A day's close counts once that London day is over."""
    fx0 = _overlay(MORE / "yahoo_USDKRW_1d.parquet", "yahoo_USDKRW_1d.parquet")["close"]
    lt = pd.DatetimeIndex(fx0.index).tz_localize("UTC").tz_convert("Europe/London"); ld = lt.normalize()
    final = pd.Series(lt == ld)                       # the finished daily bar is stamped at London midnight; a bar still forming
    order = final.reset_index(drop=True).sort_values(kind="stable").index   # carries the fetch time: the finished bar wins
    fx0, ld = fx0.iloc[order], ld[order]
    fx = pd.Series(fx0.to_numpy(), index=ld.tz_localize(None)); fx = fx[~fx.index.duplicated(keep="last")].sort_index()
    cut = _cut()
    if cut is not None:
        end_london = (ld + pd.Timedelta(days=1)).tz_convert("UTC").tz_localize(None)       # end of each London day in UTC
        keep = pd.Series(end_london <= cut, index=ld.tz_localize(None)); keep = keep[~keep.index.duplicated(keep="last")].sort_index()
        fx = fx[keep.reindex(fx.index).to_numpy()]
    return fx


def dvol(c):
    """Deribit DVOL daily bars (stamped at the day's start, known at its end)."""
    s = _overlay(ROOT / f"data/raw/deribit/{c}_DVOL.parquet", f"{c}_DVOL.parquet")["close"]
    s.index = s.index.normalize(); s = s[~s.index.duplicated(keep="last")]
    cut = _cut()
    return s[s.index + pd.Timedelta(days=1) <= cut] if cut is not None else s


def zk_strict(c, bn_hourly):
    """Kimchi premium z-score (Gen105 strict, reproduces results/gen105_zk_strict.parquet exactly)."""
    fx = usdkrw(); up = upbit(c)
    fxh = fx.shift(1).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
    kp = (up / fxh / bn_hourly.reindex(up.index) - 1).dropna(); kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
    return (kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()


def spot_hourly(c):
    """Binance SPOT hourly klines with taker-buy volume (Gen247 B, bf2 ridge): research copy + QPL_LIVE_PACK/ml/spot overlay, cut."""
    s = _overlay(ROOT / f"research_data/binance_spot/{c}USDT_1h.parquet", f"spot/{c}USDT_1h.parquet")
    cut = _cut()
    return s[s.index + pd.Timedelta(hours=1) <= cut] if cut is not None else s


def features(end, spot=False):
    from qpl.lab import binance_pack as B
    from qpl.lab.data import stablecoin_caps
    import cfd_book as CB
    days = pd.date_range("2020-01-01", pd.Timestamp(end).floor("D"))
    caps = stablecoin_caps(); caps = caps.where(caps > 0); caps.index = pd.DatetimeIndex(caps.index).normalize()
    stab = (caps / caps.shift(1) - 1).shift(2).reindex(days)
    rows = []
    for c in COINS:
        k = B.k5(c).loc[:pd.Timestamp(end).floor("D") + pd.Timedelta(hours=23, minutes=55)]
        close = k.close.resample("1D").last().reindex(days); ret = close.pct_change()
        f = pd.DataFrame(index=days)
        for n in (1, 3, 7, 30):
            f[f"r{n}"] = close / close.shift(n) - 1
        f["vol7"] = ret.rolling(7).std(); f["vol30"] = ret.rolling(30).std()
        fu = B.funding(c); fd = fu.groupby((fu.index - pd.Timedelta(seconds=1)).floor("D")).sum().reindex(days)
        f["fund1"] = fd; f["fund7"] = fd.rolling(7).mean()
        pm = B.premium(c)["close"]; f["prem"] = pm.groupby(pm.index.floor("D")).mean().reindex(days)
        oi = B.metrics(c)["sum_open_interest_value"]; oi = oi.where(oi > 0).resample("1D").last().reindex(days)
        f["oi1"] = oi / oi.shift(1) - 1; f["oi7"] = oi / oi.shift(7) - 1
        tb = k["taker_buy_volume"].resample("1D").sum(); vv = k["volume"].resample("1D").sum()
        f["imb"] = ((2 * tb - vv) / vv).reindex(days)
        bn = k.close.resample("1h").last(); cb = CB.coinbase(f"{c}-USD"); prem = (cb / bn - 1).dropna()
        p24 = prem.rolling(24, min_periods=20).mean(); zc = (p24 - p24.rolling(720, min_periods=480).mean()) / p24.rolling(720, min_periods=480).std()
        f["zc"] = zc.resample("1D").last().reindex(days)
        f["zk"] = zk_strict(c, bn).reindex(days)
        dv = dvol(c); f["dvol1"] = (dv / dv.shift(1) - 1).reindex(days)
        f["stab"] = stab; f["is_eth"] = 1.0 if c == "ETH" else 0.0
        f["target"] = ret.shift(-1); f["coin"] = c
        if spot:                                                     # Gen247 B: spot taker imbalance and spot - perp divergence
            sp = spot_hourly(c).loc[:pd.Timestamp(end).floor("D") + pd.Timedelta(hours=23)]; sd = sp.resample("1D").sum()
            simb = ((2 * sd["taker_buy_volume"] - sd["volume"]) / sd["volume"]).replace([np.inf, -np.inf], np.nan).reindex(days)
            f["simb"] = simb; f["sdiv"] = simb - f["imb"].replace([np.inf, -np.inf], np.nan)
        rows.append(f)
    return pd.concat(rows).reset_index().rename(columns={"index": "day"})


def predictions(end, spot=False):
    D = features(end, spot); feats = [x for x in D.columns if x not in ("day", "target", "coin")]
    out = pd.Series(np.nan, index=D.index)
    for m in pd.date_range("2021-01-01", pd.Timestamp(end).floor("D"), freq="MS"):
        tr = D[(D["day"] >= "2020-03-01") & (D["day"] < m - pd.Timedelta(days=1))].dropna(subset=["target"])
        te = D[(D["day"] >= m) & (D["day"] < m + pd.offsets.MonthBegin(1))]
        if len(te) == 0:
            continue
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = ((tr[feats] - mu) / sd).fillna(0.0).clip(-5, 5); Xte = ((te[feats] - mu) / sd).fillna(0.0).clip(-5, 5)
        mdl = Ridge(alpha=10.0).fit(Xtr, tr["target"]); s = np.std(mdl.predict(Xtr)) or 1.0
        out.loc[te.index] = np.clip(mdl.predict(Xte) / s, -1, 1)
    D["ridge"] = out
    return D


def ridge_weights(end=None, spot=False):
    """Daily target weights for the 'ridge ML' sleeve (spot=True: bf2's Gen247 B ridge with spot taker features):
    row d is decided at the close of day d (only complete days count)."""
    import crypto_sleeves as CS
    end = pd.Timestamp(end or CS.END)
    last_full = (end + pd.Timedelta(hours=1)).floor("D") - pd.Timedelta(days=1)          # the last day whose close is known
    D = predictions(last_full, spot)
    return D.pivot(index="day", columns="coin", values="ridge").loc[:last_full].fillna(0.0) * 0.5


if __name__ == "__main__" and sys.argv[1:] == ["check"]:
    os.environ.pop("QPL_LIVE_PACK", None); os.environ.pop("QPL_CUTOFF", None)
    D = predictions("2026-09-30"); ref = pd.read_parquet(ROOT / "results/gen108_preds.parquet")
    a = D.set_index(["day", "coin"])["ridge"]; b = ref.set_index(["day", "coin"])["ridge"].reindex(a.index)
    m = a.notna() | b.notna()
    print("rows", int(m.sum()), "max abs diff", float((a - b)[m].abs().max()), "corr", float(a[m].corr(b[m])))
