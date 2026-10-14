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
from qpl.lab import analysis as A, data as D, engine as EN, propfirms as PF, scorecard as SC, strategies as S  # noqa: E402

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
default_syms = ([s for s in ("BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "AVAX", "DOT", "LINK") if s in bars_all.symbols]
                or (bars_all.symbols if ("curve" in choice or len(bars_all.symbols) <= 15) else bars_all.symbols[:10]))
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

TAB_NAMES = ["Scorecard", "Equity", "Returns", "Edge check", "Assets & trades", "Prop firm", "Compare strategies", "Export"]
T = dict(zip(TAB_NAMES, st.tabs(["Scorecard (all strategies)"] + TAB_NAMES[1:])))

# ------------------------------------------------------------------ Equity
with T["Equity"]:
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
with T["Returns"]:
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
with T["Edge check"]:
    st.markdown("Is the edge real, or luck from testing many ideas? Tune only on **in-sample** data; the **out-of-sample** row is the honest one.")
    a, b = A.split_stats(net, ppy, pd.Timestamp(split))
    rows = {"In-sample (before split)": a, "Out-of-sample (after split)": b}
    st.dataframe(pd.DataFrame({k: {m: v.get(m, np.nan) for m in ("Sharpe", "CAGR", "Max drawdown", "Positive months", "Years")} for k, v in rows.items()}).T
                 .style.format({"Sharpe": "{:.2f}", "CAGR": "{:.1%}", "Max drawdown": "{:.1%}", "Positive months": "{:.0%}", "Years": "{:.1f}"}),
                 width="stretch")
    c1, c2, c3 = st.columns(3)
    # intraday data: bootstrap the daily results (same Sharpe estimate, 100x fewer points to resample)
    bnet, bppy = (net, ppy) if bars.freq == "1d" else (dd_["net"], D.periods_per_year(dd_.index, "1d"))
    ci, boot = A.bootstrap_sharpe(bnet, bppy, n=1000)
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
with T["Assets & trades"]:
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
def firm_controls(prefix: str):
    """Prop-firm preset + every rule editable. Returns (Firm, budget, accounts, risk_challenge, risk_funded, horizon_days)."""
    c1, c2 = st.columns([2, 1])
    preset = c1.selectbox("Prop firm", list(PF.PRESETS), key=f"{prefix}_preset",
                          help="Presets approximate public rules (check them on the firm's site). Edit any rule below.")
    base = PF.PRESETS[preset]
    acc_ = c2.number_input("Account size (USD)", 5_000, 1_000_000, int(base.account), 5_000, key=f"{prefix}_acc_{preset}")
    if base.note:
        st.caption(base.note)
    with st.expander("Firm rules (edit)", expanded=preset == "Custom"):
        r1 = st.columns(4)
        fee_ = r1[0].number_input("Fee per challenge (USD)", 0.0, 10_000.0, float(base.fee), 10.0, key=f"{prefix}_fee_{preset}")
        fee_m = r1[1].checkbox("Fee is monthly (subscription)", base.fee_monthly, key=f"{prefix}_feem_{preset}")
        refund = r1[2].checkbox("Fee refunded with 1st payout", base.refund_fee, key=f"{prefix}_ref_{preset}")
        ffee = r1[3].number_input("Activation fee when funded", 0.0, 5_000.0, float(base.funded_fee), 10.0, key=f"{prefix}_ffee_{preset}")
        r2 = st.columns(4)
        tg = r2[0].text_input("Profit target(s) per phase, %", ", ".join(f"{t * 100:g}" for t in base.targets), key=f"{prefix}_tg_{preset}",
                              help="one number per phase, e.g. '8, 5' for a 2-phase challenge")
        mind = r2[1].number_input("Min. trading days per phase", 0, 60, int(base.min_days), 1, key=f"{prefix}_mind_{preset}")
        maxd = r2[2].number_input("Max. days per phase (0 = unlimited)", 0, 1000, int(base.max_days), 5, key=f"{prefix}_maxd_{preset}")
        spl = r2[3].number_input("Profit split %", 0.0, 100.0, base.split * 100, 5.0, key=f"{prefix}_spl_{preset}")
        r3 = st.columns(4)
        dl = r3[0].number_input("Daily loss limit % (0 = none)", 0.0, 20.0, base.daily_loss * 100, 0.5, key=f"{prefix}_dl_{preset}")
        dlb = r3[1].selectbox("Daily loss measured as", ["% of initial balance below start-of-day equity", "% of start-of-day equity"],
                              index=0 if base.daily_basis == "initial" else 1, key=f"{prefix}_dlb_{preset}")
        dli = r3[2].checkbox("Daily loss on intraday equity (lows)", base.daily_intraday, key=f"{prefix}_dli_{preset}")
        pe = r3[3].number_input("Payout every (days)", 1, 120, int(base.payout_every), 1, key=f"{prefix}_pe_{preset}")
        r4 = st.columns(4)
        ml = r4[0].number_input("Max loss %", 0.5, 50.0, base.max_loss * 100, 0.5, key=f"{prefix}_ml_{preset}")
        types = ["static", "trailing", "trailing_lock"]
        mt = r4[1].selectbox("Max loss type", types, index=types.index(base.max_type), key=f"{prefix}_mt_{preset}",
                             help="trailing_lock = trails the equity high but stops at the starting balance")
        ti = r4[2].checkbox("Trail from intraday highs", base.trailing_intraday, key=f"{prefix}_ti_{preset}", help="off = from end-of-day equity")
        pf_ = r4[3].number_input("Payout fee %", 0.0, 20.0, base.payout_fee * 100, 0.5, key=f"{prefix}_pf_{preset}")
    try:
        targets = tuple(float(x) / 100 for x in tg.replace(";", ",").split(",") if x.strip())
    except ValueError:
        st.error("Profit targets: use numbers like '8, 5'"); targets = base.targets
    firm = PF.Firm(base.name, float(acc_), fee_, targets or base.targets, dl / 100, "initial" if dlb.startswith("% of initial") else "day_start",
                   dli, ml / 100, mt, ti, int(mind), int(maxd), spl / 100, int(pe), pf_ / 100, refund, ffee, base.note, fee_m)
    c = st.columns(5)
    budget_ = c[0].number_input("Max. challenges you will buy", 1, 50, 5, 1, key=f"{prefix}_budget",
                                help="re-buy after a failed challenge or a lost funded account, up to this many in total")
    accounts_ = c[1].number_input("Accounts in parallel", 1, 20, 1, 1, key=f"{prefix}_accts",
                                  help="identical accounts trading the same signals: they pass and fail together, money is multiplied")
    sc_c_ = c[2].number_input("Risk in challenge (× backtest)", 0.1, 5.0, 1.0, 0.1, key=f"{prefix}_scc")
    sc_f_ = c[3].number_input("Risk when funded (× backtest)", 0.05, 5.0, 0.4, 0.05, key=f"{prefix}_scf",
                              help="research: funded at ~40% of challenge risk keeps the account alive longer")
    hz = c[4].number_input("Horizon (months)", 3, 60, 24, 1, key=f"{prefix}_hz")
    return firm, int(budget_), int(accounts_), sc_c_, sc_f_, int(hz * 30.4)


with T["Prop firm"]:
    st.markdown("How likely is this strategy to pass a prop-firm challenge, and what does it earn after fees? Uses the **daily** "
                "results including intraday lows and highs (equity-based limits). Each start date in your range is one simulated trader.")
    firm, budget, accounts, sc_c, sc_f, horizon = firm_controls("pf")
    method = st.radio("Paths", ["every historical start date", "bootstrap 500 paths (for short data)"], horizontal=True, key="pf_method")
    meth = "historical" if method.startswith("every") else "bootstrap"
    att = PF.attempts(dd_, firm, sc_c, method=meth)
    st.subheader("One challenge attempt")
    cc = st.columns(6)
    cc[0].metric("Pass", PCT(att["P_pass"])); cc[1].metric("Fail: daily loss", PCT(att["P_fail_daily"]))
    cc[2].metric("Fail: max loss", PCT(att["P_fail_max"])); cc[3].metric("Fail: time limit", PCT(att["P_fail_time"]))
    cc[4].metric("Not finished (18 months)", PCT(att["P_open"]))
    cc[5].metric("Median days to pass", "—" if np.isnan(att["median_days_to_pass"]) else f"{att['median_days_to_pass']:.0f}")
    st.subheader(f"Buying up to {budget} challenge(s), {accounts} account(s) in parallel, over {horizon // 30} months")
    pl = PF.pipeline(dd_, firm, budget, accounts, sc_c, sc_f, horizon_days=horizon, method=meth)
    if pl.get("n", 0) < 50 and meth == "historical":
        st.info(f"Only {pl.get('n', 0)} start dates have {horizon // 30} months of data after them: using 500 bootstrapped paths instead.")
        pl = PF.pipeline(dd_, firm, budget, accounts, sc_c, sc_f, horizon_days=horizon, method="bootstrap")
    if not pl.get("n"):
        st.warning("Not enough data for this horizon.")
    else:
        m = st.columns(6)
        m[0].metric("Get funded", PCT(pl["P_funded"])); m[1].metric("Get at least one payout", PCT(pl["P_payout"]))
        m[2].metric("Challenges bought (avg)", f"{pl['bought']:.1f}"); m[3].metric("Fees paid (avg)", USD(pl["fees"]))
        m[4].metric("Payouts received (avg)", USD(pl["paid"])); m[5].metric("Chance of profit", PCT(pl["P_profit"]))
        m = st.columns(6)
        m[0].metric("Net (average)", USD(pl["net_mean"])); m[1].metric("Net (typical)", USD(pl["net_p50"]))
        m[2].metric("Net (unlucky 10%)", USD(pl["net_p10"])); m[3].metric("Net (lucky 10%)", USD(pl["net_p90"]))
        m[4].metric("Net per month (avg)", USD(pl["net_per_month"]))
        m[5].metric("Median days to funded", "—" if np.isnan(pl["days_to_funded_median"]) else f"{pl['days_to_funded_median']:.0f}")
        cv = pl["curve"]; x = np.arange(len(cv)) / pl["per_day"] / 30.4
        f = go.Figure([go.Scatter(x=x, y=cv.p90, line=dict(width=0), showlegend=False),
                       go.Scatter(x=x, y=cv.p10, fill="tonexty", line=dict(width=0), name="unlucky 10% … lucky 10%"),
                       go.Scatter(x=x, y=cv.p50, name="typical", line=dict(width=2)), go.Scatter(x=x, y=cv["mean"], name="average", line=dict(dash="dash"))])
        st.plotly_chart(fig_layout(f, 340, "cash in your pocket (USD)").update_xaxes(title="months"), width="stretch")
        st.caption(f"{pl['n']} simulated traders. Fees are paid when a challenge is bought, payouts every {firm.payout_every} days "
                   f"({firm.split:.0%} split). Parallel accounts trade the same signals, so they do NOT spread the risk.")
        with st.expander("How many challenges should I budget for?"):
            rows = []
            for bgt in (1, 2, 3, 5, 8, 12):
                q = PF.pipeline(dd_, firm, bgt, accounts, sc_c, sc_f, horizon_days=horizon, method=meth)
                rows.append({"Budget": bgt, "Get funded": q["P_funded"], "Fees (avg)": q["fees"], "Net (avg)": q["net_mean"],
                             "Net (typical)": q["net_p50"], "Chance of profit": q["P_profit"]})
            st.dataframe(pd.DataFrame(rows).set_index("Budget").style.format({"Get funded": "{:.0%}", "Fees (avg)": "${:,.0f}", "Net (avg)": "${:,.0f}",
                                                                               "Net (typical)": "${:,.0f}", "Chance of profit": "{:.0%}"}), width="stretch")
    st.caption("Not modelled: consistency rules, news-trading bans, weekend holding rules, scaling plans, rule changes. Check the firm's current rules.")


# ------------------------------------------------------------------ Scorecard
@st.cache_data(show_spinner=False)
def scorecard_row(strat_name: str, setup_key: str, setup_t: tuple, n_trials: int):
    sources_ = D.list_sources(); setup = dict(setup_t); setup["sources"] = list(setup["sources"]); setup["symbols"] = list(setup["symbols"])
    src = SC.resolve(setup, sources_)
    if src is None:
        return None, f"data not found ({setup['sources'][-1]}); run python -m qpl.lab.setup_data"
    b = sources_[src]()
    sel = b.select([s_ for s_ in setup["symbols"] if s_ in b.symbols] or b.symbols)
    sel.extra = {k_: (v_.reindex(columns=sel.symbols) if isinstance(v_, pd.DataFrame) else v_) for k_, v_ in b.extra.items()}
    b = D.resample(sel, setup["tf"])
    reg_, _ = S.registry()
    out = SC.run(reg_[strat_name], b, setup)
    return out, src


with T["Scorecard"]:
    st.markdown("**Every strategy on its own market**, with default settings: one row of statistics each, plus the prop-firm outcome "
                "for the firm chosen below. Your own plug-ins run on the data selected in the sidebar.")
    sc_firm, sc_budget, sc_accounts, sc_scc, sc_scf, sc_hz = firm_controls("sc")
    pick = st.multiselect("Strategies", list(reg), default=list(reg), key="sc_pick")
    if st.button("Build scorecard", key="sc_go", type="primary"):
        rows, prop_rows, curves = {}, {}, go.Figure()
        prog = st.progress(0.0)
        for i, nme in enumerate(pick):
            prog.progress((i + 0.5) / len(pick), text=f"{nme} ...")
            setup = SC.SETUPS.get(nme)
            try:
                if setup is None:
                    setup = dict(sources=[], symbols=list(syms), tf=tf, cost=cost, lev=lev, start=str(start), market=f"sidebar: {choice}")
                    o = SC.run(reg[nme], bars, setup); src_ = choice
                else:
                    o, src_ = scorecard_row(nme, nme, tuple((k_, tuple(v) if isinstance(v, list) else v) for k_, v in setup.items()), int(n_trials))
                if o is None:
                    rows[nme] = {"Market": setup["market"], "Data": src_}; continue
                rows[nme] = {"Market": setup["market"], "Cost bp": setup["cost"], "Leverage": setup["lev"], **SC.stats(o, int(n_trials))}
                prop_rows[nme] = SC.prop(o, sc_firm, sc_budget, sc_accounts, sc_scc, sc_scf, sc_hz)
                eq = (1 + o["daily"]["net"]).cumprod()
                curves.add_scatter(x=eq.index, y=eq, name=nme)
            except Exception as e:  # keep building the other rows
                rows[nme] = {"Market": (setup or {}).get("market", ""), "Data": f"error: {e}"}
        prog.empty()
        st.session_state["scorecard"] = (pd.DataFrame(rows).T, pd.DataFrame(prop_rows).T, curves, sc_firm.name, sc_budget, sc_accounts)
    if "scorecard" in st.session_state:
        tbl, ptbl, curves, fname, bgt, nacc = st.session_state["scorecard"]
        st.subheader("Performance (after costs)")
        fmt = {k_: "{:.2f}" for k_ in ("Sharpe", "Calmar", "Sortino", "Profit factor", "Years", "Leverage", "Cost bp")}
        fmt.update({k_: "{:.1%}" for k_ in ("CAGR", "Volatility", "Max drawdown", "Avg month", "Worst month", "Best month", "Worst day (intraday)")})
        fmt.update({k_: "{:.0%}" for k_ in ("Positive months", "Win rate", "Prob. Sharpe > 0") + tuple(c_ for c_ in tbl.columns if c_.startswith("Deflated"))})
        fmt["Trades / year"] = "{:.0f}"
        st.dataframe(tbl.style.format({k_: v for k_, v in fmt.items() if k_ in tbl.columns}, na_rep="—"), width="stretch")
        if len(ptbl):
            st.subheader(f"Prop firm: {fname}, up to {bgt} challenge(s), {nacc} account(s)")
            pf_fmt = {k_: "{:.0%}" for k_ in ptbl.columns if k_.startswith(("Pass", "Fail", "Funded", "Chance"))}
            pf_fmt.update({k_: "${:,.0f}" for k_ in ptbl.columns if k_.startswith(("Fees", "Payouts", "Net"))})
            pf_fmt.update({"Median days to pass": "{:.0f}", "Challenges bought (avg)": "{:.1f}"})
            st.dataframe(ptbl.style.format({k_: v for k_, v in pf_fmt.items() if k_ in ptbl.columns}, na_rep="—"), width="stretch")
        st.plotly_chart(fig_layout(curves, 420, "growth of 1 (log)", True), width="stretch")
        st.download_button("Scorecard (CSV)", tbl.join(ptbl).to_csv().encode(), "scorecard.csv", "text/csv")
        st.caption("Different strategies use different markets and periods, so compare Sharpe / drawdown / prop odds, not total return. "
                   "Deflated Sharpe uses the trial count from the sidebar. Short data (e.g. 3 years) gives wide uncertainty.")

# ------------------------------------------------------------------ Compare
with T["Compare strategies"]:
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
with T["Export"]:
    out = res["bars"].loc[sl].copy(); out["equity"] = (1 + out["net"].fillna(0)).cumprod()
    st.download_button("Bar-by-bar results (CSV)", out.to_csv().encode(), "backtest_bars.csv", "text/csv")
    st.download_button("Daily results incl. intraday worst/best (CSV)", dd_.to_csv().encode(), "backtest_daily.csv", "text/csv")
    st.download_button("Positions / weights (CSV)", res["held"].loc[sl].to_csv().encode(), "backtest_positions.csv", "text/csv")
    st.download_button("Trades (CSV)", EN.trades(res["held"].loc[sl], bars.close.loc[sl]).to_csv(index=False).encode(), "backtest_trades.csv", "text/csv")
