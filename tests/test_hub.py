"""Quant Trading Hub tests: core persistence, registry rules, experiments, validation numbers on known series, finance states,
risk hysteresis, prop rule versions / compatibility, jobs (dedup, retry, recovery, whitelist), worker end to end, agent gating,
acceptance checks from the hub specification."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture()
def c(tmp_path, monkeypatch):
    monkeypatch.setenv("QPL_HUB_DB", str(tmp_path / "hub.sqlite"))
    from qpl.hub import db
    con = db.init()
    yield con
    con.close()


# ------------------------------------------------------------------------------------------------------------------ core
def test_migrations_idempotent_and_live_trading_locked(c):
    from qpl.hub import db
    assert db.migrate(c) == []                                             # second run applies nothing
    assert db.get_setting(c, "live_trading_enabled") == "false"
    with pytest.raises(PermissionError):
        db.set_setting(c, "live_trading_enabled", "true")
    db.set_setting(c, "backup_keep", "3"); assert db.get_setting(c, "backup_keep") == "3"
    assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='set_setting'").fetchone()[0] == 1


def test_backup_restore_roundtrip(c, tmp_path):
    from qpl.hub import db
    db.alert(c, "info", "t", "before backup")
    b = db.backup(c, tmp_path / "bk")
    assert b["restorable"] and b["integrity"] == "ok"
    db.alert(c, "info", "t", "after backup")
    target = tmp_path / "restored.sqlite"; db.restore(Path(b["path"]), target)
    r = sqlite3.connect(target).execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    assert r == 1                                                          # the restored copy has the state at backup time


# ------------------------------------------------------------------------------------------------------------------ registry
def test_versions_are_immutable_and_idempotent(c):
    from qpl.hub import registry as RG
    RG.upsert_strategy(c, "s1", "S1", "crypto_futures")
    v1 = RG.add_version(c, "s1", "1.0", "scripts/x.py", {"a": 1})
    assert RG.add_version(c, "s1", "1.0", "scripts/x.py", {"a": 1}) == v1             # same config -> same version
    with pytest.raises(ValueError):
        RG.add_version(c, "s1", "1.0", "scripts/x.py", {"a": 2})                       # label reused with another config
    v2 = RG.add_version(c, "s1", "1.1", "scripts/x.py", {"a": 2}); assert v2 != v1
    with pytest.raises(sqlite3.DatabaseError):
        c.execute("UPDATE strategy_versions SET params='{\"a\": 3}' WHERE id=?", (v1,))   # database-level immutability


def test_lifecycle_rules(c):
    from qpl.hub import registry as RG
    RG.upsert_strategy(c, "s2", "S2", "crypto_futures"); v = RG.add_version(c, "s2", "1", "x", {}, state="idea")
    with pytest.raises(ValueError):
        RG.transition(c, v, "approved", "skip", use_scope="paper")                    # idea -> approved not allowed
    RG.transition(c, v, "research", "start"); RG.transition(c, v, "backtesting", "code ready"); RG.transition(c, v, "validation", "bt done")
    RG.transition(c, v, "candidate", "passed");
    with pytest.raises(ValueError):
        RG.transition(c, v, "approved", "ok")                                          # approval needs a scope
    RG.transition(c, v, "approved", "paper evidence", use_scope="paper")
    ev = c.execute("SELECT to_state, use_scope FROM lifecycle_events WHERE version_id=? ORDER BY id", (v,)).fetchall()
    assert [e["to_state"] for e in ev] == ["idea", "research", "backtesting", "validation", "candidate", "approved"] and ev[-1]["use_scope"] == "paper"


def test_experiment_result_is_final_and_holdout_flag(c):
    from qpl.hub import experiments as EX
    e = EX.register(c, "e1", "protocol", {"x": 1}, periods={"holdout": ["2025-01-01", "2026-09-30"]}, trials_added=3)
    assert c.execute("SELECT uses_holdout FROM experiments WHERE id=?", (e,)).fetchone()[0] == 1
    EX.finish(c, e, {"sharpe": 1.0}, "pass", "ok")
    with pytest.raises(ValueError):
        EX.finish(c, e, {"sharpe": 2.0}, "pass", "rerun")                               # never overwritten
    assert EX.trial_count(c) == 3
    e2 = EX.register(c, "e1", "protocol", {"x": 9}); assert e2 == e                    # same key -> same experiment


# ------------------------------------------------------------------------------------------------------------------ metrics / validation
def test_metrics_known_values():
    from qpl.hub.metrics import summary
    idx = pd.date_range("2022-01-01", periods=4, freq="D")
    s = summary(pd.Series([0.10, -0.10, 0.10, -0.10], index=idx))
    assert abs(s["total_return"] - (1.1 * 0.9 * 1.1 * 0.9 - 1)) < 1e-12
    assert abs(s["max_drawdown"] - (1.1 * 0.9 * 1.1 * 0.9 / 1.1 - 1)) < 1e-12           # peak 1.1 -> 0.9801
    assert s["sharpe"] == 0.0


def test_expected_max_matches_project_numbers():
    from qpl.hub.validation import emax_null
    assert abs(emax_null(1849, 1734) * np.sqrt(365) - 1.572) < 0.01                   # research/v99/METHODOLOGY_AUDIT.md
    assert emax_null(1, 100) == 0.0


def test_validation_verdicts():
    from qpl.hub import validation as V
    rng = np.random.default_rng(0); idx = pd.date_range("2022-01-01", "2026-09-30", freq="D")
    good = pd.Series(rng.normal(0.003, 0.01, len(idx)), index=idx)                     # Sharpe about 5.7
    noise = pd.Series(rng.normal(0.0, 0.01, len(idx)), index=idx)
    assert V.evaluate(good, 100, "paper_trading")["verdict"] == "pass"
    assert V.evaluate(noise, 100, "prop_challenge")["verdict"] == "fail"
    assert V.evaluate(good.iloc[:100], 100, "paper_trading")["verdict"] == "insufficient evidence"
    fam = pd.DataFrame({f"v{i}": rng.normal(0, 0.01, len(idx)) for i in range(20)}, index=idx)
    p = V.pbo_cscv(fam, max_splits=300); assert p["pbo"] > 0.4                           # pure noise family: the in-sample winner is no better out of sample


# ------------------------------------------------------------------------------------------------------------------ finance / income
def test_finance_states_and_cash(c):
    from qpl.hub import finance as F
    fee = F.add(c, "challenge_fee", 970, "USD", "paid", firm="hyrotrader")
    p = F.add(c, "payout", 5000, "USD", "requested", firm="hyrotrader", external_ref="hyro-1")
    assert F.add(c, "payout", 5000, "USD", "requested", firm="hyrotrader", external_ref="hyro-1") == p   # no duplicate record
    r = F.report(c); assert r["totals"]["received"] == 0 and r["pending_payouts"]["requested"] == 5000   # requested is not cash
    F.set_status(c, p, "approved"); F.set_status(c, p, "received")
    r = F.report(c); assert r["totals"]["received"] == 5000 and r["totals"]["net_cash"] == 5000 - 970
    with pytest.raises(ValueError):
        F.set_status(c, p, "requested")                                                  # received is final
    assert len(c.execute("SELECT * FROM finance_tx_history WHERE tx_id=?", (p,)).fetchall()) == 3
    assert F.report(c, {})["missing_fx_rates"] == []
    F.add(c, "subscription", 20, "EUR", "paid"); assert "EUR" in F.report(c)["missing_fx_rates"]    # never guesses FX


# ------------------------------------------------------------------------------------------------------------------ risk
def _paper(c, key, rets, start="2026-10-01"):
    with c:
        pass
    from qpl.hub.db import now, tx
    with tx(c):
        aid = c.execute("INSERT INTO paper_accounts (key, source_dir, initial_capital, status, created_at) VALUES (?,?,?,?,?)",
                        (key, "x", 100000, "running", now())).lastrowid
        eq = 100000 * np.cumprod(1 + np.array(rets)); ts = pd.date_range(start, periods=len(rets), freq="h")
        c.executemany("INSERT INTO paper_equity (account_id, ts, ret, equity, late) VALUES (?,?,?,?,?)", [(aid, str(t), float(r), float(e), 0) for t, r, e in zip(ts, rets, eq)])
    return aid


def test_risk_hysteresis_and_no_duplicate_events(c, tmp_path):
    from qpl.hub import risk
    _paper(c, "paper:t1", [0.0] * 5 + [-0.05, -0.05, -0.04])                           # about -13% from peak
    ev = risk.evaluate(c, "paper:t1", bot_dir=tmp_path / "bot", active_only=False)
    rules = {(e["rule"], e["action"]) for e in ev}
    assert ("drawdown_from_peak", "stop") in rules and ("drawdown_from_peak", "warning") in rules
    assert risk.evaluate(c, "paper:t1", bot_dir=tmp_path / "bot", active_only=False) == []          # still active: no repeated events
    assert not (tmp_path / "bot" / "STOP").exists()                                     # kill switch only for the v98 account


def test_portfolio_risk_contributions_sum_to_one():
    from qpl.hub.risk import portfolio_risk
    rng = np.random.default_rng(1); X = pd.DataFrame(rng.normal(0.001, 0.01, (500, 3)), columns=list("abc"))
    r = portfolio_risk(X, pd.Series({"a": 0.5, "b": 0.3, "c": 0.2}))
    assert abs(sum(r["risk_contribution"].values()) - 1) < 1e-6 and len(r["stress"]) >= 3


# ------------------------------------------------------------------------------------------------------------------ prop
def test_prop_rule_versions_and_compatibility(c):
    from qpl.hub import prop
    p1 = {"account": 200000, "daily_loss": 0.05, "max_loss": 0.10, "targets": [0.10, 0.05], "fee": 970}
    facts = [{"field": "bots_allowed", "value": True, "status": "verified", "source_url": "https://example.test/rules", "checked_at": "2026-10-30", "quote": "bots allowed"},
             {"field": "overnight_holding", "value": True, "status": "uncertain", "source_url": None, "checked_at": None}]
    r1 = prop.add_rule_set(c, "hyrotrader", "T", p1, facts, "2026-10-30")
    assert prop.add_rule_set(c, "hyrotrader", "T", p1, [], "2026-10-30") == r1          # identical rules -> same version
    r2 = prop.add_rule_set(c, "hyrotrader", "T", {**p1, "daily_loss": 0.04}, [], "2026-11-01")
    v = c.execute("SELECT id, version, superseded_at FROM prop_rule_sets ORDER BY id").fetchall()
    assert [x["version"] for x in v] == [1, 2] and v[0]["superseded_at"] is not None     # history kept
    comp = prop.compatibility(c, r1)
    assert comp["status"] in ("potentially_compatible", "insufficient_evidence")        # unverified facts never give 'verified compatible'
    prop.add_rule_set(c, "topstep", "Combine", {"account": 50000}, [{"field": "overnight_holding", "value": False, "status": "verified",
                      "source_url": "https://example.test/topstep", "checked_at": "2026-10-30"}], "2026-10-30")
    rid = c.execute("SELECT s.id FROM prop_rule_sets s JOIN prop_firms f ON f.id=s.firm_id WHERE f.key='topstep'").fetchone()[0]
    assert prop.compatibility(c, rid)["status"] == "incompatible"                        # crypto book vs futures firm


def test_futures_profile_uses_firm_policy_facts(c):
    from qpl.hub import prop
    combine = prop.add_rule_set(c, "mffu", "Combine 50k", {"account": 50000}, [], "2026-10-30")
    assert prop.compatibility(c, combine, prop.FUTURES_PROFILE, store=False)["status"] == "potentially_compatible"   # nothing known yet
    prop.add_rule_set(c, "mffu", "futures swing policy (project notes)", {"source": "test"},
                      [{"field": "overnight_holding", "value": False, "status": "verified", "source_url": "https://example.test/mffu",
                        "quote": "positions are closed at 16:10 ET", "checked_at": "2026-10-30"}], "2026-10-30")
    assert prop.compatibility(c, combine, prop.FUTURES_PROFILE, store=False)["status"] == "incompatible"       # firm-wide policy applies
    assert prop.compatibility(c, combine, prop.V98_PROFILE, store=False)["status"] == "incompatible"           # crypto book: wrong market


def test_nominal_account_is_not_loss_capacity():
    from qpl.lab import propfirms as PF
    f = PF.PRESETS["HyroTrader Two-Step $200k"]
    assert f.account * f.max_loss < 0.2 * f.account                                     # loss capacity is a fraction of the nominal size


# ------------------------------------------------------------------------------------------------------------------ jobs / worker / agent
def test_jobs_dedup_retry_recovery_whitelist(c):
    from qpl.hub import jobs as J
    a = J.enqueue(c, "noop", {"x": 1}, dedup_key="k"); assert J.enqueue(c, "noop", {"x": 2}, dedup_key="k") == a
    with pytest.raises(ValueError):
        J.enqueue(c, "rm_rf", {})
    j = J.claim(c, "w"); assert j["id"] == a and j["attempts"] == 1
    J.fail(c, a, "boom"); r = c.execute("SELECT status, next_run_at FROM jobs WHERE id=?", (a,)).fetchone()
    assert r["status"] == "queued" and r["next_run_at"] > j["started_at"]                # backoff
    c.execute("UPDATE jobs SET next_run_at='2000-01-01', status='running', heartbeat_at='2000-01-01', attempts=1 WHERE id=?", (a,))
    assert J.recover_stale(c) == [a]                                                   # dead worker -> retried
    with pytest.raises(PermissionError):
        from qpl.hub.handlers import h_run_script
        h_run_script(c, {"script": "scripts/paper_v5.py"})                              # only research directories


def test_worker_runs_jobs_end_to_end(tmp_path):
    env = {**os.environ, "QPL_HUB_DB": str(tmp_path / "w.sqlite"), "PYTHONPATH": str(ROOT / "src")}
    code = ("from qpl.hub import db, jobs; c=db.init(); c.execute('DELETE FROM schedules') if 0 else None; "
            "jobs.enqueue(c,'noop',{'a':1}); jobs.enqueue(c,'noop',{'fail':True},max_attempts=1)")
    subprocess.run([sys.executable, "-c", code], env=env, check=True, cwd=ROOT)
    con = sqlite3.connect(tmp_path / "w.sqlite"); con.execute("UPDATE schedules SET enabled=0") if con.execute("SELECT name FROM sqlite_master WHERE name='schedules'").fetchone() else None; con.commit()
    subprocess.run([sys.executable, "-c", "from qpl.hub import db,jobs; c=db.init(); jobs.ensure_schedules(c); c.execute('UPDATE schedules SET enabled=0')"], env=env, check=True, cwd=ROOT)
    subprocess.run([sys.executable, "-m", "qpl.hub", "worker", "--once"], env=env, check=True, cwd=ROOT, timeout=300)
    st = dict(con.execute("SELECT json_extract(payload,'$.fail') IS NOT NULL, status FROM jobs").fetchall())
    assert st[0] == "done" and st[1] == "failed"
    assert con.execute("SELECT COUNT(*) FROM alerts WHERE source='jobs'").fetchone()[0] == 1   # failure is observable


def test_agent_runs_only_approved_items(c):
    from qpl.hub import agent
    ag = {"items": [{"key": "x", "title": "t", "status": "proposed", "hypothesis": "h", "script": "scripts/hub_research/event_regime_scaling.py",
                     "result_file": "r.json", "decision_rule": {"values": {}, "pass_if": "True"}, "needs_data": []}]}
    assert agent.step(c, ag)["started"] == []
    assert agent.readiness({**ag["items"][0], "status": "approved", "script": "scripts/paper_v5.py"})[0] is False   # outside research dirs


def test_income_never_counts_sharpe_as_income():
    from qpl.hub import income
    idx = pd.date_range("2022-01-01", "2026-09-30 23:00", freq="h"); rng = np.random.default_rng(3)
    h = pd.Series(rng.normal(0, 0.15 / np.sqrt(365 * 24), len(idx)), index=idx)
    r = income.simulate(h, income.SCENARIOS["conservative"], n_paths=40, horizon_days=360)
    assert r["P_net_loss_over_horizon"] >= 0 and "caveat" in r and r["target_month_eur"] == 10000
    r0 = income.simulate(h, {**income.SCENARIOS["base"], "live_sharpe": 0.0}, n_paths=40, horizon_days=360)
    r2 = income.simulate(h, {**income.SCENARIOS["base"], "live_sharpe": 3.0}, n_paths=40, horizon_days=360)
    assert r2["monthly_net_cash_eur_before_tax"]["mean"] > r0["monthly_net_cash_eur_before_tax"]["mean"]


def test_verified_fact_needs_source_and_quote(c):
    from qpl.hub import prop
    r = prop.add_rule_set(c, "hyrotrader", "T2", {"account": 100000}, [], "2026-10-30")
    with pytest.raises(ValueError):
        prop.record_fact(c, r, "bots_allowed", True, "verified", None, None)
    with pytest.raises(ValueError):
        prop.record_fact(c, r, "bots_allowed", True, "verified", "https://x.test", "")
    prop.record_fact(c, r, "bots_allowed", True, "verified", "https://x.test/rules", "Trading bots connected via API are permitted.")
    assert prop.facts(c, r)["bots_allowed"]["status"] == "verified"


def test_dashboard_renders_every_page_on_an_empty_database(tmp_path, monkeypatch):
    monkeypatch.setenv("QPL_HUB_DB", str(tmp_path / "empty.sqlite"))
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app/hub.py"), default_timeout=300); at.run()
    for p in ["Overview", "Paper Trading", "Research Lab", "Strategy Center", "Portfolio & Risk", "Prop Firm Center", "Income Planner", "Finance", "System Health"]:
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, (p, [e.value for e in at.exception][:1])


def test_agent_decision_rule_with_period_checks(c, tmp_path, monkeypatch):
    from qpl.hub import agent, experiments as EX, jobs as J
    res = tmp_path / "res.json"; res.write_text(json.dumps({"candidate": [3.3, [3.1, 3.9, 2.8]], "reference_v98": [3.2, [3.0, 3.9, 2.7]]}))
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    it = {"key": "k", "title": "t", "status": "approved", "hypothesis": "h", "script": "scripts/hub_research/x.py", "result_file": "res.json",
          "decision_rule": {"values": {"book": "candidate.0", "ref": "reference_v98.0", "p": "candidate.1", "pr": "reference_v98.1"},
                            "pass_if": "book >= ref + 0.05 and all(p[i] >= pr[i] for i in range(3))"}}
    EX.register(c, "agent:k", "agent", {}, status="running")
    J.enqueue(c, "noop", {}, dedup_key="agent_run:k"); j = J.claim(c, "w"); J.complete(c, j["id"], {})
    assert agent.evaluate(c, "k", {"items": [it]})["decision"] == "pass"


def test_shadow_accounts_derive_exactly_from_the_source(c):
    from qpl.hub import ingest, shadow
    ingest.paper_accounts(c)
    shadow.define(c, "t:same", "paper:v86", "reweighted", {"multipliers": {}}, risk=2.0)
    shadow.define(c, "t:cstar", "paper:v86", "sleeve", {"sleeve": "C*", "vol_target": 0.15})
    shadow.define(c, "t:noridge", "paper:v86", "reweighted", {"multipliers": {"ridge ML": 0.0}}, risk=2.0)
    r = shadow.recompute(c)
    assert r["shadow:t:same"]["hours"] == 46 and r["shadow:t:same"]["forward_hours"] == 0          # defined after the run: all retroactive
    src = pd.read_sql_query("SELECT ts, ret FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key='paper:v86' ORDER BY ts", c)
    sh = pd.read_sql_query("SELECT ts, ret, retro FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key='shadow:t:same' ORDER BY ts", c)
    assert np.abs(src["ret"].to_numpy() - sh["ret"].to_numpy()).max() < 1e-15 and sh["retro"].all()  # neutral shadow == the paper book
    nr = pd.read_sql_query("SELECT ret FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key='shadow:t:noridge' ORDER BY ts", c)["ret"]
    assert not np.allclose(nr.to_numpy(), src["ret"].to_numpy())
    with pytest.raises(ValueError):
        shadow.define(c, "t:same", "paper:v86", "reweighted", {"multipliers": {"C*": 2}})          # immutable definition
    assert shadow.define(c, "t:waiting", "paper:not_started_yet", "sleeve", {"sleeve": "C*"})      # a source without any ledger yet
    assert "waiting" in shadow.recompute(c, "shadow:t:waiting")["shadow:t:waiting"]["status"]


def _hist_provider():
    from qpl.hub import paper_engine as PE
    from qpl.lab import data as LD
    idx = pd.date_range("2024-01-01", "2024-06-30 23:00", freq="h"); rng = np.random.default_rng(4)
    cl = pd.DataFrame({s: 100 * np.exp(np.cumsum(rng.normal(0.0001, 0.006, len(idx)))) for s in ("AAA", "BBB")}, index=idx)
    b = LD.Bars("synthetic", "1h", cl, cl * 1.002, cl * 0.998, cl, cl * 0 + 1.0, LD.PPY["1h"])
    return PE.HistoricalProvider(b, {"AAA": pd.Series(0.0001, index=pd.date_range("2024-01-01", "2024-07-01", freq="8h"))})


def test_paper_engine_matches_backtest_and_is_idempotent(c):
    from qpl.hub import paper_engine as PE
    prov = _hist_provider()
    cfg = {"kind": "strategy", "strategy": "Time-series momentum", "params": {}, "symbols": ["AAA", "BBB"], "freq": "4h",
           "sizing": {"cost_bps": 7.5, "min_history_days": 10}, "lookback_days": 400}
    PE.create_account(c, "par", cfg)
    t0 = pd.Timestamp("2024-05-01")
    PE.step(c, "engine:par", prov, end=t0, replay_from=str(t0 - pd.Timedelta(hours=4)))
    for k in range(1, 61):
        PE.step(c, "engine:par", prov, end=t0 + pd.Timedelta(hours=4 * k))
    n1 = c.execute("SELECT COUNT(*) FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key='engine:par'").fetchone()[0]
    assert PE.step(c, "engine:par", prov, end=t0 + pd.Timedelta(hours=240))["processed"] == 0          # same time again: nothing double-counted
    assert c.execute("SELECT COUNT(*) FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key='engine:par'").fetchone()[0] == n1
    E = pd.read_sql_query("SELECT ts, ret FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key='engine:par' ORDER BY ts", c)
    E = E.set_index(pd.to_datetime(E["ts"]))["ret"]
    funding_cfg = dict(cfg)
    bt = PE.backtest_same_config(funding_cfg, prov, str(E.index[0]), str(E.index[-1]))
    held_aaa = pd.read_sql_query("SELECT ts, weight FROM paper_positions p JOIN paper_accounts a ON a.id=p.account_id WHERE a.key='engine:par' AND coin='AAA'", c)
    diff = (E - bt.reindex(E.index)).iloc[2:]
    assert diff.abs().max() < 0.002                                          # differences only from the funding the backtest omits
    assert not held_aaa.empty


def test_paper_engine_controls_portfolio_and_fail_closed(c):
    from qpl.hub import paper_engine as PE
    prov = _hist_provider()
    a = {"kind": "strategy", "strategy": "Time-series momentum", "symbols": ["AAA", "BBB"], "freq": "4h", "sizing": {"min_history_days": 10}}
    b = {"kind": "strategy", "strategy": "Buy & hold (benchmark)", "symbols": ["AAA", "BBB"], "freq": "4h", "sizing": {"min_history_days": 10}}
    PE.create_account(c, "pf", {"kind": "portfolio", "freq": "4h", "cost_bps": 7.5, "gross_cap": 3.0, "members": [dict(a, weight=0.5), dict(b, weight=0.5)]})
    end = pd.Timestamp("2024-05-10")
    assert PE.step(c, "engine:pf", prov, end=end)["status"] == "ok"
    PE.set_status(c, "engine:pf", "paused", "test")
    assert PE.step(c, "engine:pf", prov, end=end + pd.Timedelta(hours=8))["processed"] == 0
    PE.set_status(c, "engine:pf", "running", "test")
    late = PE.step(c, "engine:pf", prov, end=pd.Timestamp("2024-08-01"))                               # provider has no data after 2024-06-30
    assert late["status"] == "stale data" and c.execute("SELECT COUNT(*) FROM alerts WHERE source='paper:engine:pf'").fetchone()[0] == 1
    new = PE.reset(c, "engine:pf", "pf2", "test reset")
    assert c.execute("SELECT status FROM paper_accounts WHERE key='engine:pf'").fetchone()[0] == "archived" and new
    with pytest.raises(ValueError):
        PE.create_account(c, "pf2", a)                                          # keys are never reused
    with pytest.raises(KeyError):
        PE.create_account(c, "bad", dict(a, strategy="no such strategy"))


def test_composite_shadow_adds_a_sleeve_with_the_book_rule(c, tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import crypto_sleeves as CS
    from qpl.hub import shadow
    from qpl.hub.db import now, tx
    rng = np.random.default_rng(7); idx = pd.date_range("2024-01-01", "2026-03-31 23:00", freq="h"); paper_from = pd.Timestamp("2026-01-01")
    H = pd.DataFrame({s: rng.normal(0.00003, 0.002, len(idx)) for s in ("A", "B", "Weiss expiry")}, index=idx)
    pre = tmp_path / "pre.parquet"; H[H.index < paper_from].to_parquet(pre)
    P = H[H.index >= paper_from]; new = pd.Series(rng.normal(0.00005, 0.002, len(P)), index=P.index)
    with tx(c):
        src = c.execute("INSERT INTO paper_accounts (key, source_dir, initial_capital, status, created_at) VALUES ('paper:tt','x',1,'running',?)", (now(),)).lastrowid
        c.executemany("INSERT INTO paper_sleeve_pnl VALUES (?,?,?,?,?)", [(src, str(t), s, float(v), 0.0) for s in P.columns for t, v in P[s].items()])
        ex = c.execute("INSERT INTO paper_accounts (key, source_dir, initial_capital, status, created_at) VALUES ('engine:new','x',1,'running',?)", (now(),)).lastrowid
        c.executemany("INSERT INTO paper_equity (account_id, ts, ret, equity) VALUES (?,?,?,?)", [(ex, str(t), float(v), 1.0) for t, v in new.items()])
    rel = str(pre.relative_to(tmp_path)); monkeypatch.setattr(shadow, "ROOT", tmp_path)
    shadow.define(c, "tt:same", "paper:tt", "composite", {"prefix": rel, "scale": 1.0}, risk=1.0)
    shadow.define(c, "tt:plus", "paper:tt", "composite", {"prefix": rel, "scale": 1.0, "extra": [{"name": "new", "account": "engine:new"}]}, risk=1.0)
    same = shadow.returns(c, "shadow:tt:same"); plus = shadow.returns(c, "shadow:tt:plus")
    ref = CS.portfolio_v5(H, start="2024-01-01")[0].reindex(P.index)
    assert np.abs(same.to_numpy() - ref.to_numpy()).max() < 1e-12                         # the book rule, reproduced
    Hp = pd.concat([H, new.rename("new").reindex(H.index).fillna(0.0)], axis=1)
    refp = CS.portfolio_v5(Hp, start="2024-01-01")[0].reindex(P.index)
    assert np.abs(plus.to_numpy() - refp.to_numpy()).max() < 1e-12 and not np.allclose(plus, same)   # 4th sleeve enters via the same rule
    with pytest.raises(ValueError):
        shadow.define(c, "tt:bad", "paper:tt", "composite", {"extra": [{"name": "x", "account": "engine:missing"}]})
