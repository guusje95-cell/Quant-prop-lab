"""Whitelisted job handlers. Each takes (connection, payload) and returns a JSON-able result. None of them can trade, spend money,
read credentials or run arbitrary commands: `run_script` only runs Python files under ALLOWED_SCRIPT_DIRS, with a timeout."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from qpl.hub import db as DB
from qpl.hub.db import ROOT, alert, now

ALLOWED_SCRIPT_DIRS = ("scripts/v99/", "scripts/hub_research/")


def h_ingest(c, p):
    from qpl.hub import ingest, shadow
    out = {"protocols": ingest.protocols(c), "paper": ingest.paper_accounts(c), "datasets": ingest.datasets(c)} if p.get("light", True) else ingest.all_sources(c)
    shadow.ensure_defaults(c); out["shadows"] = shadow.recompute(c)
    return out


def h_risk(c, p):
    from qpl.hub import risk
    return {r["key"]: risk.evaluate(c, r["key"]) for r in c.execute("SELECT key FROM paper_accounts").fetchall()}


def h_health(c, p):
    from qpl.hub import health
    out = {}
    for r in c.execute("SELECT key FROM paper_accounts").fetchall():
        try:
            rep = health.check_account(c, r["key"]); out[r["key"]] = {"status": rep["status"], "findings": rep["findings"]}
        except Exception as e:                                        # noqa: BLE001 - one account must not block the others
            out[r["key"]] = {"status": "error", "error": str(e)}
    return out


def h_backup(c, p):
    return DB.backup(c)


def h_prop_staleness(c, p):
    from qpl.hub import prop
    prop.load_fact_files(c)
    st = prop.stale_facts(c)
    unver = c.execute("SELECT COUNT(*) FROM prop_rule_facts f JOIN prop_rule_sets s ON s.id=f.rule_set_id WHERE s.superseded_at IS NULL AND f.status<>'verified'").fetchone()[0]
    if st:
        with DB.tx(c):
            alert(c, "info", "prop", f"{len(st)} prop-rule facts are unchecked or older than 30 days; {unver} current facts are not verified",
                  dedup_key=f"prop_stale:{now()[:10]}")
    return {"stale_or_unchecked": len(st), "unverified_current": unver}


def book_series(book: str = "v98") -> pd.Series:
    f = ROOT / ("results/v98_paper_sleeves.parquet" if book == "v98" else f"results/cache_{book}_final.parquet")
    x = pd.read_parquet(f); s = x["port"] if "port" in x else x.iloc[:, 0]
    return s.groupby(s.index.floor("D")).sum().loc["2022-01-01":]


def h_validate_book(c, p):
    from qpl.hub import experiments as EX, validation as V
    s = book_series(p.get("book", "v98"))
    n = int(c.execute("SELECT COALESCE(SUM(trials_added),0) FROM experiments WHERE kind='protocol'").fetchone()[0]) or 1849
    rep = V.evaluate(s, n, p.get("use_case", "prop_challenge"))
    key = f"monitor:validate:{p.get('book', 'v98')}:{now()[:10]}"
    eid = EX.register(c, key, "descriptive", {"book": p.get("book", "v98"), "use_case": p.get("use_case", "prop_challenge"), "n_trials": n},
                      title=f"periodic validation of book {p.get('book', 'v98')}", trials_added=0, source="hub:validate_book")
    try:
        EX.finish(c, eid, rep, rep["verdict"], "; ".join(rep["reasons"])[:2000])
    except ValueError:
        pass
    return {"verdict": rep["verdict"], "sharpe": rep["summary"].get("sharpe"), "selection_adjusted": rep["selection"]["project_haircut_sharpe"], "n_trials": n}


def h_data_integrity(c, p):
    from qpl.hub import ingest
    r = subprocess.run([sys.executable, "scripts/v99/check_v98_freeze.py"], cwd=ROOT, capture_output=True, text=True, timeout=600)
    ok = r.returncode == 0
    if not ok:
        with DB.tx(c):
            alert(c, "critical", "integrity", "v98 freeze guard failed: a file of the live paper baseline changed", {"output": r.stdout[-1000:]}, dedup_key="freeze_broken")
    return {"v98_freeze": "ok" if ok else "BROKEN", "datasets": ingest.datasets(c)}


def h_run_script(c, p):
    path = str(p["script"]).replace("\\", "/")
    if not any(path.startswith(d) for d in ALLOWED_SCRIPT_DIRS) or ".." in path or not path.endswith(".py"):
        raise PermissionError(f"script {path} is not in an allowed research directory {ALLOWED_SCRIPT_DIRS}")
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ("KEY", "SECRET", "TOKEN", "PASSWORD"))}   # no credentials in research jobs
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run([sys.executable, path, *map(str, p.get("args", []))], cwd=ROOT, capture_output=True, text=True, env=env, timeout=int(p.get("timeout_s", 3600)))
    if r.returncode != 0:
        raise RuntimeError(f"exit {r.returncode}: {r.stderr[-2000:]}")
    return {"stdout_tail": r.stdout[-3000:]}


def h_paper_engine(c, p):
    from qpl.hub import paper_engine as PE
    return PE.step_all(c)


def h_agent_step(c, p):
    from qpl.hub import agent
    return agent.step(c)


def h_agent_evaluate(c, p):
    from qpl.hub import agent
    return agent.evaluate(c, p["item_key"])


def h_daily_summary(c, p):
    day = now()[:10]
    s = {"jobs_24h": [dict(r) for r in c.execute("SELECT kind, status, COUNT(*) n FROM jobs WHERE created_at >= datetime(?, '-1 day') GROUP BY kind, status", (now(),))],
         "open_alerts": [dict(r) for r in c.execute("SELECT level, source, message FROM alerts WHERE acknowledged_at IS NULL ORDER BY id DESC LIMIT 20")],
         "experiments_done_24h": c.execute("SELECT COUNT(*) FROM experiments WHERE finished_at >= datetime(?, '-1 day')", (now(),)).fetchone()[0],
         "paper": [dict(r) for r in c.execute("SELECT key, last_data_ts FROM paper_accounts")]}
    out = DB.db_path().parent / f"summary_{day}.json"; out.write_text(json.dumps(s, indent=1, default=str))
    with DB.tx(c):
        alert(c, "info", "summary", f"daily summary {day}: {len(s['open_alerts'])} open alerts, {s['experiments_done_24h']} experiments finished", {"file": str(out)},
              dedup_key=f"summary:{day}")
    return {"file": str(out)}


def h_noop(c, p):
    if p.get("fail"):
        raise RuntimeError("requested failure (test)")
    return {"ok": True, "echo": p}


HANDLERS = {"ingest": h_ingest, "risk": h_risk, "health": h_health, "backup": h_backup, "prop_staleness": h_prop_staleness,
            "validate_book": h_validate_book, "data_integrity": h_data_integrity, "run_script": h_run_script, "agent_step": h_agent_step,
            "agent_evaluate": h_agent_evaluate, "daily_summary": h_daily_summary, "paper_engine": h_paper_engine, "noop": h_noop}
