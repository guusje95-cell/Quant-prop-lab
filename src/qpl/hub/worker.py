"""Background worker: scheduler tick + job execution, independent of any Claude session or open dashboard.

    python -m qpl.hub worker            # runs until stopped (Ctrl+C = graceful: no new jobs, running job finishes or is requeued)
    python -m qpl.hub worker --once     # one scheduler tick + run every due job, then exit (for Windows Task Scheduler)

Each job runs in a child process (`python -m qpl.hub.worker --run-job ID`) so a crash or hang cannot take the worker down; the
parent enforces the job timeout, writes heartbeats, and records CPU seconds against the daily budget."""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import traceback

from qpl.hub import db as DB
from qpl.hub import jobs as J

STOP = False


def _sig(*_):
    global STOP
    STOP = True


def run_job_inline(job_id: int) -> int:
    """Child-process entry: run one claimed job and record its outcome."""
    from qpl.hub.handlers import HANDLERS
    c = DB.init(); r = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    try:
        res = HANDLERS[r["kind"]](c, json.loads(r["payload"] or "{}"))
        J.complete(c, job_id, res if isinstance(res, dict) else {"result": res}); return 0
    except BaseException as e:                                          # noqa: BLE001 - every failure is recorded and retried
        J.fail(c, job_id, f"{type(e).__name__}: {e}\n{traceback.format_exc()[-3000:]}"); return 1


def _cpu_today(c) -> float:
    r = c.execute("SELECT COALESCE(SUM(json_extract(details,'$.cpu_s')),0) FROM audit_log WHERE action='job_cpu' AND ts >= date(?)", (DB.now(),)).fetchone()
    return float(r[0] or 0)


def run(once: bool = False, poll_s: float = 15.0) -> dict:
    signal.signal(signal.SIGINT, _sig); signal.signal(signal.SIGTERM, _sig)
    c = DB.init(); J.ensure_schedules(c); me = f"{socket.gethostname()}:{os.getpid()}"; ran = []
    with DB.tx(c):
        DB.audit(c, "worker", "start", "worker", me, {"once": once})
    try:
        while not STOP:
            J.recover_stale(c); J.tick(c)
            budget = float(DB.get_setting(c, "job_cpu_seconds_budget_per_day", "28800"))
            job = None if _cpu_today(c) > budget else J.claim(c, me)
            if job is None:
                if once:
                    break
                time.sleep(poll_s); continue
            t0 = time.time(); ru0 = os.times()
            p = subprocess.Popen([sys.executable, "-m", "qpl.hub.worker", "--run-job", str(job["id"])], cwd=str(DB.ROOT),
                                 env={**os.environ, "PYTHONPATH": str(DB.ROOT / "src")})
            while p.poll() is None:
                if time.time() - t0 > job["timeout_s"]:
                    p.kill(); p.wait(); J.fail(c, job["id"], f"timeout after {job['timeout_s']} s"); break
                if STOP and time.time() - t0 > 60:
                    p.kill(); p.wait(); J.fail(c, job["id"], "worker shutdown: requeued"); break
                J.heartbeat(c, job["id"]); time.sleep(2)
            ru1 = os.times(); cpu = (ru1.children_user + ru1.children_system) - (ru0.children_user + ru0.children_system)
            with DB.tx(c):
                DB.audit(c, "worker", "job_cpu", "jobs", job["id"], {"cpu_s": round(cpu, 1), "wall_s": round(time.time() - t0, 1)})
            ran.append(job["id"])
    finally:
        with DB.tx(c):
            DB.audit(c, "worker", "stop", "worker", me, {"jobs_run": len(ran)})
    return {"jobs_run": ran}


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--run-job", type=int); ap.add_argument("--once", action="store_true")
    a = ap.parse_args(argv)
    if a.run_job:
        sys.exit(run_job_inline(a.run_job))
    print(run(once=a.once))


if __name__ == "__main__":
    main()
