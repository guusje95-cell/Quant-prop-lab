"""V6 research helpers: period slicing, residual metrics, Newey-West, Holm, recording to registry+ledger."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtesting import panel as PB
from ..statistics import tests as T
from . import factory as F
from . import registry as R

ROOT = Path(__file__).resolve().parents[3]


def protocol(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text())


def metrics(d: pd.DataFrame, bench: pd.Series | None, a: str, z: str, d2: pd.DataFrame | None = None) -> dict:
    x = d.loc[a:z]
    m = PB.stats(x["net"])
    m["gross_sharpe"] = PB.stats(x["gross"])["sharpe"]
    m["cost_ann"] = float(x["cost"].mean() * PB.ANN)
    m["turnover_ann"] = float(x["turnover"].mean() * PB.ANN)
    m["mean_gross_lev"] = float(x["gross_lev"].mean())
    t, p = T.newey_west_t(x["net"].to_numpy(), lags=10) if len(x) > 50 else (0.0, 1.0)
    m["nw_t"], m["nw_p_one_sided"] = t, p
    if bench is not None:
        m["residual_sharpe"], m["beta"] = PB.residual(x["net"], bench.loc[a:z])
    if d2 is not None:
        m["net_sharpe_2x_cost"] = PB.stats(d2.loc[a:z, "net"])["sharpe"]
    m["by_year"] = {int(k): round(float(v), 4) for k, v in x["net"].groupby(x.index.year).sum().items()}
    return m


def holm(pvals: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, stop = len(items), {}, False
    for i, (k, p) in enumerate(items):
        ok = (not stop) and p <= alpha / (m - i)
        stop = stop or not ok
        out[k] = ok
    return out


def record(hyp_id: str, family: str, label: str, params: dict, stage: str, m: dict, generation: int, proto: str, instrument: str) -> int:
    rid = R.record(generation=generation, family=family, hypothesis_id=hyp_id, strategy=label, instrument=instrument,
                   data_source="pysystemtrade@bbe29e19" if "futures" in proto else "see protocol", timeframe="1D", params=params,
                   stage=stage, period=stage, train_period="", validation_period="", oos_period="", metrics=m, decision="info", reason=f"v6 {proto}")
    F.append({"kind": "experiment", "registry_id": rid, "hypothesis_id": hyp_id, "asset_class": "futures_panel" if "futures" in proto else "other",
              "signal": label, "params": params, "stage": stage, "protocol": proto,
              "summary": {k: m.get(k) for k in ("sharpe", "residual_sharpe", "gross_sharpe", "max_dd", "net_sharpe_2x_cost", "nw_t")}})
    return rid
