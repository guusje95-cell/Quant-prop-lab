"""Quant Trading Hub command line.

    python -m qpl.hub init                 create / migrate the database, ingest everything, seed prop rules, risk limits, schedules
    python -m qpl.hub status               one-screen status (accounts, jobs, alerts, experiments, prop facts)
    python -m qpl.hub worker [--once]      run the scheduler + job worker (independent of Claude and of the dashboard)
    python -m qpl.hub enqueue KIND [JSON]  queue a whitelisted job (ingest, risk, health, backup, validate_book, agent_step, ...)
    python -m qpl.hub jobs                 recent jobs
    python -m qpl.hub agent-plan           the research agenda with scores and blockers
    python -m qpl.hub backup | verify-backup FILE | restore FILE
    python -m qpl.hub finance-add KIND AMOUNT CUR STATUS [--firm F] [--ref R] [--note N]; finance-status ID STATUS; finance-report
Live trading cannot be enabled from here (there is no live adapter)."""
from __future__ import annotations

import argparse
import json
import sys

from qpl.hub import db as DB


def _print(x):
    print(json.dumps(x, indent=1, default=str))


def cmd_init(a):
    from qpl.hub import ingest, jobs, prop, risk, shadow
    c = DB.init(); out = {"migrations": "ok", "ingest": ingest.all_sources(c), "prop": prop.seed_from_project(c)}
    shadow.ensure_defaults(c); out["shadows"] = shadow.recompute(c)
    risk.ensure_defaults(c); jobs.ensure_schedules(c); _print(out)


def cmd_status(a):
    c = DB.init()
    s = {"db": str(DB.db_path()), "live_trading_enabled": DB.get_setting(c, "live_trading_enabled"),
         "paper_accounts": [dict(r) for r in c.execute("SELECT key, status, last_data_ts FROM paper_accounts ORDER BY key")],
         "jobs": {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status")},
         "open_alerts": [dict(r) for r in c.execute("SELECT id, level, source, message FROM alerts WHERE acknowledged_at IS NULL ORDER BY id DESC LIMIT 10")],
         "experiments": {r["kind"]: r["n"] for r in c.execute("SELECT kind, COUNT(*) n FROM experiments GROUP BY kind")},
         "trials_protocol_kind": c.execute("SELECT SUM(trials_added) FROM experiments WHERE kind='protocol'").fetchone()[0],
         "prop_facts": {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM prop_rule_facts GROUP BY status")},
         "last_backup": dict(c.execute("SELECT ts, path, verify_result FROM backups ORDER BY id DESC LIMIT 1").fetchone() or {})}
    _print(s)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m qpl.hub"); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init"); sp.add_parser("status"); sp.add_parser("jobs"); sp.add_parser("agent-plan"); sp.add_parser("backup"); sp.add_parser("finance-report")
    w = sp.add_parser("worker"); w.add_argument("--once", action="store_true")
    e = sp.add_parser("enqueue"); e.add_argument("kind"); e.add_argument("payload", nargs="?", default="{}")
    v = sp.add_parser("verify-backup"); v.add_argument("file"); r = sp.add_parser("restore"); r.add_argument("file")
    fa = sp.add_parser("finance-add"); fa.add_argument("kind"); fa.add_argument("amount", type=float); fa.add_argument("currency"); fa.add_argument("status")
    fa.add_argument("--firm"); fa.add_argument("--account"); fa.add_argument("--ref"); fa.add_argument("--note"); fa.add_argument("--ts")
    fs = sp.add_parser("finance-status"); fs.add_argument("id", type=int); fs.add_argument("status"); fs.add_argument("--note")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        return cmd_init(a)
    if a.cmd == "status":
        return cmd_status(a)
    if a.cmd == "worker":
        from qpl.hub import worker
        return _print(worker.run(once=a.once))
    c = DB.init()
    if a.cmd == "enqueue":
        from qpl.hub import jobs
        return _print({"job": jobs.enqueue(c, a.kind, json.loads(a.payload), dedup_key=f"manual:{a.kind}:{a.payload}", actor="user")})
    if a.cmd == "jobs":
        return _print([dict(r) for r in c.execute("SELECT id, kind, status, attempts, created_at, finished_at, substr(error,1,120) error FROM jobs ORDER BY id DESC LIMIT 30")])
    if a.cmd == "agent-plan":
        from qpl.hub import agent
        return _print(agent.plan(c))
    if a.cmd == "backup":
        return _print(DB.backup(c))
    if a.cmd == "verify-backup":
        from pathlib import Path
        return _print(DB.verify_backup(c, Path(a.file)))
    if a.cmd == "restore":
        from pathlib import Path
        c.close(); return _print({"restored_to": str(DB.restore(Path(a.file)))})
    if a.cmd == "finance-add":
        from qpl.hub import finance
        return _print({"id": finance.add(c, a.kind, a.amount, a.currency, a.status, ts=a.ts, firm=a.firm, account=a.account, external_ref=a.ref, note=a.note)})
    if a.cmd == "finance-status":
        from qpl.hub import finance
        finance.set_status(c, a.id, a.status, a.note); return _print({"ok": True})
    if a.cmd == "finance-report":
        from qpl.hub import finance
        return _print(finance.report(c))


if __name__ == "__main__":
    sys.exit(main())
