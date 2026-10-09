"""Regenerate v6/V6_HYPOTHESIS_REGISTRY.csv from the SQLite registry + hash-chained ledger (single source of truth)."""
import csv, json, sqlite3, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
c = sqlite3.connect(ROOT / "research_database/experiments.sqlite")
ev = [json.loads(l) for l in open(ROOT / "research_database/ledger.jsonl")]
rec, var, stages, last_dec = defaultdict(int), defaultdict(set), defaultdict(set), {}
for e in ev:
    h = e.get("hypothesis_id")
    if e["kind"] == "experiment" and h:
        rec[h] += 1
        var[h].add((json.dumps(e.get("params"), sort_keys=True), e.get("rule"), e.get("cost_bps"), e.get("signal")))
        stages[h].add(str(e.get("stage")).split(":")[-1])
    if e["kind"] == "decision":
        last_dec[h] = (e["verdict"], e.get("ts"))
# experiments recorded only in sqlite (v1/v3 futures) - count by hypothesis_id column if present
cols = [r[1] for r in c.execute("pragma table_info(experiments)")]
sql_counts = dict(c.execute("select hypothesis_id, count(*) from experiments group by hypothesis_id").fetchall()) if "hypothesis_id" in cols else {}
rows = []
for hid, fam, gen, doc, status, verdict in c.execute("select id,family,generation,doc,status,verdict from hypotheses"):
    d = json.loads(doc) if doc else {}
    rows.append({"id": hid, "generation": gen, "family": fam, "status": status,
                 "statement": d.get("statement", ""), "mechanism": d.get("mechanism", ""), "falsification": d.get("falsification", ""),
                 "data": d.get("data_required", ""), "params_tested": d.get("params_tested", ""),
                 "ledger_records": rec.get(hid, 0), "ledger_unique_variants": len(var.get(hid, ())), "sqlite_records": sql_counts.get(hid, 0),
                 "stages": ";".join(sorted(stages.get(hid, ()))), "last_decision": (last_dec.get(hid) or ("", ""))[0],
                 "decided_at": (last_dec.get(hid) or ("", ""))[1], "verdict_reason": (verdict or "")[:400]})
MAP = {"REJECT": "REJECTED", "rejected": "REJECTED", "REJECTED": "REJECTED", "EXPLORATORY": "EXPLORATORY",
       "VALIDATION_CANDIDATE": "PROMISING_BUT_UNVALIDATED", "PROMISING_BUT_UNVALIDATED": "PROMISING_BUT_UNVALIDATED",
       "PAPER_TRADING_CANDIDATE": "PROMISING_BUT_UNVALIDATED", "ELIGIBLE_FOR_INDEPENDENT_VALIDATION": "ELIGIBLE_FOR_INDEPENDENT_VALIDATION"}
for r in rows:
    r["v6_status"] = MAP.get(r["status"], r["status"])
rows.sort(key=lambda r: (r["generation"] or 0, r["id"]))
out = ROOT / "v6" / "V6_HYPOTHESIS_REGISTRY.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"wrote {out}: {len(rows)} hypotheses")
