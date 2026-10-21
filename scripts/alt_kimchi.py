"""Gen247 A (adopted in v8): kimchi premium on altcoins. weights() -> daily weights per altcoin (row d = decided at the close of d,
held during d+1): +0.1 if z > 1, -0.1 if z < -1. Live-aware through ridge_live's loaders (Upbit / USD-KRW overlays, QPL_CUTOFF)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import ridge_live as RL
MORE = ROOT / "research_data/more"


def coins():
    from qpl.lab import binance_pack as B
    return [c for c in B.coins() if c not in ("BTC", "ETH") and (MORE / f"upbit_KRW-{c}_1h.parquet").exists()]


def zscores(end=None, fx_lag=1):
    from qpl.lab import binance_pack as B
    import crypto_sleeves as CS
    end = pd.Timestamp(end or CS.END); last_full = (end + pd.Timedelta(hours=1)).floor("D") - pd.Timedelta(days=1)
    days = pd.date_range("2020-01-01", last_full); fx = RL.usdkrw(); out = {}
    for c in coins():
        up = RL.upbit(c); bn = B.k5(c).close.resample("1h").last()
        fxh = fx.shift(fx_lag).reindex(up.index.floor("D"), method="ffill").set_axis(up.index)
        kp = (up / fxh / bn.reindex(up.index) - 1).dropna().loc[:last_full + pd.Timedelta(hours=23)]
        kd = kp[kp.index.hour == 23]; kd.index = kd.index.floor("D")
        out[c] = ((kd - kd.rolling(30, min_periods=20).mean()) / kd.rolling(30, min_periods=20).std()).reindex(days)
    return pd.DataFrame(out)


def weights(end=None, th=1.0, size=0.1):
    z = zscores(end)
    return pd.DataFrame(np.where(z > th, size, np.where(z < -th, -size, 0.0)), index=z.index, columns=z.columns)


if __name__ == "__main__" and sys.argv[1:] == ["check"]:            # must reproduce the Gen247 A weights exactly
    import os
    os.environ.pop("QPL_LIVE_PACK", None); os.environ.pop("QPL_CUTOFF", None); os.environ["QPL_END"] = "2026-09-30 23:00"
    w = weights("2026-09-30 23:00"); print(w.shape, float(w.abs().sum().sum()))
