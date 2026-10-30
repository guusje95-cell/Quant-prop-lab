"""Autonomous research agent (rule-based; works without any LLM).

The agenda (research/hub/agenda.json) lists hypotheses, each with: an economic rationale, the data it needs (paths that must
exist), a whitelisted script that writes a result JSON, a pre-registered decision rule, and priority inputs. One `step()`:
  1. refreshes readiness (data present?) and skips items already decided or whose protocol changed after registration;
  2. scores ready items: economic relevance x information gain x diversification / (1 + cost hours), x0.2 if a similar test exists;
  3. registers the hypothesis and the experiment (config hash incl. the protocol file's hash) BEFORE running;
  4. enqueues `run_script` and then `agent_evaluate`, which applies the decision rule to the result file and closes the experiment.
Limits: settings `agent_max_experiments_per_day` (default 2) and `research_max_trials_per_task`.
LLM: `LLMProvider` is an interface; the default `NoLLM` proposes nothing. Proposals from any provider are written to the agenda as
status 'proposed' and NEVER run until a human sets them to 'approved' (generated code is never executed automatically)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from qpl.hub import experiments as EX
from qpl.hub import jobs as J
from qpl.hub.db import ROOT, audit, get_setting, jhash, now, tx

AGENDA = ROOT / "research/hub/agenda.json"


class LLMProvider:
    name = "none"

    def propose(self, context: dict) -> list[dict]:
        return []


class NoLLM(LLMProvider):
    name = "disabled (no provider configured)"


def load_agenda(path: Path = AGENDA) -> dict:
    return json.loads(path.read_text())


def score(item: dict) -> float:
    p = item.get("priority", {})
    s = p.get("economic_relevance", 3) * p.get("information_gain", 3) * p.get("diversification", 3) / (1 + p.get("cost_hours", 1))
    return round(s * (0.2 if p.get("similar_test_exists") else 1.0), 3)


def readiness(item: dict) -> tuple[bool, list[str]]:
    missing = [d for d in item.get("needs_data", []) if not (ROOT / d).exists()]
    if item.get("status") not in ("approved",):
        return False, [f"status is {item.get('status')} (only 'approved' items run)"]
    if not str(item.get("script", "")).startswith(("scripts/v99/", "scripts/hub_research/")):
        return False, ["script outside the allowed research directories"]
    if not (ROOT / item.get("script", "")).exists():
        missing.append(item.get("script"))
    return (not missing), missing


def plan(c: sqlite3.Connection, agenda: dict | None = None) -> list[dict]:
    agenda = agenda or load_agenda(); out = []
    for it in agenda["items"]:
        ok, why = readiness(it)
        e = c.execute("SELECT status, decision FROM experiments WHERE key=?", (f"agent:{it['key']}",)).fetchone()
        out.append({"key": it["key"], "title": it["title"], "score": score(it), "ready": ok, "blocked_by": why,
                    "experiment": dict(e) if e else None, "needs_user": it.get("needs_user")})
    return sorted(out, key=lambda x: (-int(x["ready"] and not x["experiment"]), -x["score"]))


def step(c: sqlite3.Connection, agenda: dict | None = None, provider: LLMProvider | None = None) -> dict:
    agenda = agenda or load_agenda(); provider = provider or NoLLM()
    limit = int(get_setting(c, "agent_max_experiments_per_day", "2"))
    today = c.execute("SELECT COUNT(*) FROM experiments WHERE source='hub:agent' AND registered_at >= date(?)", (now(),)).fetchone()[0]
    proposals = provider.propose({"agenda": [i["key"] for i in agenda["items"]]})
    started = []
    for it in sorted(agenda["items"], key=lambda x: -score(x)):
        if today + len(started) >= limit:
            break
        ok, _ = readiness(it)
        if not ok or c.execute("SELECT 1 FROM experiments WHERE key=?", (f"agent:{it['key']}",)).fetchone():
            continue
        if it.get("trials", 1) > int(get_setting(c, "research_max_trials_per_task", "12")):
            continue
        proto = ROOT / it["protocol"] if it.get("protocol") else None
        cfg = {"script": it["script"], "args": it.get("args", []), "result_file": it["result_file"], "decision_rule": it["decision_rule"],
               "protocol": it.get("protocol"), "protocol_sha": jhash(proto.read_text()) if proto and proto.exists() else None}
        EX.add_hypothesis(c, f"agent:{it['key']}", it["hypothesis"], it.get("rationale"), it.get("market"), it.get("family"), source="research/hub/agenda.json")
        eid = EX.register(c, f"agent:{it['key']}", "agent", cfg, title=it["title"], hypothesis_key=f"agent:{it['key']}", periods=it.get("periods"),
                          cost_model=it.get("cost_model"), trials_added=it.get("trials", 1), source="hub:agent", status="queued")
        j1 = J.enqueue(c, "run_script", {"script": it["script"], "args": it.get("args", []), "timeout_s": it.get("timeout_s", 7200)},
                       dedup_key=f"agent_run:{it['key']}", priority=7, timeout_s=it.get("timeout_s", 7200) + 300, max_attempts=2)
        J.enqueue(c, "agent_evaluate", {"item_key": it["key"]}, dedup_key=f"agent_eval:{it['key']}", priority=8, delay_minutes=5, max_attempts=48)
        with tx(c):
            c.execute("UPDATE experiments SET status='running', started_at=? WHERE id=?", (now(), eid))
            audit(c, "agent", "start_experiment", "experiments", eid, {"item": it["key"], "job": j1, "score": score(it)})
        started.append(it["key"])
    return {"started": started, "llm": provider.name, "proposals": len(proposals), "plan": plan(c, agenda)[:8]}


def _get(d, path):
    for k in path.split("."):
        d = d[int(k)] if isinstance(d, list) else d[k]
    return d


def evaluate(c: sqlite3.Connection, item_key: str, agenda: dict | None = None) -> dict:
    """Apply the pre-registered decision rule once the run job is done. Raises (so the job retries later) while the run is pending."""
    agenda = agenda or load_agenda(); it = next(i for i in agenda["items"] if i["key"] == item_key)
    e = c.execute("SELECT * FROM experiments WHERE key=?", (f"agent:{item_key}",)).fetchone()
    run = c.execute("SELECT status, error FROM jobs WHERE dedup_key=? ORDER BY id DESC LIMIT 1", (f"agent_run:{item_key}",)).fetchone()
    if run is None or run["status"] in ("queued", "running", "paused"):
        raise RuntimeError("run job not finished yet")
    if run["status"] != "done":
        EX.finish(c, e["id"], {}, "error", f"run failed: {(run['error'] or '')[-500:]}", failed=True); return {"decision": "error"}
    res = json.loads((ROOT / it["result_file"]).read_text()); rule = it["decision_rule"]
    vals = {k: _get(res, p) for k, p in rule["values"].items()}
    passed = bool(eval(rule["pass_if"], {"__builtins__": {}}, {**vals, "all": all, "any": any, "min": min, "max": max}))   # rule text is from the reviewed agenda file, not generated
    EX.finish(c, e["id"], {"values": vals, "result_file": it["result_file"]}, "pass" if passed else "fail", rule["pass_if"], {"result_file": it["result_file"]})
    with tx(c):
        c.execute("UPDATE hypotheses SET status='closed', verdict=? WHERE key=?", ("supported" if passed else "not supported", f"agent:{item_key}"))
    return {"decision": "pass" if passed else "fail", "values": vals}
