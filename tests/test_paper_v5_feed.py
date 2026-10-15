"""Paper v5 data feed: parses Binance public responses (mocked, no network) into the research-pack formats, and the loaders
overlay the live folder on the pack and honour the cutoff."""
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.live import binance_public as BP  # noqa: E402


def _kl(t0, n, step_ms, px=100.0):
    return [[t0 + i * step_ms, str(px), str(px + 1), str(px - 1), str(px + 0.5), "10", t0 + (i + 1) * step_ms - 1, "1000", 50, "6", "600", "0"]
            for i in range(n)]


class FakeClient:
    def __init__(self, now):
        self.now = now

    def get(self, url, params):
        t = int(params.get("startTime", 0))
        if url.endswith("/fapi/v1/klines"):
            return _kl(t, 24, 300_000) if t < self.now else []
        if url.endswith("premiumIndexKlines"):
            return _kl(t, 2, 3_600_000, px=0.0001) if t < self.now else []
        if url.endswith("fundingRate"):
            return [{"fundingTime": t + 3_600_000, "fundingRate": "0.0001"}] if t < self.now else []
        if url.endswith("openInterestHist"):
            return [{"timestamp": t + i * 300_000, "sumOpenInterest": "5", "sumOpenInterestValue": "500"} for i in range(3)] if t < self.now else []
        if url.endswith("/api/v3/klines"):
            return _kl(t, 3, 86_400_000) if t < self.now else []
        raise AssertionError(url)


def test_update_writes_pack_formats(tmp_path, monkeypatch):
    pack = ROOT / "research_data" / "binance"
    if not (pack / "BTCUSDT_5m.parquet").exists():
        import pytest
        pytest.skip("research pack not present")
    now = pd.Timestamp("2026-10-01 02:00")
    monkeypatch.setattr(BP, "Client", lambda: FakeClient(int(now.value // 1_000_000)))
    live = tmp_path / "live"; spot_base = tmp_path / "spot.parquet"
    n = BP.update(pack, live, ["BTC"], ["BTC"], now=now, log=lambda *_: None, spot_base=spot_base)
    assert n["5m"] > 0 and n["funding"] > 0 and n["premium"] > 0 and n["spot"] > 0
    assert n["oi"] == 0                       # the pack's open interest already runs past `now`: nothing to fetch
    k = pd.read_parquet(live / "BTCUSDT_5m.parquet")
    ref = pd.read_parquet(pack / "BTCUSDT_5m.parquet").iloc[:2]
    assert list(k.columns) == list(ref.columns) and k.index.name == "time" and k.index.min() == pd.Timestamp("2026-10-01 00:00")
    assert (k.index + pd.Timedelta(minutes=5) <= now).all()                    # only closed bars
    for name in ("funding", "premium_1h"):
        a = pd.read_parquet(live / f"BTCUSDT_{name}.parquet"); b = pd.read_parquet(pack / f"BTCUSDT_{name}.parquet").iloc[:1]
        assert set(b.columns) <= set(a.columns), name
    s = pd.read_parquet(spot_base)
    assert s.index.name == "t" and ("BTC", "close") in s.columns
    # second update with nothing new appends nothing and keeps files valid
    BP.update(pack, live, ["BTC"], ["BTC"], now=now, log=lambda *_: None, spot_base=spot_base)
    assert pd.read_parquet(live / "BTCUSDT_5m.parquet").index.is_unique
    # loaders overlay live on the pack and respect the cutoff (fresh process: settings are read at import)
    code = ("import sys; sys.path.insert(0, 'src'); from qpl.lab import binance_pack as B; k = B.k5('BTC'); "
            "print(k.index.max(), len(B.funding('BTC')), B.premium('BTC').index.max())")
    env = {**os.environ, "QPL_LIVE_PACK": str(live), "QPL_CUTOFF": "2026-10-01 01:00"}
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout
    assert out.startswith("2026-10-01 00:55:00"), out
    assert "2026-10-01 00:00:00" in out.split()[-2] + " " + out.split()[-1]
