"""Quant Trading Hub dashboard (local web app; reads and writes the hub database only).

    streamlit run app/hub.py          (Windows: hub_dashboard.bat)

Every number comes from the hub database or from a computation started here; each view says whether it is a BACKTEST, PAPER,
MODEL ESTIMATE or ACTUAL figure. Live trading is not available. The background worker (hub_start.bat) does not need this page."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from qpl.hub import db as DB  # noqa: E402

st.set_page_config(page_title="Quant Trading Hub", layout="wide", page_icon="📈")
TPL = "plotly_dark"
st.markdown("""<style>
.block-container {padding-top: 1.2rem;}
div[data-testid="stMetricValue"] {font-size: 1.35rem;}
.tag {display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;margin-right:6px}
.bt {background:#1f3b5b;color:#9cc9ff} .pp {background:#1f4b33;color:#9ff0bf} .me {background:#4b3b1f;color:#ffd99c} .ac {background:#4b1f3b;color:#ffb0e0}
</style>""", unsafe_allow_html=True)
TAG = {"backtest": '<span class="tag bt">BACKTEST</span>', "paper": '<span class="tag pp">PAPER</span>', "model": '<span class="tag me">MODEL ESTIMATE</span>',
       "actual": '<span class="tag ac">ACTUAL</span>'}


def tag(*k):
    st.markdown(" ".join(TAG[x] for x in k), unsafe_allow_html=True)


@st.cache_resource
def con():
    return DB.init()


def q(sql, params=()):
    return pd.read_sql_query(sql, con(), params=params)


def js(x):
    try:
        return json.loads(x) if isinstance(x, str) else x
    except Exception:
        return x


c = con()
st.sidebar.title("Quant Trading Hub")
page = st.sidebar.radio("View", ["Overview", "Research Lab", "Strategy Center", "Portfolio & Risk", "Prop Firm Center", "Income Planner", "Finance", "System Health"])
st.sidebar.caption(f"Database: `{DB.db_path()}`")
st.sidebar.caption("Live trading: **disabled** (no live adapter exists)" if DB.get_setting(c, "live_trading_enabled") == "false" else "check settings")
if st.sidebar.button("Refresh data"):
    st.cache_data.clear(); st.rerun()


# ============================================================================================================ Overview
def overview():
    st.header("Overview")
    j = q("SELECT status, COUNT(*) n FROM jobs GROUP BY status").set_index("status")["n"].to_dict()
    al = q("SELECT * FROM alerts WHERE acknowledged_at IS NULL ORDER BY id DESC")
    bk = q("SELECT ts, verify_result FROM backups ORDER BY id DESC LIMIT 1")
    hb = q("SELECT ts FROM audit_log WHERE actor='worker' ORDER BY id DESC LIMIT 1")
    k = st.columns(6)
    k[0].metric("Paper accounts", len(q("SELECT id FROM paper_accounts")))
    k[1].metric("Open alerts", len(al), help="unacknowledged")
    k[2].metric("Jobs queued / failed", f"{j.get('queued', 0)} / {j.get('failed', 0)}")
    k[3].metric("Experiments recorded", int(q("SELECT COUNT(*) n FROM experiments")["n"][0]))
    k[4].metric("Last worker activity", hb["ts"][0][5:16] if len(hb) else "never")
    k[5].metric("Last backup", bk["ts"][0][5:16] if len(bk) else "never", help=(js(bk["verify_result"][0]) or {}).get("integrity") if len(bk) else None)
    a, b = st.columns([3, 2])
    with a:
        st.subheader("Book v9.8 (frozen paper baseline)")
        tag("backtest")
        f = ROOT / "results/v98_paper_sleeves.parquet"
        if f.exists():
            p = pd.read_parquet(f)["port"].loc["2022":]; d = p.groupby(p.index.floor("D")).sum(); eq = (1 + d).cumprod()
            fig = px.line(eq, template=TPL, labels={"value": "growth of 1 (unit risk, 15% vol)", "index": ""}); fig.update_layout(height=280, showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig, width="stretch")
            v = q("SELECT metrics FROM experiments WHERE key LIKE 'monitor:validate:v98:%' ORDER BY id DESC LIMIT 1")
            if len(v):
                m = js(v["metrics"][0]); s = m["selection"]
                st.caption(f"Backtest Sharpe {s['sharpe']:.2f} · selection-adjusted (N = {s['n_trials']}) {s['project_haircut_sharpe']:.2f} · Harvey-Liu BHY {s['harvey_liu_bhy']:.2f} · "
                           f"DSR {s['dsr']:.4f} · verdict for prop challenges: **{m['verdict']}**. None of these is a live forecast (see METHODOLOGY_AUDIT).")
        st.subheader("Recent experiments")
        st.dataframe(q("SELECT key, kind, title, status, decision, registered_at FROM experiments WHERE kind IN ('protocol','agent','descriptive') ORDER BY id DESC LIMIT 12"),
                     width="stretch", hide_index=True)
    with b:
        st.subheader("Alerts")
        if al.empty:
            st.success("No open alerts.")
        for _, r in al.head(15).iterrows():
            icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}[r["level"]]
            cc = st.columns([6, 1])
            cc[0].markdown(f"{icon} **{r['source']}** · {r['ts'][5:16]}  \n{r['message']}")
            if cc[1].button("ack", key=f"ack{r['id']}"):
                with DB.tx(c):
                    c.execute("UPDATE alerts SET acknowledged_at=?, acknowledged_by='user' WHERE id=?", (DB.now(), int(r["id"])))
                    DB.audit(c, "user", "ack_alert", "alerts", int(r["id"]))
                st.rerun()
        st.subheader("Decisions waiting for you")
        from qpl.hub import agent
        for it in agent.plan(c):
            if it["needs_user"] or (it["blocked_by"] and "status is proposed" in " ".join(it["blocked_by"])):
                st.markdown(f"- **{it['title']}**: {it['needs_user'] or 'proposed item: approve it in research/hub/agenda.json to let the agent run it'}")


# ============================================================================================================ Research
def research():
    st.header("Research Lab")
    from qpl.hub import agent
    t1, t2, t3 = st.tabs(["Experiments", "Agenda (autonomous agent)", "Hypotheses"])
    with t1:
        cols = st.columns(4)
        kinds = q("SELECT DISTINCT kind FROM experiments")["kind"].tolist()
        kind = cols[0].multiselect("Kind", kinds, default=[k for k in kinds if k != "legacy_variant"])
        dec = cols[1].multiselect("Decision", q("SELECT DISTINCT COALESCE(decision,'') d FROM experiments")["d"].tolist())
        txt = cols[2].text_input("Search title / key")
        hold = cols[3].selectbox("Uses the 2025-26 holdout", ["any", "yes", "no"])
        df = q("SELECT id, key, kind, title, status, decision, trials_added, uses_holdout, registered_at, finished_at, source FROM experiments ORDER BY id DESC")
        if kind:
            df = df[df.kind.isin(kind)]
        if dec:
            df = df[df.decision.fillna("").isin(dec)]
        if txt:
            df = df[df.title.fillna("").str.contains(txt, case=False) | df.key.str.contains(txt, case=False)]
        if hold != "any":
            df = df[df.uses_holdout == (1 if hold == "yes" else 0)]
        tot = q("SELECT kind, SUM(trials_added) t FROM experiments GROUP BY kind")
        st.caption("Trials recorded: " + " · ".join(f"{r.kind} {int(r.t)}" for r in tot.itertuples()) + ". The selection-bias gate uses the protocol trials (see METHODOLOGY_AUDIT).")
        st.dataframe(df, width="stretch", hide_index=True, height=420)
        sel = st.number_input("Show experiment id", min_value=0, value=0, step=1)
        if sel:
            r = q("SELECT * FROM experiments WHERE id=?", (int(sel),))
            if len(r):
                st.json({k: js(v) for k, v in r.iloc[0].to_dict().items()}, expanded=False)
    with t2:
        st.caption("Ranked by economic relevance × information gain × diversification ÷ (1 + cost hours); ×0.2 if a similar test exists. "
                   "Only 'approved' items run; every run is registered before it starts and judged by its pre-registered rule.")
        st.dataframe(pd.DataFrame(agent.plan(c)), width="stretch", hide_index=True)
        if st.button("Queue one agent step now"):
            from qpl.hub import jobs
            st.success(f"queued job {jobs.enqueue(c, 'agent_step', {}, dedup_key='manual:agent_step', actor='user')} (the worker runs it)")
    with t3:
        st.dataframe(q("SELECT key, text, family, status, verdict, registered_at, source FROM hypotheses ORDER BY id DESC"), width="stretch", hide_index=True)


# ============================================================================================================ Strategies
def strategies():
    st.header("Strategy Center")
    from qpl.hub import registry as RG
    df = q("SELECT v.id, s.key, s.name, s.market, s.family, v.version, v.state, v.code_ref, v.created_at FROM strategy_versions v JOIN strategies s ON s.id=v.strategy_id ORDER BY s.market, s.key")
    st.dataframe(df, width="stretch", hide_index=True)
    vid = st.selectbox("Version", df["id"].tolist(), format_func=lambda i: f"{df.set_index('id').loc[i, 'name']} {df.set_index('id').loc[i, 'version']}") if len(df) else None
    if vid:
        r = q("SELECT s.description, s.hypothesis, v.params, v.notes, v.config_hash FROM strategy_versions v JOIN strategies s ON s.id=v.strategy_id WHERE v.id=?", (vid,)).iloc[0]
        st.markdown(f"**{r['description'] or ''}**  \n{r['notes'] or ''}  \nconfig hash `{r['config_hash'][:16]}`")
        st.subheader("Lifecycle history")
        st.dataframe(q("SELECT ts, from_state, to_state, use_scope, reason, actor FROM lifecycle_events WHERE version_id=? ORDER BY id", (vid,)), width="stretch", hide_index=True)
        st.subheader("Paper deviation (sleeve in the paper ledger)")
        name = df.set_index("id").loc[vid, "name"]
        sp = q("SELECT a.key, SUM(p.pnl) cum_unit_pnl, COUNT(*) hours FROM paper_sleeve_pnl p JOIN paper_accounts a ON a.id=p.account_id WHERE p.sleeve=? GROUP BY a.key", (name,))
        tag("paper"); st.dataframe(sp, width="stretch", hide_index=True)
        with st.form("transition"):
            cur = df.set_index("id").loc[vid, "state"]
            to = st.selectbox("Move to", sorted(RG.ALLOWED.get(cur, [])) or ["(no transition allowed)"])
            scope = st.selectbox("Use scope (approval only)", ["", *RG.SCOPES])
            reason = st.text_area("Reason and evidence (required)")
            if st.form_submit_button("Record transition"):
                try:
                    RG.transition(c, int(vid), to, reason, actor="user", use_scope=scope or None); st.success("recorded"); st.rerun()
                except Exception as e:                                     # noqa: BLE001
                    st.error(str(e))


# ============================================================================================================ Portfolio & risk
@st.cache_data(show_spinner="Computing risk...")
def book_risk():
    from qpl.hub.risk import portfolio_risk
    import crypto_sleeves as CS
    H = pd.read_parquet(ROOT / "results/v98_paper_sleeves.parquet").drop(columns="port").loc[:"2026-09-30 23:00"]
    D = H.groupby(H.index.floor("D")).sum().loc["2022":]
    _, W, mult = CS.portfolio_v5(H); w = W.reindex(D.index).ffill().mean()
    return portfolio_risk(D, w), D


def portfolio():
    st.header("Portfolio & Risk")
    t1, t2, t5, t3 = st.tabs(["Crypto book v9.8", "Paper accounts", "Shadow accounts (per strategy / portfolio variants)", "Risk limits & events"])
    with t1:
        tag("backtest")
        if not (ROOT / "results/v98_paper_sleeves.parquet").exists():
            st.warning("results/v98_paper_sleeves.parquet not found"); return
        R, D = book_risk()
        a, b = st.columns(2)
        rc = pd.Series(R["risk_contribution"]).sort_values()
        a.plotly_chart(px.bar(rc, orientation="h", template=TPL, labels={"value": "share of book variance", "index": ""}, title="Risk contribution (average weights 2022-26)").update_layout(showlegend=False, height=360), width="stretch")
        b.plotly_chart(px.imshow(pd.DataFrame(R["correlation"]), template=TPL, zmin=-1, zmax=1, color_continuous_scale="RdBu_r", title="Daily correlation").update_layout(height=360), width="stretch")
        st.subheader("Stress tests (weights fixed)")
        st.table(pd.Series(R["stress"]).rename("result").to_frame())
        yr = D.groupby(D.index.year).apply(lambda x: x.mean() / x.std() * np.sqrt(365)).round(2)
        st.subheader("Sleeve Sharpe by year"); st.dataframe(yr, width="stretch")
        st.caption("Leave-one-out marginal contributions and regimes: research/LEADERBOARD.md Gen473; costs on net trades: Gen473b.")
    with t2:
        tag("paper")
        acc = q("SELECT id, key, status, initial_capital, last_data_ts FROM paper_accounts ORDER BY key")
        st.dataframe(acc, width="stretch", hide_index=True)
        k = st.selectbox("Account", acc["key"].tolist()) if len(acc) else None
        if k:
            from qpl.hub import health
            P = health.paper_series(c, k)
            if len(P):
                st.plotly_chart(px.line(P["equity"], template=TPL, title=f"{k} equity (paper, frozen hourly ledger)").update_layout(height=300, showlegend=False), width="stretch")
            if st.button("Run health check"):
                st.json(health.check_account(c, k), expanded=True)
            st.dataframe(q("SELECT ts, coin, side, usd, type, reason FROM paper_orders o JOIN paper_accounts a ON a.id=o.account_id WHERE a.key=? ORDER BY ts DESC LIMIT 200", (k,)),
                         width="stretch", hide_index=True, height=240)
    with t5:
        shadow_tab()
    with t3:
        from qpl.hub import risk
        risk.ensure_defaults(c)
        st.dataframe(q("SELECT * FROM risk_limits"), width="stretch", hide_index=True)
        st.dataframe(q("SELECT * FROM risk_events ORDER BY id DESC LIMIT 100"), width="stretch", hide_index=True)
        st.caption("A 'stop' on paper:v98 also writes the dry-run bot's kill switch bot_state/STOP. Recovery always needs a manual review.")


def shadow_tab():
    from qpl.hub import shadow
    tag("paper")
    st.caption("Shadow accounts are built EXACTLY from a running paper trader's frozen hourly ledger (same hours, fills and costs), "
               "per strategy or as an alternative portfolio. Hours before a shadow was defined are a retroactive replay; only hours after it are forward paper evidence.")
    S = q("SELECT a.id, a.key, a.initial_capital, a.config, a.last_data_ts, SUM(CASE WHEN e.retro=0 THEN 1 ELSE 0 END) forward_hours, COUNT(e.ts) hours, "
          "SUM(CASE WHEN e.retro=0 THEN e.ret ELSE 0 END) forward_return_sum FROM paper_accounts a LEFT JOIN paper_equity e ON e.account_id=a.id "
          "WHERE a.key LIKE 'shadow:%' GROUP BY a.id ORDER BY a.key")
    if S.empty:
        st.info("No shadow accounts yet. They are created automatically at the next ingest (hub_start.bat), or define one below.")
    else:
        S["source"] = S["config"].map(lambda x: js(x)["source"]); S["kind"] = S["config"].map(lambda x: js(x)["kind"])
        S["description"] = S["config"].map(lambda x: js(x).get("description", "")); S["defined_at"] = S["config"].map(lambda x: js(x)["defined_at"][:16])
        st.dataframe(S[["key", "source", "kind", "defined_at", "hours", "forward_hours", "forward_return_sum", "last_data_ts", "description"]], width="stretch", hide_index=True)
        pick = st.multiselect("Compare equity", S["key"].tolist(), default=S["key"].tolist()[:4])
        if pick:
            E = q("SELECT a.key, e.ts, e.equity / a.initial_capital AS growth, e.retro FROM paper_equity e JOIN paper_accounts a ON a.id=e.account_id WHERE a.key IN (%s)" % ",".join("?" * len(pick)), tuple(pick))
            if len(E):
                fig = px.line(E, x="ts", y="growth", color="key", template=TPL, title="Growth of 1 (dashed region = retroactive replay)")
                fd = E[E.retro == 0]["ts"].min()
                if isinstance(fd, str):
                    fig.add_vline(x=fd, line_dash="dash")
                st.plotly_chart(fig.update_layout(height=360), width="stretch")
    with st.form("new_shadow"):
        st.markdown("**Define a new shadow account** (immutable once defined; a change = a new key)")
        cc = st.columns(4)
        key = cc[0].text_input("Key (e.g. v98:weiss_x2)"); src = cc[1].selectbox("Source paper account", q("SELECT key FROM paper_accounts WHERE key LIKE 'paper:%' ORDER BY key DESC")["key"].tolist() or ["paper:v98"])
        kind = cc[2].selectbox("Kind", ["sleeve", "reweighted", "custom", "rule"]); risk_ = cc[3].number_input("Risk multiplier", 0.1, 3.0, 1.5, 0.1)
        sleeves = q("SELECT DISTINCT sleeve FROM paper_sleeve_pnl")["sleeve"].tolist()
        cc2 = st.columns(3)
        slv = cc2[0].selectbox("Sleeve (kind = sleeve)", sleeves or ["C*"]); spec_json = cc2[1].text_input("Multipliers / weights JSON (reweighted / custom)", '{"Weiss expiry": 2.0}')
        rule = cc2[2].selectbox("Rule (kind = rule)", list(shadow.RULES)); desc = st.text_input("Why (hypothesis / purpose)")
        if st.form_submit_button("Define and compute"):
            try:
                spec = {"sleeve": slv, "vol_target": 0.15} if kind == "sleeve" else {"rule": rule} if kind == "rule" else (
                    {"multipliers": js(spec_json)} if kind == "reweighted" else {"weights": js(spec_json)})
                shadow.define(c, key, src, kind, spec, risk=risk_, description=desc)
                st.success(shadow.recompute(c, f"shadow:{key}")); st.rerun()
            except Exception as e:                                         # noqa: BLE001
                st.error(str(e))
    if st.button("Recompute all shadows now"):
        st.json(shadow.recompute(c))


# ============================================================================================================ Prop firms
def propfirms():
    st.header("Prop Firm Center")
    from qpl.hub import prop
    st.warning("Rules are only as good as their sources. Facts marked 'uncertain' come from project snapshots or third parties; check the firm's official "
               "pages before any purchase. Nothing here buys, connects or trades.")
    rs = q("SELECT s.id, f.key firm, s.account_type, s.version, s.effective_from, s.superseded_at FROM prop_rule_sets s JOIN prop_firms f ON f.id=s.firm_id ORDER BY f.key, s.account_type, s.version")
    fs = q("SELECT f.status, COUNT(*) n FROM prop_rule_facts f GROUP BY f.status")
    st.caption("Facts by status: " + " · ".join(f"{r.status} {r.n}" for r in fs.itertuples()) + f" · unchecked or older than 30 days: {len(prop.stale_facts(c))}")
    t1, t2, t3, t4 = st.tabs(["Rules & sources", "Compatibility", "Challenge simulation", "Multi-account allocation"])
    with t1:
        st.dataframe(rs, width="stretch", hide_index=True)
        rid = st.selectbox("Rule set", rs["id"].tolist(), format_func=lambda i: f"{rs.set_index('id').loc[i, 'firm']} · {rs.set_index('id').loc[i, 'account_type']} v{rs.set_index('id').loc[i, 'version']}")
        if rid:
            st.dataframe(q("SELECT field, value, status, confidence, source_url, checked_at, quote, note FROM prop_rule_facts WHERE rule_set_id=? ORDER BY field", (int(rid),)),
                         width="stretch", hide_index=True)
            with st.form("fact"):
                st.markdown("**Record / verify a rule** (verified = you read it on the firm's official page; paste the exact sentence)")
                cc = st.columns(3)
                fld = cc[0].selectbox("Field", sorted(set(prop.SIM_FIELDS) | set(prop.POLICY_FIELDS) | {"per_trade_loss_cap", "prohibited_strategies", "vps_allowed"}))
                val = cc[1].text_input("Value (JSON: 0.05, true, \"text\")"); stt = cc[2].selectbox("Status", ["verified", "uncertain", "ambiguous", "not_found", "assumption"])
                url = st.text_input("Official source URL"); quote = st.text_area("Exact quote"); day = st.date_input("Date checked")
                if st.form_submit_button("Save fact"):
                    try:
                        prop.record_fact(c, int(rid), fld, js(val) if val else None, stt, url or None, quote or None, str(day)); st.success("saved"); st.rerun()
                    except Exception as e:                                 # noqa: BLE001
                        st.error(str(e))
            snaps = sorted((ROOT / "research_data/prop_pages").glob(f"{rs.set_index('id').loc[rid, 'firm']}/*/index.json"))
            st.caption(f"Saved official page snapshots for this firm: {len(snaps)} (get_prop_rules.bat on your PC)" + (f", newest {snaps[-1].parent.name}" if snaps else ""))
    with t2:
        if st.button("Assess the v9.8 crypto book against every current rule set"):
            out = [prop.compatibility(c, int(i)) for i in rs[rs.superseded_at.isna()]["id"]]
            st.session_state["compat"] = out
        res = st.session_state.get("compat") or [js(x) for x in q("SELECT reasons FROM compat_assessments ORDER BY id DESC LIMIT 40")["reasons"]]
        if res:
            st.dataframe(pd.DataFrame([{"firm": r["firm"], "account": r["account_type"], "status": r["status"], "blocking": "; ".join(r["blocking"]),
                                        "missing / unverified": len(r["missing_or_unverified"])} for r in res]), width="stretch", hide_index=True)
            st.caption("Status 'verified compatible' requires every needed rule to be verified from an official source; otherwise the best possible status is 'potentially compatible'.")
    with t3:
        tag("model")
        sim_sets = rs[rs.superseded_at.isna() & ~rs.account_type.str.contains("config/")]
        rid = st.selectbox("Account type", sim_sets["id"].tolist(), format_func=lambda i: sim_sets.set_index("id").loc[i, "account_type"], key="simrs")
        cc = st.columns(4)
        lvl = cc[0].selectbox("Assumed live Sharpe", [1.0, 1.2, 1.5, 1.7, 2.0, "backtest"], index=3)
        rch = cc[1].number_input("Challenge risk", 0.5, 3.0, 1.5, 0.25); rfd = cc[2].number_input("Funded risk", 0.5, 3.0, 1.5, 0.25)
        win = cc[3].selectbox("Return window", ["2025-01-01 / 2026-09-30", "2022-01-01 / 2024-12-31"])
        if st.button("Run simulation (about a minute)"):
            p = pd.read_parquet(ROOT / "results/v98b_book_hourly.parquet")["book"] if (ROOT / "results/v98b_book_hourly.parquet").exists() else None
            if p is None:
                st.error("results/v98b_book_hourly.parquet missing")
            else:
                a, b = win.split(" / ")
                r = prop.simulate(c, int(rid), p, "crypto book v9.8", "results/v98b_book_hourly.parquet", None if lvl == "backtest" else float(lvl),
                                  rch, rfd, window=(a, b + " 23:00"))
                st.json(r["results"])
    with t4:
        tag("model")
        st.caption("All accounts trade the same book and share one return path: more accounts add money and fees, not safety. Presets are unverified snapshots.")
        from qpl.hub import allocation, income
        cc = st.columns(5)
        sc = cc[0].selectbox("Scenario", list(income.SCENARIOS), index=1, key="alsc"); mt = int(cc[1].number_input("Max accounts", 1, 6, 3))
        mpf = int(cc[2].number_input("Max per firm type", 1, 3, 1)); fb = cc[3].number_input("Fee budget (USD)", 500.0, 50000.0, 5000.0, 500.0)
        gap = int(cc[4].number_input("Days between starts", 0, 365, 120))
        if st.button("Optimise allocation (a few minutes)"):
            h = pd.read_parquet(ROOT / "results/v98b_book_hourly.parquet")["book"]
            st.session_state["alloc"] = allocation.optimise(h, income.SCENARIOS[sc], max_per_firm=mpf, max_total=mt, fee_budget_usd=fb, gap_days=gap, n_paths=80)
        r = st.session_state.get("alloc")
        if r and "all" in r:
            st.markdown("**Conservative (best 2-year p10 of net cash)**"); st.dataframe(pd.DataFrame(r["conservative_top"]), width="stretch", hide_index=True)
            st.markdown("**Aggressive (best year-2 mean month)**"); st.dataframe(pd.DataFrame(r["aggressive_top"]), width="stretch", hide_index=True)
            st.caption(" · ".join(r["caveats"]))
    with t3:
        st.subheader("Stored simulations")
        st.dataframe(q("SELECT s.ts, f.key firm, r.account_type, s.sharpe_level, json_extract(s.results,'$.P_pass_single_attempt') p_pass, "
                       "json_extract(s.results,'$.net_mean') net_mean_2y, json_extract(s.results,'$.net_p10') net_p10, json_extract(s.results,'$.P_net_profit') p_profit "
                       "FROM challenge_sims s JOIN prop_rule_sets r ON r.id=s.rule_set_id JOIN prop_firms f ON f.id=r.firm_id ORDER BY s.id DESC"), width="stretch", hide_index=True)


# ============================================================================================================ Income
def income_page():
    st.header("Income Planner")
    tag("model")
    st.caption("Monthly cash = challenge fees, failures, funded breaches, payout cadence and split from the firm rule engine on bootstrapped book returns at an ASSUMED "
               "live Sharpe, then payout rejection / delay, costs, FX and a flat tax placeholder. Accounts on one strategy move together. Not a forecast.")
    from qpl.hub import income
    sc = st.selectbox("Scenario", list(income.SCENARIOS), index=1)
    s = dict(income.SCENARIOS[sc]); cc = st.columns(5)
    s["live_sharpe"] = cc[0].number_input("Live Sharpe", 0.0, 4.0, float(s["live_sharpe"]), 0.1)
    s["payout_reject_prob"] = cc[1].number_input("Payout rejection prob.", 0.0, 1.0, float(s["payout_reject_prob"]), 0.01)
    s["payout_delay_days"] = int(cc[2].number_input("Payout delay (days)", 0, 60, int(s["payout_delay_days"])))
    s["monthly_costs_usd"] = cc[3].number_input("Monthly costs (USD)", 0.0, 5000.0, float(s["monthly_costs_usd"]), 25.0)
    tgt = cc[4].number_input("Target per month (EUR)", 1000.0, 100000.0, 10000.0, 500.0)
    cc2 = st.columns(4)
    n_acc = int(cc2[0].number_input("Accounts (HyroTrader 2-Step $200k)", 1, 12, 2)); gap = int(cc2[1].number_input("Days between account starts", 0, 365, 180))
    tax = cc2[2].number_input("Tax placeholder (flat)", 0.0, 0.6, 0.37, 0.01); fx = cc2[3].number_input("USD per EUR", 0.8, 1.5, 1.08, 0.01)
    if st.button("Run scenario"):
        p = pd.read_parquet(ROOT / "results/v98b_book_hourly.parquet")["book"]
        plan = [{"preset": "HyroTrader Two-Step $200k", "start_day": i * gap, "budget": 3} for i in range(n_acc)]
        r = income.simulate(p, s, plan, tgt, usd_per_eur=fx, tax_rate=tax, n_paths=300)
        income.store(c, f"{sc} {n_acc} acc", r); st.session_state["inc"] = r
    r = st.session_state.get("inc")
    if r:
        k = st.columns(4)
        k[0].metric("Year-2 mean month (EUR, before tax)", f"€{r['second_year_mean_month_eur']:,.0f}")
        k[1].metric(f"P(month ≥ €{r['target_month_eur']:,.0f}) in year 2", f"{r['P_month_at_or_above_target_in_year2']:.0%}")
        k[2].metric("P(net loss over 2 years)", f"{r['P_net_loss_over_horizon']:.0%}")
        k[3].metric("Worst cumulative cash p10", f"€{r['worst_cumulative_cash_eur_p10']:,.0f}", help="reserve needed for fees before payouts")
        st.json({k_: v for k_, v in r.items() if k_ not in ("plan",)}, expanded=False)
    st.subheader("Stored scenarios")
    st.dataframe(q("SELECT ts, name, json_extract(results,'$.second_year_mean_month_eur') year2_month_eur, json_extract(results,'$.P_month_at_or_above_target_in_year2') p_target, "
                   "json_extract(results,'$.P_net_loss_over_horizon') p_loss FROM income_scenarios ORDER BY id DESC"), width="stretch", hide_index=True)


# ============================================================================================================ Finance
def finance_page():
    st.header("Finance")
    tag("actual")
    from qpl.hub import finance
    with st.form("add_tx"):
        cc = st.columns(6)
        kind = cc[0].selectbox("Kind", ["challenge_fee", "subscription", "data", "infrastructure", "software", "other_expense", "payout", "tax_payment", "capital_in", "capital_out"])
        amt = cc[1].number_input("Amount", 0.0, 1e7, 0.0); cur = cc[2].selectbox("Currency", ["USD", "EUR", "USDT"])
        status = cc[3].selectbox("Status", ["paid", "planned", "requested", "approved", "received", "rejected", "cancelled"])
        firm = cc[4].text_input("Firm"); ref = cc[5].text_input("Reference (prevents duplicates)")
        note = st.text_input("Note"); ts = st.date_input("Date")
        if st.form_submit_button("Record"):
            try:
                finance.add(c, kind, amt, cur, status, ts=str(ts), firm=firm or None, external_ref=ref or None, note=note or None); st.success("recorded")
            except Exception as e:                                         # noqa: BLE001
                st.error(str(e))
    T = q("SELECT * FROM finance_tx ORDER BY ts DESC")
    st.dataframe(T, width="stretch", hide_index=True)
    if len(T):
        cc = st.columns(3)
        tid = cc[0].selectbox("Transaction", T["id"].tolist()); new = cc[1].selectbox("New status", ["requested", "approved", "received", "rejected", "paid", "cancelled"])
        if cc[2].button("Change status"):
            try:
                finance.set_status(c, int(tid), new); st.rerun()
            except Exception as e:                                         # noqa: BLE001
                st.error(str(e))
    fx = st.text_input("FX rates to the base currency (JSON, e.g. {\"EUR\": 1.08})", "{}")
    st.json(finance.report(c, js(fx) or {}))


# ============================================================================================================ System
def system():
    st.header("System Health")
    from qpl.hub import jobs as J
    t1, t2, t3, t4 = st.tabs(["Jobs", "Schedules", "Data & backups", "Audit log"])
    with t1:
        df = q("SELECT id, kind, status, priority, attempts, max_attempts, created_at, started_at, finished_at, schedule_name, substr(error,1,200) error FROM jobs ORDER BY id DESC LIMIT 300")
        st.dataframe(df, width="stretch", hide_index=True, height=360)
        cc = st.columns(4)
        jid = cc[0].number_input("Job id", 0, step=1); act = cc[1].selectbox("Action", ["cancel", "pause", "resume"])
        if cc[2].button("Apply") and jid:
            st.info(f"{J.set_status(c, int(jid), act)} job(s) changed")
        from qpl.hub.handlers import HANDLERS
        kind = cc[3].selectbox("Queue a job", sorted(k for k in HANDLERS if k not in ("noop", "run_script", "agent_evaluate")))
        if st.button("Queue"):
            st.success(f"job {J.enqueue(c, kind, {}, dedup_key=f'manual:{kind}', actor='user')} queued; the worker (hub_start.bat) runs it")
        hb = q("SELECT ts, action, details FROM audit_log WHERE actor='worker' AND action IN ('start','stop') ORDER BY id DESC LIMIT 5")
        st.caption("Worker start/stop events:"); st.dataframe(hb, width="stretch", hide_index=True)
    with t2:
        J.ensure_schedules(c); S = q("SELECT * FROM schedules"); st.dataframe(S, width="stretch", hide_index=True)
        cc = st.columns(4)
        nm = cc[0].selectbox("Schedule", S["name"].tolist()); en = cc[1].selectbox("Enabled", [1, 0]); ev = cc[2].number_input("Every (minutes)", 5, 100000, 60)
        if cc[3].button("Save schedule"):
            with DB.tx(c):
                c.execute("UPDATE schedules SET enabled=?, every_minutes=? WHERE name=?", (en, int(ev), nm)); DB.audit(c, "user", "schedule", "schedules", nm, {"enabled": en, "every": ev})
            st.rerun()
    with t3:
        st.dataframe(q("SELECT key, market, kind, n_files, ROUND(bytes/1e6,1) mb, last_ts, status, checked_at FROM datasets"), width="stretch", hide_index=True)
        st.dataframe(q("SELECT ts, path, bytes, verify_result FROM backups ORDER BY id DESC LIMIT 20"), width="stretch", hide_index=True)
        if st.button("Back up now (and verify)"):
            st.json(DB.backup(c))
    with t4:
        st.dataframe(q("SELECT * FROM audit_log ORDER BY id DESC LIMIT 500"), width="stretch", hide_index=True, height=480)


{"Overview": overview, "Research Lab": research, "Strategy Center": strategies, "Portfolio & Risk": portfolio, "Prop Firm Center": propfirms,
 "Income Planner": income_page, "Finance": finance_page, "System Health": system}[page]()
