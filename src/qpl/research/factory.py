"""Research factory (v3): pre-registered hypotheses, standard variant evaluation, append-only ledger.

Ledger: research_database/ledger.jsonl. Every line is an event with `prev` (hash of the previous
line) and `hash` (sha256 of the canonical event incl. prev), so silent edits or deletions break
the chain (`verify_ledger()`). The SQLite registry keeps working for queries; the ledger is the
tamper-evident record.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtesting import accounting as A
from ..instruments import get
from ..statistics import metrics as M
from . import pipeline as P
from . import registry as R

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "research_database" / "ledger.jsonl"
HYP_DIR = ROOT / "research_database" / "hypotheses"

COST_ASSUMPTIONS = {
    "slippage": "1 tick per side on market/stop orders (applied post-hoc), 0 on limit targets",
    "commission_rt": "ES/NQ/YM $2.80, MES/MNQ/MYM $0.74 per contract round turn (ASSUMPTION)",
    "normalization": "historical point P&L rescaled to price level at 2025-03-21 (pipeline.REF_PRICE)",
    "fills": "signal at bar close, market fill at next bar open; stop before target intrabar",
}


def _canon(o) -> str:
    return json.dumps(o, sort_keys=True, default=str, separators=(",", ":"))


def _last_hash() -> str:
    if not LEDGER.exists():
        return "GENESIS"
    last = None
    with open(LEDGER) as f:
        for line in f:
            if line.strip():
                last = line
    return json.loads(last)["hash"] if last else "GENESIS"


def append(event: dict) -> str:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    ev = dict(event)
    ev.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
    ev["prev"] = _last_hash()
    ev["hash"] = hashlib.sha256(_canon({k: v for k, v in ev.items() if k != "hash"}).encode()).hexdigest()
    with open(LEDGER, "a") as f:
        f.write(_canon(ev) + "\n")
    return ev["hash"]


def verify_ledger() -> tuple[bool, int]:
    prev = "GENESIS"
    n = 0
    if not LEDGER.exists():
        return True, 0
    with open(LEDGER) as f:
        for line in f:
            if not line.strip():
                continue
            ev = json.loads(line)
            h = hashlib.sha256(_canon({k: v for k, v in ev.items() if k != "hash"}).encode()).hexdigest()
            if ev["prev"] != prev or ev["hash"] != h:
                return False, n
            prev = ev["hash"]
            n += 1
    return True, n


@dataclass
class Hypothesis:
    id: str
    family: str
    statement: str
    mechanism: str
    falsification: str
    data_required: str
    params_tested: str
    baseline: str
    promotion: str
    sources: list = field(default_factory=list)   # [{"title", "url", "published", "sample", "limitations"}]
    generation: int = 7

    def register(self) -> None:
        HYP_DIR.mkdir(parents=True, exist_ok=True)
        doc = asdict(self)
        p = HYP_DIR / f"{self.id}.json"
        if not p.exists():                        # first registration is the pre-registration
            p.write_text(json.dumps(doc, indent=1))
            append({"kind": "hypothesis_registered", "hypothesis": doc})
        R.register_hypothesis(self.id, self.family, self.generation, doc, status="open")


def regime_labels(ctx: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Ex-ante daily regime labels: trend (prior close vs 200d SMA) and vol tercile (20d realized,
    terciles fixed on TRAIN only)."""
    rc = ctx.groupby("date")["close"].last()
    rc.index = pd.DatetimeIndex(rc.index)
    rc = rc.reindex(days).ffill()
    sma = rc.rolling(200, min_periods=150).mean().shift(1)
    trend = np.where(rc.shift(1) > sma, "bull", "bear")
    rv = np.log(rc).diff().rolling(20).std().shift(1)
    tr = rv.loc[P.SPLITS["train"][0]:P.SPLITS["train"][1]]
    q = tr.quantile([1 / 3, 2 / 3]).to_numpy()
    vol = np.where(rv <= q[0], "low", np.where(rv <= q[1], "mid", "high"))
    return pd.DataFrame({"trend": trend, "vol": vol}, index=days)


def evaluate_variant(hyp: Hypothesis, strategy: str, fut: str, proxy: str, params: dict, tf: str = "M15",
                     session: tuple[int, int] = (570, 960), periods: dict | None = None, source: str = "dukascopy",
                     stage: str = "screen", influenced: str | None = None, extra: dict | None = None,
                     record: bool = True) -> dict:
    periods = periods or {"train": P.SPLITS["train"], "validation": P.SPLITS["validation"]}
    ctx = P.context(source, proxy, tf, *session)
    days = P.trading_days(ctx)
    inst = get(fut)
    fn = P.SI.STRATEGIES[strategy]
    orders = fn(ctx, params)
    n_signal_bars = int((orders.entry_dir != 0).sum())
    tr = P.backtest(strategy, ctx, params, inst)
    norm = source == "dukascopy"
    net = P.usd(tr, inst, contracts=1, norm=norm)
    gross = P.usd(tr, inst, contracts=1, cost_mult=0, slip_mult=0, norm=norm)
    dn, dg = A.daily_pnl(net, days), A.daily_pnl(gross, days)
    reg = regime_labels(ctx, days)
    rec = {"periods": {}}
    for name, (a, b) in periods.items():
        m = M.summarize(dn.loc[a:b, "pnl"], net[(net.day >= a) & (net.day <= b)])
        g = M.summarize(dg.loc[a:b, "pnl"], gross[(gross.day >= a) & (gross.day <= b)])
        x = dn.loc[a:b, "pnl"]
        yrs = x.groupby(x.index.year).sum()
        rr = reg.loc[a:b]
        by_reg = {}
        for col in ("trend", "vol"):
            for k, v in x.groupby(rr[col]):
                by_reg[f"{col}:{k}"] = {"days": int(len(v)), "total": float(v.sum()),
                                        "sharpe": float(v.mean() / v.std() * np.sqrt(252)) if v.std() > 0 else None}
        tt = net[(net.day >= a) & (net.day <= b)]
        eh = pd.DatetimeIndex(tt.entry_ts).tz_convert("America/New_York").hour if len(tt) else []
        rec["periods"][name] = {
            "net": m, "gross_sharpe": g["sharpe"], "gross_total": g["total_usd"], "gross_expectancy": g.get("expectancy_usd"),
            "by_year": {int(k): float(v) for k, v in yrs.items()}, "pct_years_positive": float((yrs > 0).mean()) if len(yrs) else None,
            "by_regime": by_reg,
            "by_entry_hour_ET": {int(k): float(v) for k, v in tt.groupby(eh).pnl_usd.sum().items()} if len(tt) else {},
            "worst_day": float(x.min()) if len(x) else None,
            "cvar5_day": float(x[x <= x.quantile(0.05)].mean()) if len(x) > 20 else None,
        }
    rec.update({"signal_bars": n_signal_bars, "trades_total": int(len(tr)),
                "rejected_signal_bars": int(max(n_signal_bars - len(tr), 0))})
    if extra:
        rec.update(extra)
    if record:
        meta = dict(generation=hyp.generation, family=hyp.family, hypothesis_id=hyp.id, strategy=strategy, instrument=fut,
                    data_source=f"{source}:{proxy}", timeframe=tf, params={**params, "session": list(session)}, stage=stage,
                    period=",".join(periods), train_period=str(periods.get("train")), validation_period=str(periods.get("validation")),
                    oos_period=str(periods.get("oos")), metrics=rec, decision="info",
                    reason=f"v3 factory; influenced={influenced}")
        rid = R.record(**meta)
        append({"kind": "experiment", "registry_id": rid, **{k: v for k, v in meta.items() if k != "metrics"},
                "cost_assumptions": COST_ASSUMPTIONS, "code_version": R.code_version(), "data_version": R.data_version(),
                "summary": {p: {"net_sharpe": v["net"]["sharpe"], "gross_sharpe": v["gross_sharpe"],
                                "net_total": v["net"]["total_usd"], "trades": v["net"].get("trades", 0),
                                "max_dd": v["net"]["max_dd_usd"]} for p, v in rec["periods"].items()}})
        rec["registry_id"] = rid
    return rec


def decide(hyp: Hypothesis, verdict: str, reason: str, evidence: dict | None = None) -> None:
    """verdict in REJECT / EXPLORATORY / VALIDATION_CANDIDATE / PAPER_TRADING_CANDIDATE / PROP_EVALUATION_CANDIDATE."""
    R.set_verdict(hyp.id, verdict, reason)
    append({"kind": "decision", "hypothesis_id": hyp.id, "verdict": verdict, "reason": reason, "evidence": evidence or {}})
