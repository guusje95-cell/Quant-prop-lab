"""Historical REPLAY of the crypto paper trader (NOT elapsed paper time) + reconciliation against the research engine.
Spot and perp accounts are reported separately. Period: protected-holdout window 2024-01-01..2026-10-08 (already viewed)."""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.execution import paper_crypto as P
from qpl.research import crypto_factory as CF
from qpl.strategies import crypto as CS
ROOT = Path(__file__).resolve().parents[1]
b = CD.btc_bars("1D").loc["2014-06-01":"2026-10-08"]
fund, actual = CF.btc_funding()
START = pd.Timestamp("2024-01-01", tz="UTC")
out = {"label": "historical replay through the paper-trading stack; not live and not elapsed paper time"}
logdir = ROOT / "paper_trading" / "crypto_replay"; logdir.mkdir(parents=True, exist_ok=True)
for kind in ("perp", "spot"):
    acct = P.PerpAccount(fee_bps=5, slip_bps=2) if kind == "perp" else P.SpotAccount(fee_bps=10, slip_bps=5)
    log = logdir / f"{kind}_log.jsonl"; log.unlink(missing_ok=True)
    r = P.CryptoPaperRunner(acct, log_path=log)
    if kind == "perp":
        for ts, rate in fund.loc[START:].items():
            r.add_funding(ts, rate)
    for row in b.itertuples():
        (r.on_bar if row.Index >= START else r.warmup)(row.Index, row.open, row.high, row.low, row.close)
    h = pd.DataFrame(r.history).set_index("ts")
    eq = h["equity"]
    dret = eq.pct_change().dropna()
    # research engine at the same book scale and comparable costs
    w = CS.trend_ensemble(b, {}) * 0.30
    if kind == "spot":
        w = w.clip(lower=0)
    cost = 7.0 if kind == "perp" else 15.0
    ref = VB.daily(VB.run(b, w, cost, fund if kind == "perp" else None, perp=(kind == "perp")), at="realized")["net"].loc[dret.index]
    # paper equity at close t includes the move open t -> close t and close t-1 -> open t; engine uses open-to-open,
    # so compare cumulative returns (levels) and daily correlation
    out[kind] = {"final_equity": float(eq.iloc[-1]), "paper_total_return": float(eq.iloc[-1] / 10_000 - 1),
                 "engine_total_return_additive": float(ref.sum()), "paper_sharpe": float(dret.mean() / dret.std() * np.sqrt(365)),
                 "engine_sharpe": VB.stats(ref)["sharpe"], "daily_corr_paper_vs_engine": float(dret.corr(ref)),
                 "max_dd_paper": float((eq / eq.cummax() - 1).min()), "n_fills": len(r.acct.fills),
                 "fees_paid": float(sum(f["fee"] for f in r.acct.fills)),
                 "funding_paid": float(getattr(r.acct, "funding_paid", 0.0)),
                 "risk_events": [e for e in (json.loads(x) for x in open(log)) if e["kind"] == "risk"][:10],
                 "guard_events": r.guard.events[:10], "killed": r.risk.killed}
(ROOT / "results/v4_paper_crypto_replay.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(out, indent=1, default=str))
