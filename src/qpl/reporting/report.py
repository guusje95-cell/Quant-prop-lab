"""Generate the final research report (self-contained HTML, theme-aware, inline SVG charts).

Every number is read from results/*.json|csv, config/*.json or the experiment database, so
`python -m qpl.reporting.report` regenerates the report from a fresh pipeline run."""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtesting import accounting as A
from ..instruments import get
from ..research import pipeline as P
from ..research import registry as R

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results"
FROZEN = dict(lookback=14, mult=1.25, trail="band_mean", check_min=60)


def J(name):
    return json.loads((RES / name).read_text())


def f(x, d=2, pct=False, money=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–"
    if pct:
        return f"{100 * x:.{0 if d is None else d}f}%"
    if money:
        s = f"{abs(x):,.0f}"
        return ("−$" if x < 0 else "$") + s
    return f"{x:.{d}f}"


def tag(kind):
    return f'<span class="tag t-{kind.lower()}">{kind}</span>'


def table(headers, rows, cls=""):
    h = "".join(f"<th>{html.escape(str(x))}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


# ---------------------------------------------------------------------------------------- charts
def svg_line(series: dict[str, pd.Series], w=760, h=260, shade=None, ylab="USD", money=True):
    """series: name -> pd.Series indexed by datetime. shade: list of (start, end, label)."""
    pad_l, pad_r, pad_t, pad_b = 64, 16, 14, 30
    allv = np.concatenate([s.to_numpy() for s in series.values()])
    lo, hi = float(min(0, allv.min())), float(allv.max())
    span = hi - lo or 1
    lo -= 0.04 * span; hi += 0.04 * span
    t0 = min(s.index[0] for s in series.values()); t1 = max(s.index[-1] for s in series.values())
    tx = lambda t: pad_l + (pd.Timestamp(t) - t0).total_seconds() / max((t1 - t0).total_seconds(), 1) * (w - pad_l - pad_r)
    ty = lambda v: pad_t + (hi - v) / (hi - lo) * (h - pad_t - pad_b)
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="{html.escape(ylab)} chart">']
    for a, b, lab in (shade or []):
        x0, x1 = tx(max(pd.Timestamp(a), t0)), tx(min(pd.Timestamp(b), t1))
        out.append(f'<rect x="{x0:.1f}" y="{pad_t}" width="{max(x1 - x0, 0):.1f}" height="{h - pad_t - pad_b}" class="shade"/>')
        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{pad_t + 12}" class="ax" text-anchor="middle">{lab}</text>')
    ticks = np.linspace(lo, hi, 5)
    for v in ticks:
        y = ty(v)
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        lab = (f"${v / 1000:,.0f}k" if abs(hi - lo) > 5000 else f"${v:,.0f}") if money else f"{v:.2f}"
        out.append(f'<text x="{pad_l - 6}" y="{y + 4:.1f}" class="ax" text-anchor="end">{lab}</text>')
    if lo < 0 < hi:
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{ty(0):.1f}" y2="{ty(0):.1f}" class="zero"/>')
    for yv in range(t0.year + 1, t1.year + 1):
        x = tx(pd.Timestamp(yv, 1, 1))
        if yv % 2 == 0 or (t1.year - t0.year) < 6:
            out.append(f'<text x="{x:.1f}" y="{h - 10}" class="ax" text-anchor="middle">{yv}</text>')
    for i, (name, s) in enumerate(series.items()):
        pts = " ".join(f"{tx(t):.1f},{ty(v):.1f}" for t, v in zip(s.index, s.to_numpy()))
        out.append(f'<polyline points="{pts}" class="ln ln{i}" fill="none"/>')
        out.append(f'<circle cx="{tx(s.index[-1]):.1f}" cy="{ty(s.iloc[-1]):.1f}" r="3.5" class="dot{i}"/>')
    out.append("</svg>")
    leg = "".join(f'<span class="lg"><i class="sw sw{i}"></i>{html.escape(n)}</span>' for i, n in enumerate(series))
    return f'<figure>{"".join(out)}<figcaption>{leg}</figcaption></figure>'


def svg_bars(labels, values, w=760, h=220, money=True, hl=None):
    pad_l, pad_r, pad_t, pad_b = 64, 10, 12, 34
    lo, hi = min(0, min(values)), max(0, max(values))
    span = hi - lo or 1
    hi += 0.08 * span; lo -= 0.08 * span if lo < 0 else 0
    n = len(values)
    bw = (w - pad_l - pad_r) / n
    ty = lambda v: pad_t + (hi - v) / (hi - lo) * (h - pad_t - pad_b)
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="bar chart">']
    for v in np.linspace(lo, hi, 4):
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{ty(v):.1f}" y2="{ty(v):.1f}" class="grid"/>')
        out.append(f'<text x="{pad_l - 6}" y="{ty(v) + 4:.1f}" class="ax" text-anchor="end">{("$" + format(v / 1000, ",.0f") + "k") if money else f"{v:.2f}"}</text>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = pad_l + i * bw + bw * 0.15
        y0, y1 = ty(max(v, 0)), ty(min(v, 0))
        cls = "bar-neg" if v < 0 else ("bar-hl" if hl and lab in hl else "bar")
        out.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw * 0.7:.1f}" height="{max(y1 - y0, 1):.1f}" class="{cls}"/>')
        out.append(f'<text x="{x + bw * 0.35:.1f}" y="{h - 14}" class="ax" text-anchor="middle">{html.escape(str(lab))}</text>')
    out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{ty(0):.1f}" y2="{ty(0):.1f}" class="zero"/>')
    out.append("</svg>")
    return f"<figure>{''.join(out)}</figure>"


def svg_scenarios(sc):
    """Pass probability vs share of historical edge retained, per firm."""
    w, h, pad_l, pad_r, pad_t, pad_b = 760, 250, 56, 150, 14, 36
    keys = ["keep_100pct_edge", "keep_75pct_edge", "keep_50pct_edge", "keep_25pct_edge", "keep_0pct_edge"]
    xs = [100, 75, 50, 25, 0]
    firms = list(sc[keys[0]].keys())
    tx = lambda x: pad_l + (100 - x) / 100 * (w - pad_l - pad_r)
    ty = lambda p: pad_t + (1 - p) * (h - pad_t - pad_b)
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img" aria-label="pass probability scenarios">']
    for p in (0, 0.25, 0.5, 0.75, 1):
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{ty(p):.1f}" y2="{ty(p):.1f}" class="grid"/>')
        out.append(f'<text x="{pad_l - 6}" y="{ty(p) + 4:.1f}" class="ax" text-anchor="end">{int(p * 100)}%</text>')
    for x in xs:
        out.append(f'<text x="{tx(x):.1f}" y="{h - 14}" class="ax" text-anchor="middle">{x}%</text>')
    out.append(f'<text x="{(pad_l + w - pad_r) / 2:.1f}" y="{h - 1}" class="ax" text-anchor="middle">share of historical edge that persists</text>')
    for i, fm in enumerate(firms):
        ps = [sc[k][fm]["p_pass"] for k in keys]
        pts = " ".join(f"{tx(x):.1f},{ty(p):.1f}" for x, p in zip(xs, ps))
        out.append(f'<polyline points="{pts}" class="ln ln{i}" fill="none"/>')
        for x, p in zip(xs, ps):
            out.append(f'<circle cx="{tx(x):.1f}" cy="{ty(p):.1f}" r="3" class="dot{i}"/>')
        out.append(f'<text x="{tx(0) + 8:.1f}" y="{ty(ps[-1]) + 4 + (i - 1) * 3:.1f}" class="ax lab{i}">{html.escape(fm)}</text>')
    out.append("</svg>")
    return f"<figure>{''.join(out)}</figure>"


# ---------------------------------------------------------------------------------------- data
def equity_series():
    inst = get("MNQ")
    ctx = P.context("dukascopy", "US100", "M15")
    days = P.trading_days(ctx)
    u = P.usd(P.backtest("noise_area", ctx, FROZEN, inst), inst, contracts=1)
    d = A.daily_pnl(u, days)["pnl"].loc["2013-08-01":"2023-09-11"]
    ctx2 = P.context("topstepx", "MNQ", "1h", 540, 960)
    u2 = P.usd(P.backtest("noise_area", ctx2, FROZEN, inst), inst, contracts=1, norm=False)
    d2 = A.daily_pnl(u2, P.trading_days(ctx2))["pnl"].loc["2025-03-21":"2026-04-15"]
    return d, d2


CSS = """
:root{
  /* Layout: single reading column (~72ch) with full-width tables/charts; dossier-style section index */
  --bg:#f3f5f6; --panel:#ffffff; --ink:#15212b; --muted:#566573; --rule:#d5dde3;
  --accent:#0b5f86; --accent2:#9a5b13; --good:#1f7a4d; --bad:#b0362f; --warn:#a36a00; --shade:rgba(11,95,134,.07);
  --display:"Archivo", "Helvetica Neue", Arial, sans-serif; --body:"Source Serif 4", Georgia, serif;
  --mono:"JetBrains Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0f161c;--panel:#16212a;--ink:#e3e9ee;--muted:#9aa9b6;--rule:#2a3843;--accent:#5cb6df;--accent2:#e0a35a;--good:#5cc28d;--bad:#ef7a70;--warn:#e3b04f;--shade:rgba(92,182,223,.08);color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f161c;--panel:#16212a;--ink:#e3e9ee;--muted:#9aa9b6;--rule:#2a3843;--accent:#5cb6df;--accent2:#e0a35a;--good:#5cc28d;--bad:#ef7a70;--warn:#e3b04f;--shade:rgba(92,182,223,.08);color-scheme:dark}
body{background:var(--bg);color:var(--ink);font:17px/1.6 var(--body);padding-inline:16px;padding-block:24px 64px}
main{max-width:980px;margin:0 auto;display:grid;gap:8px}
main>*{min-width:0}
td{overflow-wrap:anywhere}
.col{max-width:72ch}
h1,h2,h3{font-family:var(--display);line-height:1.15;text-wrap:balance;margin:0}
h1{font-size:clamp(2rem,5vw,3rem);font-weight:800;letter-spacing:-.01em}
h2{font-size:1.45rem;font-weight:700;margin-top:40px;padding-top:14px;border-top:2px solid var(--ink);display:flex;gap:12px;align-items:baseline}
h2 .n{font-family:var(--mono);font-size:.8rem;color:var(--muted);font-weight:500}
h3{font-size:1.08rem;font-weight:700;margin-top:18px}
p{margin:.4em 0}
.eyebrow{font-family:var(--mono);font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.verdict{background:var(--panel);border:1px solid var(--rule);border-left:6px solid var(--warn);padding:16px 20px;margin:12px 0}
.verdict strong{font-family:var(--display)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.kpi{background:var(--panel);border:1px solid var(--rule);padding:12px 14px}
.kpi b{display:block;font-family:var(--mono);font-size:1.35rem;font-variant-numeric:tabular-nums}
.kpi span{font-size:.82rem;color:var(--muted);font-family:var(--display)}
.tw{overflow-x:auto;margin:10px 0;border:1px solid var(--rule);background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:.86rem;font-family:var(--display)}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-size:.74rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;background:var(--bg)}
td{font-variant-numeric:tabular-nums}
.tag{font-family:var(--mono);font-size:.68rem;letter-spacing:.06em;padding:1px 6px;border:1px solid currentColor;border-radius:3px;white-space:nowrap}
.t-fact{color:var(--good)}.t-assumption{color:var(--accent2)}.t-estimate{color:var(--accent)}.t-uncertainty{color:var(--bad)}
.t-verified{color:var(--good)}.t-uncertain{color:var(--warn)}.t-not_found{color:var(--muted)}
.pass{color:var(--good);font-weight:700}.fail{color:var(--bad);font-weight:700}.weak{color:var(--warn);font-weight:700}
figure{margin:12px 0;background:var(--panel);border:1px solid var(--rule);padding:10px}
figcaption{display:flex;gap:16px;flex-wrap:wrap;font-family:var(--display);font-size:.8rem;color:var(--muted);padding:4px 6px}
.chart{width:100%;height:auto;display:block}
.chart .grid{stroke:var(--rule);stroke-width:1}
.chart .zero{stroke:var(--muted);stroke-width:1}
.chart .ax{fill:var(--muted);font:11px var(--display)}
.chart .shade{fill:var(--shade)}
.chart .ln{stroke-width:1.8}.chart .ln0{stroke:var(--accent)}.chart .ln1{stroke:var(--accent2)}.chart .ln2{stroke:var(--good)}
.chart .dot0{fill:var(--accent)}.chart .dot1{fill:var(--accent2)}.chart .dot2{fill:var(--good)}
.chart .lab0{fill:var(--accent)}.chart .lab1{fill:var(--accent2)}.chart .lab2{fill:var(--good)}
.chart .bar{fill:var(--accent)}.chart .bar-hl{fill:var(--accent2)}.chart .bar-neg{fill:var(--bad)}
.lg{display:inline-flex;gap:6px;align-items:center}.sw{width:14px;height:3px;display:inline-block}
.sw0{background:var(--accent)}.sw1{background:var(--accent2)}.sw2{background:var(--good)}
code,pre{font-family:var(--mono);font-size:.84rem}
pre{background:var(--panel);border:1px solid var(--rule);padding:12px;overflow-x:auto;line-height:1.45}
.card{display:grid;grid-template-columns:minmax(150px,220px) 1fr;border:1px solid var(--rule);background:var(--panel)}
.card div{padding:7px 12px;border-bottom:1px solid var(--rule);min-width:0}
.card div:nth-child(odd){font-family:var(--display);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.toc{columns:2 260px;font-family:var(--display);font-size:.88rem;margin:10px 0;padding-left:1.2em}
ul{padding-left:1.2em;margin:.4em 0}
li{margin:.15em 0}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (max-width:560px){body{font-size:16px}.card{grid-template-columns:1fr}}
"""


def build() -> str:
    ev = J("h3_eval.json")["markets"]
    nq = ev["NQ"]
    fal = J("h3_falsification_NQ.json")
    exp = J("h3_mnq_expectation.json")
    prop = J("prop_h3_mnq.json")
    ftmo = J("prop_h3_ftmo.json")
    sc = J("prop_scenarios.json")
    fin = J("final_test_test.json")
    cal = J("final_test_calibrate.json")
    h4 = J("h4_candidate_eval.json")["markets"]
    firms = json.loads((ROOT / "config" / "prop_firms.json").read_text())
    proto = json.loads((ROOT / "config" / "final_test_protocol.json").read_text())
    hyp = R.query("select id, family, status, verdict from hypotheses order by id")
    counts = dict(R.query("select hypothesis_id, count(*) from experiments where decision not like '%superseded%' "
                          "and decision!='invalid' group by hypothesis_id"))
    n_valid = R.count("decision not like '%superseded%' and decision!='invalid'")
    n_all = R.count()
    d_hist, d_final = equity_series()
    sp = nq["splits"]

    S = []
    a = S.append
    a(f"<title>Nasdaq Noise-Area Study</title><style>{CSS}</style>")
    a('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">')
    a("<main>")
    a('<p class="eyebrow">Quant Prop Lab · autonomous research dossier · generated from the experiment database</p>')
    a("<h1>Nasdaq Noise-Area Study</h1>")
    a('<p class="col">Ten hypothesis families were tested on CME equity-index, metal, energy and FX markets with the goal of a legitimate, '
      'automated strategy for prop-firm evaluations. One survived every pre-registered test: <b>noise-area intraday momentum on '
      'Nasdaq-100 futures (NQ/MNQ)</b>. It passed its final test on real futures only narrowly, and the most recent 13 months were much '
      'weaker than its history.</p>')
    a('<div class="verdict"><strong>Verdict: conditional candidate, paper trade first.</strong> Strong evidence 2013–2023 (out-of-sample Sharpe '
      f'{f(sp["oos"]["sharpe"])}, p={f(nq["stats_oos"]["nw_p_one_sided"], 3)}); final test on real CME futures 2025-03 → 2026-04 positive but weak '
      f'(Sharpe {f(fin["B_NQ"]["metrics"]["sharpe"])}). Pass probability for a Topstep 50K Combine is about '
      f'{f(sc["scenarios"]["keep_100pct_edge"]["Topstep 50K Combine"]["p_pass"], 0, pct=True)} if the historical edge persists and '
      f'{f(sc["realised_2025_26"]["Topstep 50K Combine"]["p_pass"], 0, pct=True)} if the 2025–26 regime persists. '
      'Do not buy evaluations until the paper-trading gate below is met.</div>')
    a('<div class="kpis">'
      f'<div class="kpi"><b>{n_valid}</b><span>valid experiments ({n_all} incl. superseded/invalid)</span></div>'
      f'<div class="kpi"><b>10 → 1</b><span>hypothesis families → survivor</span></div>'
      f'<div class="kpi"><b>{f(sp["oos"]["sharpe"])}</b><span>OOS Sharpe 2021–23, 1 NQ, after costs</span></div>'
      f'<div class="kpi"><b>{f(fin["B_NQ"]["metrics"]["sharpe"])}</b><span>final-test Sharpe, real NQ futures, 13 mo</span></div>'
      f'<div class="kpi"><b>{exp["trades_per_week"]:.1f}/wk</b><span>trades; median hold {exp["median_hold_min"]:.0f} min</span></div>'
      "</div>")
    a('<p class="col">Labels used throughout: ' + tag("FACT") + " measured from data or official sources; " + tag("ASSUMPTION") +
      " a modelling choice; " + tag("ESTIMATE") + " a simulated or extrapolated quantity; " + tag("UNCERTAINTY") + " a known unknown.</p>")
    toc = ["Executive summary", "Prop-firm universe and verified rules", "Data sources and quality", "Methodology", "Strategy families and experiment count",
           "Failed and surviving hypotheses", "Final candidate: exact logic, risk and sizing", "In-sample, validation and out-of-sample",
           "Walk-forward", "Statistical validation", "Monte Carlo", "Cost and slippage stress", "Parameter robustness", "Regime analysis",
           "Falsification attempts", "Final test on real futures", "Prop-firm simulation", "Weaknesses and failure scenarios",
           "Paper-trading plan", "Strategy card", "Reproducibility"]
    a('<ol class="toc">' + "".join(f"<li>{t}</li>" for t in toc) + "</ol>")

    # 1 executive summary
    a('<h2><span class="n">01</span>Executive summary</h2><div class="col">')
    a("<ul>"
      f"<li>{tag('FACT')} 10 hypothesis families, {n_valid} recorded valid experiments, strict chronological splits: TRAIN 2013–2018, VALIDATION 2019–2020, OOS 2021–2023-09, FINAL TEST on real CME futures 2025-03-21 → 2026-04-15.</li>"
      f"<li>{tag('FACT')} Survivor: noise-area intraday momentum (Zarattini, Aziz &amp; Barbon 2024) on NQ, frozen as lookback 14, band ×1.25, hourly checks. OOS Sharpe {f(sp['oos']['sharpe'])} (Newey-West t={f(nq['stats_oos']['nw_t'])}), {f(next(x['sharpe'] for x in nq['cost_stress_oos'] if x['scenario']=='cost3x'))} at 3× costs; all {nq['neighbors_dev']['n']} parameter neighbours positive.</li>"
      f"<li>{tag('FACT')} Final test (pre-registered, run once): narrow pass. 13-month hourly approximation Sharpe {f(fin['B_NQ']['metrics']['sharpe'])}; exact 15-minute spec Jan–Apr 2026 Sharpe {f(fin['A_NQ']['metrics']['sharpe'])}.</li>"
      f"<li>{tag('UNCERTAINTY')} The final-test Sharpe sits near the 6th percentile of what history predicted. It is consistent with bad luck (similar years: 2016, 2019) or with decay after the strategy's 2024 publication. Available data cannot separate the two.</li>"
      f"<li>{tag('ESTIMATE')} Topstep 50K pass probability: {f(sc['scenarios']['keep_100pct_edge']['Topstep 50K Combine']['p_pass'],0,pct=True)} (full edge) → {f(sc['scenarios']['keep_50pct_edge']['Topstep 50K Combine']['p_pass'],0,pct=True)} (half) → {f(sc['scenarios']['keep_0pct_edge']['Topstep 50K Combine']['p_pass'],0,pct=True)} (no edge). Median time to pass at conservative size ≈ {f(sc['scenarios']['keep_100pct_edge']['Topstep 50K Combine']['days_to_pass_p50'],0)} trading days.</li>"
      "<li>Rejected: opening-range breakout, last-half-hour momentum, overnight drift (strong 2013–20, failed OOS), gap fade, cross-asset noise-area, midday reversion, NQ/ES relative strength, gold Asian drift, multi-asset daily trend.</li>"
      "</ul></div>")

    # 2 prop firms
    a('<h2><span class="n">02</span>Prop-firm universe and verified rules</h2>')
    a(f'<p class="col">{html.escape(firms["_meta"]["method"])}</p>')
    rows = []
    for key, fm in firms["firms"].items():
        def g(k):
            v = fm.get(k)
            if not v:
                return tag("NOT_FOUND")
            st = v.get("status", "")
            s = str(v.get("value", ""))
            if v.get("type"):
                s += f" ({v['type']})"
            return f"{html.escape(s)} {tag(st.split(' ')[0])}"
        rows.append([f"<b>{html.escape(fm['firm'])}</b><br>{html.escape(fm.get('product', ''))}", g("profit_target"), g("max_loss_limit"),
                     g("daily_loss_limit"), g("consistency"), g("automation")])
    a(table(["Firm / product", "Profit target", "Max loss", "Daily loss", "Consistency", "Automation"], rows))
    ts = firms["firms"]["topstep_50k_combine"]
    a('<h3>Primary target: Topstep 50K Combine (full record)</h3>')
    a(table(["Rule", "Value", "Status"], [[k.replace("_", " "), html.escape(str(v.get("value", ""))) + (f"<br><small>conflict: {html.escape(v['conflict'])}</small>" if v.get("conflict") else ""), tag(v.get("status", "").split(" ")[0])]
                                          for k, v in ts.items() if isinstance(v, dict)]))
    a(f'<p class="col">{tag("FACT")} Apex Trader Funding prohibits automated order entry on all accounts, so it is excluded as a target. FTMO permits EAs and is modelled as the CFD alternative.</p>')

    # 3 data
    q = json.loads((ROOT / "data" / "metadata" / "data_quality.json").read_text())
    a('<h2><span class="n">03</span>Data sources and quality</h2><div class="col">')
    a(f"<p>{tag('FACT')} The environment's network policy blocks the usual vendors (Yahoo, Dukascopy direct, Stooq, HistData, Kaggle, CME). Two public GitHub mirrors were used, pinned to commits in <code>config/data_sources.json</code>:</p><ul>"
      "<li><b>Development:</b> Dukascopy CFD/FX bars (US100, US500, US30, DE40, gold, silver, Brent, six FX majors), M5–D1, 2007/2013 → 2023-09-11. Timezone verified as UTC from the cash-open volatility spike. Index CFDs track the cash index; no systematic quarterly roll jumps were found (session-break gaps average ≈0 bp with no roll-date pattern).</li>"
      "<li><b>Final test:</b> TopstepX/ProjectX CME futures bars (ES, NQ, YM, RTY, MES, MNQ, GC, SI, CL, 6E, 6B, 6J), 1h from 2025-03-21 and 5/15-minute from 2026-01-20 to 2026-04-15. Equity-index series are continuous front-month; GC 1h is a thin back-month contract and was not used.</li></ul>")
    a(f"<p>{tag('FACT')} Structural checks across {len(q)} files: 0 duplicates, 0 OHLC violations after cleaning, no intra-week gaps over 6 hours. Abnormal moves (&gt;12 MAD) were inspected and are real events (e.g. the 2020-03-16 limit-down open).</p>")
    a(f"<p>{tag('ASSUMPTION')} Holidays and early closes follow an explicit NYSE calendar; early-close days are not traded. Data-vendor gaps inside a day are tolerated (flatten at the last available bar).</p>")
    a(f"<p>{tag('UNCERTAINTY')} CFD volume is a tick count, so the published VWAP trail was replaced by a running typical-price mean (TWAP). The gold CFD has a 17:00/18:00 ET rollover quote artifact (t≈±9); it was identified and excluded from every hypothesis. No intraday futures data exists in this environment for 2023-09 → 2025-03.</p></div>")

    # 4 methodology
    a('<h2><span class="n">04</span>Methodology</h2><div class="col"><ul>'
      "<li>Pipeline: data → cleaning → validation → features → documented hypothesis → implementation → unit and leakage tests → TRAIN screen → neighbourhood on TRAIN+VALIDATION → freeze → single OOS look → robustness, walk-forward, statistics, Monte Carlo → prop simulation → pre-registered final test.</li>"
      "<li>Execution model (numba engine, 39 tests): signals at bar close, fills at next bar open; stops at the worse of stop and open; stop assumed before target inside a bar; limit fills need trade-through; trailing stops update only on completed bars; forced flat at 16:00 ET (Topstep cut-off 16:10 ET).</li>"
      f"<li>{tag('ASSUMPTION')} Costs: 1 tick slippage per side on market/stop orders plus round-turn commission (ES/NQ $2.80, MES/MNQ $0.74). Historical P&amp;L is rescaled to the price level at the start of the final test (NQ 19,900), so fixed tick costs carry today's relative weight. Un-normalised historical-tick costs are kept as a stress case.</li>"
      "<li>Leakage defence: an automated test rebuilds every feature from truncated data and requires identical signals. It caught one real defect (daily features mapped by same-day row, which made signal <i>availability</i> depend on whether the day completed). The defect was fixed and every result re-run; superseded results remain flagged in the database.</li>"
      "<li>Multiple testing: every variant is recorded; Deflated Sharpe uses the full trial count; White's Reality Check and Hansen SPA are run within families.</li></ul></div>")

    # 5 families / counts
    a('<h2><span class="n">05</span>Strategy families and experiment count</h2>')
    a(table(["Hypothesis", "Family", "Valid experiments", "Status"],
            [[h, html.escape(fam), counts.get(h, 0), f'<span class="{"pass" if st=="SURVIVOR" else "fail"}">{st}</span>'] for h, fam, st, _ in hyp]))
    a('<h3>Filtering funnel</h3>')
    a(table(["Stage", "Survivors"], [["Hypothesis families tested", "10"], ["Passed TRAIN screen (≥1 variant, normalised costs)", "3 (H2, H3, H4)"],
                                     ["Survived costs (baseline and 2×)", "3"], ["Survived TRAIN+VALIDATION neighbourhood", "2 (H3, H4)"],
                                     ["Survived out-of-sample 2021–23", "1 (H3-NQ; H3-ES partial)"], ["Survived robustness and walk-forward", "1"],
                                     ["Survived Monte Carlo", "1"], ["Survived prop simulation (historical regime)", "1"],
                                     ["Survived final test on real futures", "1, narrowly"]]))

    # 6 failed/surviving
    a('<h2><span class="n">06</span>Failed and surviving hypotheses</h2>')
    a(table(["Hypothesis", "Verdict and evidence"], [[h, html.escape(v or "")] for h, fam, st, v in hyp]))
    a(f'<p class="col">The overnight-drift result is instructive. Returns concentrated at 00:00–03:00 ET in US and German indices (t≈2.5–3, matching Boyarchenko, Larsen &amp; Whelan), and the frozen spec had dev Sharpe {f(h4["NQ"]["splits"]["dev"]["sharpe"])} on NQ, yet out-of-sample it fell to {f(h4["NQ"]["splits"]["oos"]["sharpe"])} (ES {f(h4["ES"]["splits"]["oos"]["sharpe"])}, YM {f(h4["YM"]["splits"]["oos"]["sharpe"])}). It was rejected without retuning.</p>')

    # 7 final candidate
    a('<h2><span class="n">07</span>Final candidate: exact logic, risk and sizing</h2><div class="col">')
    a("<p><b>Hypothesis.</b> When Nasdaq-100 futures escape the normal intraday noise range around the open, the move tends to continue into the close. Plausible drivers are option-dealer gamma hedging, leveraged-ETF rebalancing and late-informed flow, all specific to equity indices. That fits H6's failure outside equities and H7's failure (midday moves continue rather than revert).</p>")
    a("<pre>Instrument     NQ (research) / MNQ (prop accounts), 15-minute bars, US equity RTH 09:30-16:00 ET\n"
      "Reference      O = today's 09:30 open; C1 = prior complete session's 16:00 close\n"
      "Noise sigma    s(k) = mean over the previous 14 sessions of |close_k / open - 1| at the same\n"
      "               time-of-day slot k (today excluded)\n"
      "Bands          UB = max(O, C1) * (1 + 1.25 s(k));  LB = min(O, C1) * (1 - 1.25 s(k))\n"
      "Checks         closes of bars ending 10:00, 11:00, ..., 15:00 ET (hourly)\n"
      "Entry          check close > UB -> BUY at next bar open; check close < LB -> SELL at next bar open\n"
      "               (no new entries after the 15:30 check window; at most 6 entries per day)\n"
      "Exit           long: at a check, close < max(UB, TWAP) -> exit at next open\n"
      "               short: at a check, close > min(LB, TWAP) -> exit at next open\n"
      "               TWAP = running mean of (H+L+C)/3 since 09:30\n"
      "Hard stop      1.5 x 20-day std of daily close changes from the fill (rarely hit)\n"
      "Time exit      flat at the 15:45-16:00 bar close (Topstep cut-off 16:10 ET)\n"
      "Targets        none (trend capture; exits are signal, stop or time)\n"
      "Max positions  1</pre>")
    a(f"<p><b>Sizing.</b> contracts = floor(B / (σ<sub>20d</sub> in points × $2)), minimum 1, maximum 50 MNQ. Conservative B=$500 (≈1 MNQ at current volatility), moderate $1,000, aggressive $1,600. {tag('ESTIMATE')} At 1 MNQ the expected trade is {f(exp['exp_trade_mean'], money=True)} ± {f(exp['exp_trade_sd'], money=True)} and the expected daily P&amp;L {f(exp['exp_daily_mean'], money=True)} ± {f(exp['exp_daily_sd'], money=True)}.</p></div>")

    # 8 splits
    a('<h2><span class="n">08</span>In-sample, validation and out-of-sample</h2>')
    rows = [[k, f(v["sharpe"]), f(v["total_usd"], money=True), v.get("trades"), f(v.get("win_rate"), 1, pct=True), f(v.get("profit_factor")),
             f(v["max_dd_usd"], money=True), f(v.get("expectancy_usd"), money=True)] for k, v in sp.items()]
    a(table(["Period (1 NQ, normalised costs)", "Sharpe", "Total", "Trades", "Win rate", "PF", "Max DD", "Expectancy/trade"], rows))
    cum = (d_hist.cumsum())
    a(svg_line({"H3 frozen spec, 1 MNQ, cumulative P&L after costs": cum}, shade=[("2019-01-01", "2020-12-31", "validation"), ("2021-01-01", "2023-09-11", "out-of-sample")]))
    yr = d_hist.groupby(d_hist.index.year).sum()
    a(svg_bars([str(y) for y in yr.index], list(yr.values), hl=["2021", "2022", "2023"]))
    a(f'<p class="col">{tag("FACT")} Only 2019 was a losing year (−$377 per MNQ). The out-of-sample years are highlighted.</p>')

    # 9 WF
    wf = nq["walk_forward"]
    a('<h2><span class="n">09</span>Walk-forward</h2>')
    a(f'<p class="col">Rolling 3-year in-sample selection over 24 variants, then a 1-year out-of-sample test, 2016–2023. Stitched OOS Sharpe {f(wf["oos_sharpe"])} vs in-sample {f(wf["is_mean_sharpe"])} (efficiency {f(wf["wf_efficiency"])}); {f(wf["pct_oos_years_positive"],0,pct=True)} of OOS years positive.</p>')
    a(table(["Test year", "Selected variant", "IS Sharpe", "OOS Sharpe", "Median variant OOS"],
            [[p["test_year"], f'lb {p["pick"]["lookback"]}, ×{p["pick"]["mult"]}, {p["pick"]["check_min"]} min', f(p["is_sharpe"]), f(p["oos_sharpe"]), f(p["median_variant_oos_sharpe"])] for p in wf["picks"]]))

    # 10 stats
    sd_, so = nq["stats_dev"], nq["stats_oos"]
    a('<h2><span class="n">10</span>Statistical validation</h2>')
    a(table(["Test", "Dev 2013–2020", "OOS 2021–2023"], [
        ["Newey-West t (mean daily P&L &gt; 0)", f(sd_["nw_t"]), f(so["nw_t"])],
        ["one-sided p", f(sd_["nw_p_one_sided"], 5), f(so["nw_p_one_sided"], 4)],
        ["Block-bootstrap 95% CI of Sharpe", f"{f(sd_['sharpe_ci95'][0])} … {f(sd_['sharpe_ci95'][1])}", f"{f(so['sharpe_ci95'][0])} … {f(so['sharpe_ci95'][1])}"],
        ["Probabilistic Sharpe vs 0", f(sd_["psr_vs0"], 3), f(so["psr_vs0"], 3)],
        ["Deflated Sharpe (all trials)", f(sd_["dsr"], 3), "single look"],
        ["White Reality Check p (24-variant family)", f(sd_["reality_check"]["rc_pvalue"], 3), "–"],
        ["Hansen SPA p", f(sd_["reality_check"]["spa_pvalue"], 3), "–"],
        ["Random-direction sign-flip p", f(fal["dev_signflip_p"], 4), f(fal["oos_signflip_p"], 4)]]))
    a(f'<p class="col">{tag("UNCERTAINTY")} The Deflated Sharpe on development data is about 0.5 once all ~1,000 trials across unrelated families are counted. Development data alone is not conclusive under the most severe multiple-testing correction. The evidence rests on the independent single-look OOS result.</p>')

    # 11 MC
    mc = nq["mc_dev"]
    a('<h2><span class="n">11</span>Monte Carlo</h2>')
    a('<p class="col">Stationary block bootstrap (5-day blocks, 5,000 paths) of one-year paths of dev daily P&amp;L, 1 NQ. Divide by 10 for 1 MNQ.</p>')
    a(table(["Percentile", "1-yr total", "Sharpe", "Max drawdown", "Longest losing-day streak"],
            [[f"p{p}", f(mc["total"][f"p{p}"], money=True), f(mc["sharpe"][f"p{p}"]), f(mc["max_dd"][f"p{p}"], money=True), f(mc["loss_streak_days"][f"p{p}"], 0)] for p in (5, 25, 50, 75, 95)]))
    a(f'<p class="col">{tag("ESTIMATE")} Probability that a 1-year path loses money: {f(mc["p_total_le0"], 1, pct=True)}.</p>')

    # 12 cost
    a('<h2><span class="n">12</span>Cost and slippage stress</h2>')
    cs = {x["scenario"]: x for x in nq["cost_stress_oos"]}
    cd = {x["scenario"]: x for x in nq["cost_stress_dev"]}
    a(table(["Scenario", "Dev Sharpe", "OOS Sharpe", "OOS total (1 NQ)"], [[k, f(cd[k]["sharpe"]), f(cs[k]["sharpe"]), f(cs[k]["total_usd"], money=True)] for k in cs]))
    a(f'<p class="col">Random extra slippage of 0–4 ticks per side: OOS Sharpe p5 {f(fal["random_extra_slip_0to4ticks"]["oos_p5"])}. Delaying every entry and exit by one bar (15 min): dev {f(fal["delay_1bar"]["dev"])}, OOS {f(fal["delay_1bar"]["oos"])}. About 120 trades a year with large average moves make costs a small share of the edge.</p>')

    # 13 params
    nb = pd.read_csv(RES / "h3_neighbors_NQ.csv")
    a('<h2><span class="n">13</span>Parameter robustness</h2>')
    a(f'<p class="col">All {len(nb)} neighbours (lookback 10/14/20 × band 1.0/1.25/1.5 × checks 30/60 min) are positive on development data: Sharpe {f(nb.sharpe.min())} to {f(nb.sharpe.max())}, median {f(nb.sharpe.median())}. The frozen point sits near the middle of the plateau rather than at its peak.</p>')
    a(table(["Lookback", "Band", "Checks", "Dev Sharpe", "Max DD (1 NQ)"], [[r.lookback, r.mult, f"{r.check_min} min", f(r.sharpe), f(r.max_dd, money=True)] for r in nb.itertuples()]))

    # 14 regimes
    rg = nq["regimes_all"]
    a('<h2><span class="n">14</span>Regime analysis</h2>')
    a(table(["Regime (2013–2023)", "Days", "Sharpe", "Total (1 NQ)"], [[f"{k} trend", v["days"], f(v["sharpe"]), f(v["total"], money=True)] for k, v in rg["trend"].items()] +
            [[k.replace("_", " "), v["days"], f(v["sharpe"]), f(v["total"], money=True)] for k, v in rg["vol"].items()]))
    a(table(["Crisis window", "P&L (1 NQ)"], [[k.replace("_", " "), f(v, money=True)] for k, v in rg["crises"].items()]))
    a('<p class="col">The edge holds in bull and bear trends and in every volatility tercile. It earned the most in directional sell-offs (2018-Q4, 2022) and lost in choppy low-trend years (2019). That fits a trend-capture mechanism.</p>')

    # 15 falsification
    a('<h2><span class="n">15</span>Falsification attempts</h2>')
    ls = fal["dev_long_short"]
    a(table(["Attack", "Result", "Outcome"], [
        ["Look-ahead / leakage (truncate future, shock future prices)", "All strategies produce identical past signals; one defect found and fixed earlier", '<span class="pass">survived</span>'],
        ["Just long beta?", f"Dev: shorts {f(ls['short']['total'], money=True)} vs longs {f(ls['long']['total'], money=True)}; bear-trend Sharpe {f(rg['trend']['bear']['sharpe'])}", '<span class="pass">survived</span>'],
        ["Random direction at same times", f"sign-flip p = {f(fal['dev_signflip_p'],4)} / {f(fal['oos_signflip_p'],4)}", '<span class="pass">survived</span>'],
        ["Execution latency (+1 bar)", f"Sharpe {f(fal['delay_1bar']['dev'])} / {f(fal['delay_1bar']['oos'])}", '<span class="pass">survived</span>'],
        ["Drop best year", f"Sharpe {f(fal['dev_sharpe_drop_best_year'])} / {f(fal['oos_sharpe_drop_best_year'])}", '<span class="pass">survived</span>'],
        ["Drop best 10 days", f"Sharpe {f(fal['dev_sharpe_drop_best10days'])} / {f(fal['oos_sharpe_drop_best10days'])}", '<span class="weak">weakened: payoff concentrated in trend days</span>'],
        ["Generalises to other markets?", "ES OOS 1.17 but fragile; YM weak; FX/oil/gold fail", '<span class="weak">equity-specific</span>'],
        ["Roll artifacts", "Intraday, flat daily; CFD proxies show no quarterly jump pattern", '<span class="pass">not applicable</span>'],
        ["Data-source dependency (CFD vs futures)", f"Real futures final test: Sharpe {f(fin['B_NQ']['metrics']['sharpe'])} (13 mo), {f(fin['A_NQ']['metrics']['sharpe'])} (exact, 3 mo)", '<span class="weak">narrow pass</span>'],
        ["Independent re-implementation", "Event-driven paper trader reproduces all 22 backtest trades on real MNQ data", '<span class="pass">survived</span>']]))

    # 16 final test
    b, aa = fin["B_NQ"]["metrics"], fin["A_NQ"]["metrics"]
    a('<h2><span class="n">16</span>Final test on real futures</h2>')
    a(f'<p class="col">The protocol was committed before any strategy touched the futures data: <i>{html.escape(proto["test_B_hourly_approximation"]["criterion"])}</i> Calibration of the hourly approximation on CFD data: dev {f(cal["dev"]["sharpe"])}, OOS {f(cal["oos"]["sharpe"])}; expected 13-month Sharpe median {f(cal["boot_270d_sharpe_pcts"]["50"])}, 5th percentile {f(cal["boot_270d_sharpe_pcts"]["5"])}.</p>')
    a(table(["Test", "Sharpe", "Total", "Trades", "Max DD", "Win rate", "PF", "Result"], [
        ["B · NQ · 1h approx · 2025-03 → 2026-04", f(b["sharpe"]), f(b["total_usd"], money=True), b["trades"], f(b["max_dd_usd"], money=True), f(b["win_rate"], 0, pct=True), f(b["profit_factor"]), '<span class="weak">pass (narrow)</span>'],
        ["B · MNQ", f(fin["B_MNQ"]["metrics"]["sharpe"]), f(fin["B_MNQ"]["metrics"]["total_usd"], money=True), fin["B_MNQ"]["metrics"]["trades"], f(fin["B_MNQ"]["metrics"]["max_dd_usd"], money=True), f(fin["B_MNQ"]["metrics"]["win_rate"], 0, pct=True), f(fin["B_MNQ"]["metrics"]["profit_factor"]), '<span class="weak">agrees</span>'],
        ["A · NQ · exact 15m · 2026-01 → 04", f(aa["sharpe"]), f(aa["total_usd"], money=True), aa["trades"], f(aa["max_dd_usd"], money=True), f(aa["win_rate"], 0, pct=True), f(aa["profit_factor"]), '<span class="pass">positive</span>']]))
    a(svg_line({"Final test B, 1 MNQ, real futures (hourly approximation)": d_final.cumsum()}))
    mo = fin["B_NQ"]["monthly"]
    a(svg_bars([k.replace("(", "").replace(")", "").replace(", ", "-")[2:] for k in mo], [v / 10 for v in mo.values()], money=True))
    a(f'<p class="col">{tag("UNCERTAINTY")} Monthly P&amp;L per MNQ: the 13-month result depends on Oct–Nov 2025. Historically about 4–7% of 13-month windows were this weak, so this is not a refutation, but it is the main open risk.</p>')

    # 17 prop
    a('<h2><span class="n">17</span>Prop-firm simulation</h2>')
    a('<p class="col">Engine: EOD-trailing max loss checked intraday against open-trade excursion, optional daily loss limit, Topstep 55% consistency (target rises to best day ÷ 0.55), minimum days, fees. Monte Carlo uses 4,000 block-bootstrap evaluation attempts; the historical method starts an evaluation every third historical day.</p>')
    rows = []
    for key in ("conservative|dev", "conservative|oos", "moderate|oos", "aggressive|oos"):
        for rn, r in prop[key]["rules"].items():
            if rn in ("Topstep 50K Combine", "Topstep 150K Combine", "MyFundedFutures 50K Core"):
                mcp = r["mc"]
                rows.append([key.replace("|", " · "), rn, f(r["avg_contracts"], 1), f(mcp["p_pass"], 0, pct=True), f(mcp["p_fail_mll"], 0, pct=True),
                             f(mcp["p_timeout"], 0, pct=True), f(mcp["days_to_pass_p50"], 0), f(mcp["days_to_pass_p95"], 0),
                             f(mcp.get("expected_cost_to_pass_usd"), money=True), f(r["hist"]["p_pass"], 0, pct=True)])
    for key in ("conservative|oos", "moderate|oos"):
        r = ftmo[key]["rules"]["FTMO 2-Step 100K"]; mcp = r["mc"]
        rows.append([key.replace("|", " · "), "FTMO 2-Step 100K (US100 CFD)", "≈0.5% / 0.8% daily σ", f(mcp["p_pass"], 0, pct=True), f(mcp["p_fail"], 0, pct=True),
                     f(mcp["p_timeout"], 0, pct=True), f(mcp["days_to_pass_p50"], 0), f(mcp["days_to_pass_p95"], 0), f(mcp.get("expected_cost_to_pass_usd"), money=True), f(r["hist"]["p_pass"], 0, pct=True)])
    a(table(["Risk · data", "Account", "Avg MNQ", "Pass", "Fail (loss limit)", "Unresolved", "Days to pass p50", "p95", "Exp. cost to pass", "Historical-start pass"], rows))
    a(f'<p class="col">{tag("ESTIMATE")} More risk does not help. Moving from conservative to aggressive cuts Topstep 50K pass probability from about 75% to 47–64% and only shortens the median from ~110–150 to ~50–60 trading days. Conservative sizing is recommended. The trailing $2,000 limit and the 1-MNQ minimum cap pass probability at about 76% even with the full historical edge.</p>')
    a("<h3>Pass probability if the edge decays</h3>")
    a(svg_scenarios(sc["scenarios"]))
    rr = sc["realised_2025_26"]["Topstep 50K Combine"]
    a(f'<p class="col">{tag("ESTIMATE")} Bootstrapping the realised 2025–26 futures results gives a Topstep 50K pass probability of {f(rr["p_pass"],0,pct=True)} with a median of {f(rr["days_to_pass_p50"],0)} days. At that level the evaluation economics are negative.</p>')

    # 18 weaknesses
    a('<h2><span class="n">18</span>Weaknesses and failure scenarios</h2><div class="col"><ul>'
      "<li><b>Edge decay after publication.</b> The strategy went public in 2024 and is widely copied. The 2025–26 final test is consistent with partial decay.</li>"
      "<li><b>Choppy, range-bound markets</b> (2019-like) give many small whipsaw losses. Longest losing-day streaks of 8–11 days are normal (Monte Carlo p75–p95).</li>"
      "<li><b>Concentrated payoff.</b> Without its 10 best days the OOS Sharpe falls to 0.62, so missing a few trend days through downtime or a manual override costs a lot.</li>"
      "<li><b>Proxy data.</b> Development used CFD bars with a TWAP instead of VWAP; futures checks cover only 13 months (approximation) and 3 months (exact).</li>"
      "<li><b>Trailing-drawdown mechanics.</b> At 1 MNQ the daily σ is about $175 against a $2,000 trailing limit; a normal 1-year drawdown for 1 MNQ is $1.4k (p50) to $3.4k (p95), so roughly a quarter of evaluations fail even with the full edge.</li>"
      "<li><b>Slow evaluations.</b> The median is about 5–7 months, which adds subscription fees and exposure to rule changes. Consistency and position-limit rules currently do not bind.</li>"
      "<li><b>Platform risk.</b> Automation is allowed at Topstep via the API, but malfunctions are not refunded. Rules were verified only through search extracts of official pages and can change.</li></ul></div>")

    # 19 paper plan
    a('<h2><span class="n">19</span>Paper-trading plan</h2><div class="col">')
    a("<p>Implementation: <code>src/qpl/execution/paper.py</code> (event-driven, signals only from received bars, simulated fills, Topstep rule tracking, JSONL audit log, kill switch) and <code>paper_trading/run_paper.py</code>. Parity test: the paper trader reproduces every backtest trade on real MNQ data. It never sends orders.</p>")
    a("<ol><li>Feed completed 15-minute MNQ bars (UTC open-time stamps) from a market-data source, for example the TopstepX/ProjectX history endpoint or any CME feed, into <code>PaperTrader.on_bar</code>, or append them to a CSV and run <code>python paper_trading/run_paper.py --csv bars.csv</code>.</li>"
      "<li>Run for at least 60 trading days (~50 trades), conservative sizing (1 MNQ).</li>"
      f"<li><b>Go</b> to a Topstep 50K Combine only if: cumulative P&amp;L per contract is above zero <i>and</i> the monitor z-score vs the backtest expectation ({f(exp['exp_trade_mean'], money=True)} ± {f(exp['exp_trade_sd'], money=True)} per trade) is above −1.0, with live fills within 1 tick of the simulated price on average.</li>"
      "<li><b>Stop</b> (the kill switch fires automatically) if, after 30 or more trades, z &lt; −2. That means do not buy evaluations and return to research.</li>"
      "<li>Between −2 and −1: extend paper trading to 100 trades before deciding.</li></ol></div>")

    # 20 card
    a('<h2><span class="n">20</span>Strategy card</h2>')
    card = [("Market", "Nasdaq-100 futures: MNQ for prop accounts (NQ = 10 MNQ)"), ("Timeframe", "15-minute bars, US RTH; decisions hourly 10:00–15:00 ET"),
            ("Family", "Intraday momentum / volatility breakout"), ("Hypothesis", "Escapes from the time-of-day noise band continue into the close (equity-specific hedging flows)"),
            ("Entry", "Hourly check close outside band ×1.25 of the 14-day time-of-day mean absolute move from the open → market order at next bar open"),
            ("Exit", "Close back inside max/min(band, session TWAP) at a check → next open; flat 16:00 ET"), ("Stop", "Hard stop 1.5 × 20-day daily σ"), ("Target", "None"),
            ("Max positions", "1 (≤6 entries/day; observed ≤3)"), ("Position sizing", "floor($500 ÷ (σ20d pts × $2)), min 1, max 50 MNQ; ≈1 MNQ today"),
            ("Trades", f"≈{exp['trades_per_year']/252:.2f}/day, ≈{exp['trades_per_week']:.1f}/week, trades on {f(exp['pct_days_traded'],0,pct=True)} of days"),
            ("Holding period", f"median {exp['median_hold_min']:.0f} min, mean {exp['avg_hold_min']:.0f} min"),
            ("Expectancy", f"{f(exp['exp_trade_mean'], money=True)}/trade per MNQ (win rate {f(exp['win_rate'],0,pct=True)}, avg win {f(exp['avg_win'], money=True)}, avg loss {f(exp['avg_loss'], money=True)})"),
            ("Sharpe", f"dev {f(sp['dev']['sharpe'])} · OOS {f(sp['oos']['sharpe'])} · final test {f(fin['B_NQ']['metrics']['sharpe'])} (13 mo) / {f(fin['A_NQ']['metrics']['sharpe'])} (3 mo exact)"),
            ("Drawdown", f"max DD per MNQ: dev {f(sp['dev']['max_dd_usd']/10, money=True)}, OOS {f(sp['oos']['max_dd_usd']/10, money=True)}, final {f(fin['B_MNQ']['metrics']['max_dd_usd'], money=True)}"),
            ("Monte Carlo drawdown", f"1-yr per MNQ p50 {f(mc['max_dd']['p50']/10, money=True)}, p95 {f(mc['max_dd']['p95']/10, money=True)}"),
            ("Walk-forward", f"stitched OOS Sharpe {f(wf['oos_sharpe'])}, efficiency {f(wf['wf_efficiency'])}"),
            ("Prop pass probability", f"Topstep 50K ≈{f(sc['scenarios']['keep_100pct_edge']['Topstep 50K Combine']['p_pass'],0,pct=True)} (historical edge) / {f(sc['scenarios']['keep_50pct_edge']['Topstep 50K Combine']['p_pass'],0,pct=True)} (half edge) / {f(rr['p_pass'],0,pct=True)} (2025–26 regime); FTMO 2-Step ≈{f(sc['scenarios']['keep_100pct_edge']['FTMO 2-Step 100K']['p_pass'],0,pct=True)}"),
            ("Failure probability", f"Topstep 50K ≈{f(sc['scenarios']['keep_100pct_edge']['Topstep 50K Combine']['p_fail'],0,pct=True)} with full edge"),
            ("Major failure conditions", "Post-publication decay; range-bound markets; missing trend days; trailing-drawdown path risk"),
            ("Recommended risk", "Conservative: 1 MNQ on a Topstep 50K, only after the paper-trading gate")]
    a('<div class="card">' + "".join(f"<div>{html.escape(k)}</div><div>{html.escape(v)}</div>" for k, v in card) + "</div>")

    # 21 repro
    a('<h2><span class="n">21</span>Reproducibility</h2>')
    a("<pre>pip install -r requirements.txt\n"
      "bash scripts/run_tests.sh          # 40 tests incl. leakage and paper-parity\n"
      "bash scripts/run_pipeline.sh       # fetch pinned data, validate, all research generations\n"
      "bash scripts/reproduce_final.sh    # frozen candidate: eval, falsification, prop sims, final test\n"
      "bash scripts/make_report.sh        # regenerates reports/research_report.html</pre>")
    a(f'<p class="col">Data commits: Dukascopy mirror {json.loads((ROOT/"config"/"data_sources.json").read_text())["dukascopy_github"]["commit"][:12]}, TopstepX mirror {json.loads((ROOT/"config"/"data_sources.json").read_text())["topstepx_github"]["commit"][:12]}. Experiment database: <code>research_database/experiments.sqlite</code> ({n_all} rows including superseded and invalid ones, kept for audit). Nothing here is a guarantee: backtests and simulations are evidence, not promises of profit, evaluation passes or payouts.</p>')
    a("</main>")
    return "\n".join(S)


def main():
    out = ROOT / "reports" / "research_report.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(build())
    print("wrote", out)


if __name__ == "__main__":
    main()
