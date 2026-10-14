"""Quant Prop Lab - Backtest Lab (local web app).

    pip install -r requirements-lab.txt
    streamlit run app/lab.py

Pick a data set and a strategy, set costs and risk, and get: equity curve, drawdowns, monthly returns, edge diagnostics
(in-sample vs out-of-sample, bootstrap, deflated Sharpe, random-timing test, parameter sensitivity), per-asset and trade
statistics, and a Crypto Fund Trader challenge simulation. Add strategies in strategies_user/, data via
`python -m qpl.lab.download ...` or a CSV upload. See LAB_README.md."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import analysis as A, data as D, engine as EN, strategies as S  # noqa: E402

st.set_page_config(page_title="Backtest Lab", layout="wide")
PCT = lambda v: "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.1%}"
NUM = lambda v: "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.2f}"
USD = lambda v: f"{'-' if v < 0 else ''}${abs(v):,.0f}"


def fig_layout(fig, h=360, ytitle=None, log=False):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.08), hovermode="x unified",
                      yaxis_title=ytitle)
    if log:
        fig.update_yaxes(type="log")
    return fig


# ------------------------------------------------------------------ cached loaders
@st.cache_data(show_spinner="Loading data...")
def load_source(name: str):
    return D.list_sources()[name]()


@st.cache_data(show_spinner="Reading CSV...")
def load_csv(content: bytes, fname: str):
    return D.read_csv(content, fname)


@st.cache_data(show_spinner="Running backtest...")
def backtest(_bars, bars_key, strat_name, params_t, cfg_t):
    reg, _ = S.registry()
    strat = reg[strat_name]()
    params = dict(params_t); cfg = EN.Config(**dict(cfg_t))
    sig = strat.signal(_bars, params)
    w = EN.size(_bars, sig, cfg, strat.sizing)
    r = EN.run(_bars, w, cfg)
    r["info"] = getattr(strat, "info", None)          # optional strategy details (e.g. chosen pairs, training windows)
    return r, EN.to_daily(r["bars"], _bars.freq)


# ------------------------------------------------------------------ sidebar: data
st.sidebar.title("Backtest Lab")
st.sidebar.header("1 · Data")
sources = D.list_sources()
choice = st.sidebar.selectbox("Data set", list(sources) + ["Upload a CSV file"], key="src")
if choice == "Upload a CSV file":
    up = st.sidebar.file_uploader("CSV: time, symbol, open, high, low, close, volume", type=["csv"], key="csv")
    if not up:
        st.info("Upload a CSV (columns time, open, high, low, close; optional symbol and volume) or choose a data set on the left.")
        st.stop()
    bars_all = load_csv(up.getvalue(), up.name); bars_key = f"csv:{up.name}:{len(up.getvalue())}"
else:
    try:
        bars_all = load_source(choice); bars_key = choice
    except Exception as e:
        st.error(f"Could not load '{choice}': {e}"); st.stop()

tf_opts = D.FREQS[D.FREQS.index(bars_all.freq):]
tf = st.sidebar.selectbox("Timeframe", tf_opts, index=0, key=f"tf_{bars_key}")
default_syms = [s for s in ("BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK") if s in bars_all.symbols] or bars_all.symbols[:10]
syms = st.sidebar.multiselect("Assets", bars_all.symbols, default=default_syms, key=f"syms_{bars_key}")
if not syms:
    st.warning("Choose at least one asset."); st.stop()
idx0, idx1 = bars_all.close.index.min().date(), bars_all.close.index.max().date()
c1, c2 = st.sidebar.columns(2)
start = c1.date_input("From", value=max(idx0, pd.Timestamp("2018-01-01").date()) if idx0 < pd.Timestamp("2018-01-01").date() else idx0,
                      min_value=idx0, max_value=idx1, key=f"start_{bars_key}")
end = c2.date_input("To", value=idx1, min_value=idx0, max_value=idx1, key=f"end_{bars_key}")
# keep warm-up history before 'start' so indicators are ready on day one
bars = D.resample(bars_all.select(syms), tf)

# ------------------------------------------------------------------ sidebar: strategy
st.sidebar.header("2 · Strategy")
reg, errs = S.registry()
for f, e in errs.items():
    st.sidebar.error(f"strategies_user/{f} failed to load: {e}")
sname = st.sidebar.selectbox("Strategy", list(reg), key="strategy")
strat = reg[sname]()
st.sidebar.caption(strat.description)
if strat.sizing == "raw":
    st.sidebar.caption("This strategy sizes its own positions: the volatility target and minimum-history settings below do not apply.")
params = {}
for k, p in strat.params.items():
    key = f"p_{sname}_{k}"
    if isinstance(p.default, bool):
        params[k] = st.sidebar.checkbox(k.replace("_", " "), value=p.default, help=p.help, key=key)
    elif p.choices:
        params[k] = st.sidebar.selectbox(k, p.choices, index=p.choices.index(p.default), help=p.help, key=key)
    elif isinstance(p.default, int):
        params[k] = int(st.sidebar.number_input(k, int(p.min), int(p.max), int(p.default), int(p.step or 1), help=p.help, key=key))
    else:
        params[k] = float(st.sidebar.number_input(k, float(p.min), float(p.max), float(p.default), float(p.step or 0.1), help=p.help, key=key))

st.sidebar.header("3 · Costs and risk")
cost = st.sidebar.number_input("Cost per trade side (bp of traded value)", 0.0, 100.0, 7.5, 0.5, key="cost",
                               help="Bybit taker 5.5 bp + ~2 bp slippage = 7.5")
fund = st.sidebar.number_input("Funding / swap paid by longs (bp per day)", -50.0, 50.0, 0.0, 0.5, key="fund",
                               help="0 on the CFT Bybit route. Exchange perps average ~1 bp per 8h = 3 bp/day.")
avt = st.sidebar.number_input("Per-asset volatility target (0 = off)", 0.0, 2.0, 0.40, 0.05, key="avt",
                              help="Each asset's position is scaled to this annual volatility (capped at 1x).")
lev = st.sidebar.number_input("Leverage (whole book)", 0.05, 10.0, 0.79 if sname.startswith("C*") else 1.0, 0.05, key="lev",
                              help="0.79 = the research C* setting (~15% annual volatility)")
minh = st.sidebar.number_input("Min. history before trading an asset (days)", 0, 400, 200, 10, key="minh")
if "MaxAI" in sname and cost > 2:
    st.sidebar.warning(f"{cost:g} bp per side is a crypto cost. MaxAI trades several times a day: NQ futures cost ≈ 0.3 bp per side, "
                       "index CFDs at a prop firm ≈ the spread (US100 ~1 point ≈ 0.6 bp).")
cfg = EN.Config(cost_bps=cost, funding_bps_day=fund, asset_vol_target=avt, leverage=lev, min_history_days=int(minh))

st.sidebar.header("4 · Honesty checks")
split_default = pd.Timestamp("2024-01-01").date()
if not idx0 < split_default < idx1:
    split_default = (pd.Timestamp(idx0) + 0.7 * (pd.Timestamp(idx1) - pd.Timestamp(idx0))).date()
split = st.sidebar.date_input("Out-of-sample starts", value=split_default, min_value=idx0, max_value=idx1, key=f"split_{bars_key}",
                              help="Tune only on data before this date; judge the strategy on data after it.")
if "trials" not in st.session_state:
    st.session_state.trials = set()
trial_key = (bars_key, tf, tuple(syms), sname, tuple(sorted(params.items())), cost, fund, avt, minh)
st.session_state.trials.add(trial_key)
n_trials = st.sidebar.number_input("Trials so far (for deflated Sharpe)", 1, 100000, max(1, len(st.session_state.trials)), key="ntr",
                                   help="Every distinct setting you looked at counts. The research project used ~170 for C*.")

# ------------------------------------------------------------------ run
res, daily = backtest(bars, (bars_key, tf, tuple(syms)), sname, tuple(sorted(params.items())), tuple(sorted(vars(cfg).items())))
bh_res, bh_daily = backtest(bars, (bars_key, tf, tuple(syms)), "Buy & hold (benchmark)", tuple(), tuple(sorted(vars(cfg).items())))
sl = slice(pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23))
net = res["bars"]["net"].loc[sl]; bh = bh_res["bars"]["net"].loc[sl]
dd_ = daily.loc[sl]; ppy = bars.periods_per_year; bpd = D.BPD.get(bars.freq, 1)
S_ = A.summary(net, ppy); B_ = A.summary(bh, ppy)
if not S_:
    st.error("Not enough data in this range (or the strategy never traded)."); st.stop()

st.title(sname)
st.caption(f"{bars.name} · {tf} bars · {len(syms)} assets · {start} → {end} · costs {cost} bp/side · leverage {lev}×")
k = st.columns(8)
for col, (lab, val, fmt) in zip(k, [("Sharpe", S_["Sharpe"], NUM), ("Return / year", S_["CAGR"], PCT), ("Max drawdown", S_["Max drawdown"], PCT),
                                     ("Volatility", S_["Volatility"], PCT), ("Positive months", S_["Positive months"], PCT),
                                     ("Worst month", S_["Worst month"], PCT), ("Worst intraday day", dd_["worst"].min(), PCT),
                                     ("Benchmark Sharpe", B_.get("Sharpe", np.nan), NUM)]):
    col.metric(lab, fmt(val))

tabs = st.tabs(["Equity", "Returns", "Edge check", "Assets & trades", "Prop firm (CFT)", "Compare strategies", "Export"])

# ------------------------------------------------------------------ Equity
with tabs[0]:
    eq = (1 + net.fillna(0)).cumprod(); beq = (1 + bh.fillna(0)).cumprod()
    fig = go.Figure()
    fig.add_scatter(x=eq.index, y=eq, name=sname, line=dict(width=2))
    fig.add_scatter(x=beq.index, y=beq, name="Buy & hold (same assets, same sizing)", line=dict(width=1, dash="dot"))
    fig.add_vline(x=pd.Timestamp(split), line_dash="dash", line_color="gray", annotation_text="out-of-sample →")
    log = st.toggle("Log scale", value=True, key="log")
    st.plotly_chart(fig_layout(fig, 420, "growth of 1", log), width="stretch")
    c1, c2 = st.columns(2)
    d = A.drawdown(net); fd = go.Figure(go.Scatter(x=d.index, y=d, fill="tozeroy", name="drawdown", line=dict(width=1)))
    c1.plotly_chart(fig_layout(fd, 260, "drawdown").update_yaxes(tickformat=".0%"), width="stretch")
    ex = res["bars"]["gross_exposure"].loc[sl]
    fe = go.Figure(go.Scatter(x=ex.index, y=ex, name="gross exposure", line=dict(width=1)))
    c2.plotly_chart(fig_layout(fe, 260, "exposure (× equity)"), width="stretch")
    st.dataframe(pd.DataFrame({"Strategy": S_, "Buy & hold": B_}).T.style.format(
        {c: "{:.1%}" for c in ["Total return", "CAGR", "Volatility", "Max drawdown", "Positive months", "Worst month", "Best month", "Worst bar"]}
        | {c: "{:.2f}" for c in ["Sharpe", "Sortino", "Calmar", "Skew", "Years"]}), width="stretch")

# ------------------------------------------------------------------ Returns
with tabs[1]:
    mt = A.monthly_table(net)
    mt.columns = [pd.Timestamp(2000, c, 1).strftime("%b") if isinstance(c, (int, np.integer)) else c for c in mt.columns]
    st.subheader("Monthly returns")
    st.dataframe(mt.style.format("{:.1%}", na_rep="").background_gradient(cmap="RdYlGn", vmin=-0.1, vmax=0.1), width="stretch")
    c1, c2 = st.columns(2)
    yr = (1 + net.fillna(0)).groupby(net.index.year).prod() - 1
    c1.plotly_chart(fig_layout(go.Figure(go.Bar(x=yr.index.astype(str), y=yr, marker_color=np.where(yr >= 0, "#2e8b57", "#c0392b"))), 300, "year return")
                    .update_yaxes(tickformat=".0%"), width="stretch")
    m = (1 + net.fillna(0)).resample("ME").prod() - 1
    c2.plotly_chart(fig_layout(go.Figure(go.Histogram(x=m, nbinsx=40)), 300, "count of months").update_xaxes(tickformat=".0%"), width="stretch")
    rs = A.rolling_sharpe(res["bars"]["net"], ppy, 365, bpd).loc[sl]
    st.plotly_chart(fig_layout(go.Figure(go.Scatter(x=rs.index, y=rs, name="rolling 1-year Sharpe")), 280, "rolling 1y Sharpe")
                    .add_hline(y=0, line_color="gray"), width="stretch")

# ------------------------------------------------------------------ Edge check
with tabs[2]:
    st.markdown("Is the edge real, or luck from testing many ideas? Tune only on **in-sample** data; the **out-of-sample** row is the honest one.")
    a, b = A.split_stats(net, ppy, pd.Timestamp(split))
    rows = {"In-sample (before split)": a, "Out-of-sample (after split)": b}
    st.dataframe(pd.DataFrame({k: {m: v.get(m, np.nan) for m in ("Sharpe", "CAGR", "Max drawdown", "Positive months", "Years")} for k, v in rows.items()}).T
                 .style.format({"Sharpe": "{:.2f}", "CAGR": "{:.1%}", "Max drawdown": "{:.1%}", "Positive months": "{:.0%}", "Years": "{:.1f}"}),
                 width="stretch")
    c1, c2, c3 = st.columns(3)
    ci, boot = A.bootstrap_sharpe(net, ppy, n=1000)
    c1.metric("Sharpe 95% range (bootstrap)", f"{ci[0]:.2f} … {ci[2]:.2f}")
    c2.metric("Probability Sharpe > 0 (PSR)", PCT(A.psr(net, ppy)))
    c3.metric(f"Deflated Sharpe ({int(n_trials)} trials)", PCT(A.dsr(net, ppy, int(n_trials))),
              help=">95% = unlikely to be the luckiest of your trials. Below 50% = probably noise.")
    with st.expander("Random-timing test (does the WHEN matter?)", expanded=False):
        if st.button("Run 300 random-timing paths", key="rt"):
            held = res["held"].loc[sl]; ret = bars.close.pct_change(fill_method=None).fillna(0).loc[sl]
            p, sr = A.random_timing_pvalue(held, ret, ppy)
            st.write(f"Real gross Sharpe {sr:.2f}; share of shuffled-timing paths doing at least as well: **{p:.1%}** "
                     f"({'timing carries information' if p < 0.05 else 'could be exposure / luck'}).")
    st.subheader("Parameter sensitivity")
    numeric = [k_ for k_, p in strat.params.items() if not isinstance(p.default, bool) and not p.choices]
    if numeric:
        pk = st.selectbox("Parameter to vary", numeric, key="sweep_p")
        pdef = strat.params[pk]
        lo_, hi_ = st.slider("Range", float(pdef.min), float(pdef.max), (float(pdef.min), float(min(pdef.max, pdef.default * 3))), key="sweep_r")
        nsteps = st.slider("Steps", 3, 15, 7, key="sweep_n")
        if st.button("Run sweep", key="sweep_go"):
            vals = np.linspace(lo_, hi_, nsteps)
            vals = np.unique(np.round(vals).astype(int)) if isinstance(pdef.default, int) else vals
            out = []
            for v in vals:
                pp = dict(params); pp[pk] = type(pdef.default)(v)
                r_, _ = backtest(bars, (bars_key, tf, tuple(syms)), sname, tuple(sorted(pp.items())), tuple(sorted(vars(cfg).items())))
                x = r_["bars"]["net"].loc[sl]; ia, ib = A.split_stats(x, ppy, pd.Timestamp(split))
                out.append((v, ia.get("Sharpe", np.nan), ib.get("Sharpe", np.nan)))
            st.session_state.trials.update({("sweep", sname, pk, float(v)) for v in vals})
            o = pd.DataFrame(out, columns=[pk, "in-sample Sharpe", "out-of-sample Sharpe"])
            f = go.Figure([go.Scatter(x=o[pk], y=o["in-sample Sharpe"], name="in-sample", mode="lines+markers"),
                           go.Scatter(x=o[pk], y=o["out-of-sample Sharpe"], name="out-of-sample", mode="lines+markers")])
            st.plotly_chart(fig_layout(f, 300, "Sharpe"), width="stretch")
            st.caption("A real edge shows a broad plateau, not one sharp peak. These runs were added to the trial count.")
    else:
        st.caption("This strategy has no numeric parameters.")

# ------------------------------------------------------------------ Assets & trades
with tabs[3]:
    info = res.get("info")
    if isinstance(info, pd.DataFrame) and len(info):
        with st.expander("Strategy details (what the strategy chose / learnt, per window)", expanded=True):
            st.dataframe(info, width="stretch", height=min(400, 40 + 35 * len(info)))
    ap = res["asset_pnl"].loc[sl].sum().sort_values()
    st.plotly_chart(fig_layout(go.Figure(go.Bar(x=ap.values, y=ap.index, orientation="h")), 320, None)
                    .update_xaxes(tickformat=".0%", title="sum of daily contributions (after costs)"), width="stretch")
    tr = EN.trades(res["held"].loc[sl], bars.close.loc[sl])
    if len(tr):
        wins = tr[tr.pnl_contribution > 0]; losses = tr[tr.pnl_contribution <= 0]
        c = st.columns(5)
        c[0].metric("Trades", f"{len(tr):,}"); c[1].metric("Win rate", PCT(len(wins) / len(tr)))
        c[2].metric("Profit factor", NUM(wins.pnl_contribution.sum() / -losses.pnl_contribution.sum() if len(losses) and losses.pnl_contribution.sum() < 0 else np.nan))
        c[3].metric("Avg win / avg loss", NUM(wins.pnl_contribution.mean() / -losses.pnl_contribution.mean() if len(losses) and len(wins) else np.nan))
        c[4].metric("Avg holding (bars)", f"{tr.bars.mean():.1f}")
        st.dataframe(tr.sort_values("entry", ascending=False).style.format({"pnl_contribution": "{:.3%}"}), width="stretch", height=320)

# ------------------------------------------------------------------ Prop firm
with tabs[4]:
    st.markdown("Crypto Fund Trader rules on this strategy's **daily** results (equity-based daily loss from start-of-day equity, "
                "intraday lows included). Rules from third-party trackers - check them at checkout.")
    prog_name = st.selectbox("Program", list(A.PROGRAMS), key="prog")
    prog = A.PROGRAMS[prog_name]
    c1, c2, c3 = st.columns(3)
    sc_c = c1.number_input("Risk multiplier in the challenge", 0.1, 5.0, 1.0, 0.1, key="scc", help="× the backtest's leverage")
    st_mult_note = c1.caption("1.0 = trade the challenge exactly as backtested")
    acc = c2.number_input("Account size (USD)", 5000, 400000, 100000, 5000, key="acc")
    fee = c3.number_input("Challenge fee (USD)", 0, 5000, 798, 10, key="fee")
    att = A.prop_attempts(dd_, prog, sc_c)
    cc = st.columns(5)
    cc[0].metric("Pass per attempt", PCT(att["P_pass"])); cc[1].metric("Fail: daily loss", PCT(att["P_fail_daily"]))
    cc[2].metric("Fail: max loss", PCT(att["P_fail_max"])); cc[3].metric("Not decided in 18 months", PCT(att["P_unresolved"]))
    cc[4].metric("Median days to pass", "—" if att["median_days_to_pass"] is None else f"{att['median_days_to_pass']:.0f}")
    st.subheader("Buying challenges until funded (2-year pipeline)")
    st.caption("Re-buy after a failed challenge; once funded, trade the funded account (often at lower risk), take payouts every "
               "30 days (80% split, 5% payout fee), re-buy after a funded breach. Starts every 5 days across your date range.")
    c1, c2, c3 = st.columns(3)
    budget = c1.slider("Max. challenges you will buy", 1, 15, 5, key="budget")
    sc_f = c2.number_input("Risk multiplier when funded", 0.05, 5.0, 0.4, 0.05, key="scf", help="research: funded at ~40% of challenge risk")
    if c3.button("Run pipeline", key="pipe"):
        pl = A.prop_pipeline(dd_, dd_, prog, sc_c, sc_f, acc, fee, budget)
        m = st.columns(7)
        m[0].metric("Get funded", PCT(pl["P_funded"])); m[1].metric("Challenges bought", f"{pl['bought']:.1f}")
        m[2].metric("Fees (avg)", USD(pl["fees"])); m[3].metric("Payouts (avg)", USD(pl["paid"]))
        m[4].metric("Net (average)", USD(pl["net_mean"])); m[5].metric("Net (typical)", USD(pl["net_p50"]))
        m[6].metric("Chance of profit", PCT(pl["P_profit"]))
        cv = pl["curve"]; x = np.arange(len(cv)) / 30.4
        f = go.Figure([go.Scatter(x=x, y=cv.p90, line=dict(width=0), showlegend=False),
                       go.Scatter(x=x, y=cv.p10, fill="tonexty", line=dict(width=0), name="unlucky 10% … lucky 10%"),
                       go.Scatter(x=x, y=cv.p50, name="typical", line=dict(width=2)), go.Scatter(x=x, y=cv["mean"], name="average", line=dict(dash="dash"))])
        st.plotly_chart(fig_layout(f, 360, "cash (USD)").update_xaxes(title="months"), width="stretch")
        st.caption(f"{pl['n']} start dates. Several challenges bought at the SAME time trade the same signals and pass or fail together.")

# ------------------------------------------------------------------ Compare
with tabs[5]:
    picks = st.multiselect("Strategies (default parameters, same data and costs)", list(reg), default=[n for n in list(reg)[:3]], key="cmp")
    if picks:
        rows, f = {}, go.Figure()
        for nme in picks:
            stc = reg[nme]()
            r_, _ = backtest(bars, (bars_key, tf, tuple(syms)), nme, tuple(sorted(stc.defaults().items())), tuple(sorted(vars(cfg).items())))
            x = r_["bars"]["net"].loc[sl]; s_ = A.summary(x, ppy); ia, ib = A.split_stats(x, ppy, pd.Timestamp(split))
            rows[nme] = {"Sharpe": s_.get("Sharpe"), "CAGR": s_.get("CAGR"), "Max drawdown": s_.get("Max drawdown"),
                         "Positive months": s_.get("Positive months"), "Sharpe in-sample": ia.get("Sharpe"), "Sharpe out-of-sample": ib.get("Sharpe")}
            f.add_scatter(x=x.index, y=(1 + x.fillna(0)).cumprod(), name=nme)
        st.dataframe(pd.DataFrame(rows).T.style.format({"Sharpe": "{:.2f}", "CAGR": "{:.1%}", "Max drawdown": "{:.1%}", "Positive months": "{:.0%}",
                                                        "Sharpe in-sample": "{:.2f}", "Sharpe out-of-sample": "{:.2f}"}), width="stretch")
        st.plotly_chart(fig_layout(f, 420, "growth of 1", True), width="stretch")

# ------------------------------------------------------------------ Export
with tabs[6]:
    out = res["bars"].loc[sl].copy(); out["equity"] = (1 + out["net"].fillna(0)).cumprod()
    st.download_button("Bar-by-bar results (CSV)", out.to_csv().encode(), "backtest_bars.csv", "text/csv")
    st.download_button("Daily results incl. intraday worst/best (CSV)", dd_.to_csv().encode(), "backtest_daily.csv", "text/csv")
    st.download_button("Positions / weights (CSV)", res["held"].loc[sl].to_csv().encode(), "backtest_positions.csv", "text/csv")
    st.download_button("Trades (CSV)", EN.trades(res["held"].loc[sl], bars.close.loc[sl]).to_csv(index=False).encode(), "backtest_trades.csv", "text/csv")
