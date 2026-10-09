"""V6 deliverable: reports/v6_research_report.html (earlier reports untouched). All numbers read from results/ and config/."""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from ..research import factory as F
from .report import f, svg_line, table, tag
from .report_v3 import h2, head, status_span

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results"


def J(p):
    return json.loads((RES / p).read_text())


def st(s):
    m = {"ELIGIBLE_FOR_INDEPENDENT_VALIDATION": "ELIGIBLE", "PROMISING_BUT_UNVALIDATED": "PROMISING"}
    cls = "pass" if s.startswith("ELIGIBLE") else ("weak" if s.startswith(("PROMISING", "EXPLOR")) else "fail")
    return f'<span class="{cls}">{html.escape(m.get(s, s))}</span>'


def build() -> str:
    ok, n_ev = F.verify_ledger()
    reg = pd.read_csv(ROOT / "v6/V6_HYPOTHESIS_REGISTRY.csv")
    counts = reg.v6_status.value_counts().to_dict()
    dec, g13, aud, g14 = J("v6_ct1_decay.json"), J("v6_futures_gen13.json"), J("v6_futures_audit.json"), J("v6_futures_gen14.json")
    rg, ml, sts, pf = J("v6_gen15_regime.json"), J("v6_gen15_ml.json"), J("v6_futures_stats.json"), J("v6_portfolio.json")
    c16, c18, f9r, sm, td = J("v6_gen16_crypto_xs.json"), J("v6_gen18_crypto_cont.json"), J("v6_f9_record.json"), J("v6_gen17_small.json"), J("v6_trend_decay.json")
    fam = g13["families"]
    S = head("Quant Prop Lab V6", "Quant Prop Lab · V6 autonomous research · 2026-10-09")
    S += ["<h1>Quant Prop Lab V6</h1>",
          '<p class="col">V6 asked one question: is there a real, robust edge, and why did the only V4 survivor (crypto CT1) decay? '
          "The answer came from 50 years of futures data the project had never touched (252 markets, pysystemtrade, 1970–2024), "
          "from new on-chain crypto data (Coin Metrics), and from pre-registered tests whose protocols were committed to git before any return was computed. "
          "Earlier reports are unchanged.</p>",
          '<div class="verdict"><strong>Answer.</strong> Yes, with honest limits. <b>Diversified futures trend-following and carry</b> passed every pre-registered gate on untouched data, including one TEST look (2014–19) and one HOLDOUT look (2020–24). '
          f"Trend+carry combo: {fam['F7_COMBO']['DISCOVERY']['sharpe']:.2f} / {fam['F7_COMBO']['VALIDATION']['sharpe']:.2f} / {fam['F7_COMBO']['TEST']['sharpe']:.2f} / {fam['F7_COMBO']['HOLDOUT']['sharpe']:.2f} net Sharpe. "
          "This is a <b>replication of well-published effects</b>, not a discovery, and they have decayed: the combined book's Sharpe is about 1.5 before 2010 and about 0.8 after. "
          "The book is cost-sensitive and needs about $1M for a faithful futures implementation. No recent window is individually significant, and a prospective record would need about 5–10 years to confirm Sharpe 0.5–0.7. "
          "CT1's decay turns out to be part of this economy-wide decline, plus the fact that CT1 was mostly conditional long BTC exposure. "
          "Every regime, change-point, factor-timing and ML layer failed against random controls or simple baselines. "
          "<b>Nothing here authorises real-money trading.</b> The next evidence is prospective paper trading, for which the tooling is built.</div>",
          '<div class="kpis">'
          f'<div class="kpi"><b>{len(reg)}</b><span>hypotheses in the registry (all versions)</span></div>'
          f'<div class="kpi"><b>{counts.get("ELIGIBLE_FOR_INDEPENDENT_VALIDATION", 0)}</b><span>eligible for independent validation (futures trend/carry)</span></div>'
          f'<div class="kpi"><b>{counts.get("REJECTED", 0)}</b><span>rejected, kept on record</span></div>'
          f'<div class="kpi"><b>{sts["PBO_dev_1985_2013"]["pbo"]:.3f}</b><span>PBO of the futures grid</span></div>'
          f'<div class="kpi"><b>{"intact" if ok else "BROKEN"}</b><span>ledger hash chain, {n_ev} events</span></div></div>']
    secs = ["Why CT1 decayed", "New data: futures panel", "Gen13: futures factor families", "Falsification audit", "Implementation: costs, buffering, capital",
            "Adaptive layers: regime, change-point, ML", "Statistical integrity", "Has the trend premium decayed?", "New crypto data: on-chain and cross-section",
            "Portfolio: crypto CT1 + futures", "F9: the frozen candidate for paper trading", "Limits and what is not established", "Next actions and reproduction"]
    S.append('<ol class="toc">' + "".join(f"<li>{html.escape(s)}</li>" for s in secs) + "</ol>")

    # 1
    p = dec["periods"]
    S.append(h2(1, secs[0]))
    S.append(table(["", *p.keys()], [
        ["CT1 net Sharpe", *[f(v["net_sharpe"]) for v in p.values()]], ["gross Sharpe", *[f(v["gross_sharpe"]) for v in p.values()]],
        ["cost + funding drag p.a.", *[f(v["ann_cost"] - v["ann_funding"], 1, pct=True) for v in p.values()]],
        ["long-leg Sharpe", *[f(v["long_leg_sharpe"]) for v in p.values()]], ["short-leg Sharpe", *[f(v["short_leg_sharpe"]) for v in p.values()]],
        ["BTC drift / vol", *[f(v["btc_drift_over_vol"]) for v in p.values()]], ["signal flips / year", *[f(v["signal_flips_per_year"], 0) for v in p.values()]],
        ["TSMOM-20 → next 5d t-stat", *[f(v["tsmom_pred"]["L20_h5"]["t"]) for v in p.values()]],
        ["top 5% days share of P&L", *[f(v["top5pct_days_share_of_pnl"], 0, pct=True) for v in p.values()]]]))
    dv = dec["dev_vs_post"]
    S.append('<p class="col">' + tag("FACT") + " CT1 was conditional long exposure to BTC trends. The short leg never paid in any period, and the long leg scaled with BTC's own drift/vol. "
             "Costs and funding are not the cause. Short-horizon persistence disappeared in 2024–26 and whipsaw rose. "
             f"The dev→post decline ({dv['dev_sharpe']:.2f} → {dv['post_sharpe']:.2f}) has a 95% bootstrap CI for the difference of [{dv['diff_ci95'][0]:.2f}, {dv['diff_ci95'][1]:.2f}]. "
             "§8 shows the same decline in 50 years of futures trend.</p>")

    # 2
    S.append(h2(2, secs[1]))
    S.append('<p class="col">' + tag("FACT") + " <code>robcarver17/pysystemtrade</code> @bbe29e19 (GPL-3): back-adjusted futures, carry contracts, cost estimates and FX. "
             "252 instruments → 227 after de-duplication → <b>155 in a rule-based universe</b> (38 equity, 33 FX, 30 bond, 26 ags, 13 metals, 13 energy, 2 vol). Crypto was excluded to keep this test independent of V4. "
             "Decimal-shift bad ticks were found and repaired. Weekly returns correlate 0.89–0.99 with the independent Dukascopy data. "
             "Returns are ΔADJ / actual contract PRICE. Execution lags the decision by one full day. Costs come from the repository's spread + commission table.</p>")

    # 3
    S.append(h2(3, secs[2]))
    rows = []
    for k, r in fam.items():
        rows.append([k, *[f(r[p_]["sharpe"]) if p_ in r else "–" for p_ in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT")],
                     f(r["DISCOVERY"].get("residual_sharpe")), st(r["verdict"])])
    S.append(table(["Family (net Sharpe)", "DISCOVERY 1975–2004", "VALIDATION 2005–13", "TEST 2014–19 (1 look)", "HOLDOUT 2020–24Q1 (1 look)", "DISC residual vs long RP", "Status"], rows))
    b = g13["benchmark"]
    S.append('<p class="col">' + tag("FACT") + f" Long-only risk-parity benchmark: {b['DISCOVERY']['sharpe']:.2f} / {b['VALIDATION']['sharpe']:.2f} / {b['TEST']['sharpe']:.2f} / {b['HOLDOUT']['sharpe']:.2f}. "
             "F0 is the frozen crypto CT1 rule applied unchanged to futures. Its pass is out-of-domain evidence that the trend idea is real. "
             "Cross-sectional momentum, value and skew did not survive costs.</p>")
    try:
        pn = pd.read_parquet(RES / "v6_futures_gen13_pnl.parquet").loc["1980":]
        cur = {"F7 trend+carry combo": pn["F7_COMBO"].cumsum(), "Long-only risk parity": pn["LONG_RP"].cumsum()}
        cur = {k: v.resample("ME").last() for k, v in cur.items()}
        S.append(svg_line(cur, ylab="cumulative net return (10% vol book)", money=False,
                          shade=[("2014-01-01", "2019-12-31", "TEST"), ("2020-01-01", "2024-03-28", "HOLDOUT")]))
    except Exception as e:  # pragma: no cover
        S.append(f"<p>chart unavailable: {html.escape(str(e))}</p>")

    # 4
    S.append(h2(4, secs[3]))
    a4 = aud["A4_lag_cost"]["F7_COMBO"]
    S.append(table(["F7 variant", "DISCOVERY", "VALIDATION", "TEST", "HOLDOUT"], [[k, *[f(v[p_]) for p_ in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT")]] for k, v in a4.items()]))
    S.append('<p class="col">' + tag("FACT") + " The result is robust to execution lag (1–5 days) and to random halves of the universe (TEST 0.50–0.98). P&L is broad: no instrument dominates. "
             "<b>It is not robust to costs.</b> At 3× the assumed costs, VALIDATION is roughly break-even, and at 5× everything is negative. "
             "Cross-source check (weekly correlation with Dukascopy): " + ", ".join(f"{k} {v['weekly_corr']:.2f}" for k, v in aud["A1_cross_source"].items() if isinstance(v, dict)) + ".</p>")

    # 5
    S.append(h2(5, secs[4]))
    ga = g14["G14a"]["F7_COMBO"]
    S.append(table(["F7 buffer b", "VAL 1× cost", "VAL 3× cost", "TEST 3× (contam.)", "turnover ×/yr (VAL)"],
                   [[k, f(v["VALIDATION_1x"]), f(v["VALIDATION_3x"]), f(v["TEST_3x"]), f(v["turnover_val"], 0)] for k, v in ga.items() if k.startswith("b")]))
    S.append(table(["Capital (integer contracts)", "instruments held", "VALIDATION", "2014–24 (contam.)", "realised vol"],
                   [[f"${int(k):,}", f(v["median_instruments_held_2020"], 0), f(v["VALIDATION"]), f(v["2014_2024_contaminated"]), f(v["ann_vol_2014_2024"], 1, pct=True)] for k, v in g14["G14c"].items()]))
    S.append('<p class="col">' + tag("FACT") + " Buffering roughly halves cost sensitivity; b = 0.05 was adopted by the pre-registered smallest-stable rule. "
             "A faithful futures implementation needs about $1M. At $250k the book under-deploys risk. A small-account design (gen17) passed at $100k with only 5 instruments while the $250k version failed. That is a noise signature, so it is <b>not recommended</b>. "
             "Two implementation bugs (audit V6-B1) were found and fixed before reporting.</p>")

    # 6
    S.append(h2(6, secs[5]))
    rr = [[k, f(v["OOS"]), f(v["SEC"]), f(v.get("random_p95")), st("PROMISING_BUT_UNVALIDATED" if v.get("adopt") else "REJECTED")] for k, v in rg.items() if isinstance(v, dict) and "random_p95" in v]
    rr += [[f"ML {k}", f(ml[k]["OOS"]), f(ml[k]["SEC"]), f"P(≤F7) {ml[k]['P(sharpe<=F7)']:.2f}", st("REJECTED")] for k in ("RIDGE", "LGBM")]
    S.append(table(["Layer (walk-forward OOS 1995–2013)", "OOS Sharpe", "2014–24 (contam.)", "random p95 / bootstrap", "Verdict"], rr))
    S.append('<p class="col">' + tag("FACT") + f" Baselines: equal-risk sleeves B0 {rg['B0']['OOS']:.2f}; F7 {ml['F7']['OOS']:.2f}. "
             "HMM states use the forward filter only (no smoothing), and ML training data is purged before each annual refit. Timing layers never beat random weight paths with the same distribution. "
             "This is the third replication across asset classes. ML found no information beyond the simple trend/carry combination.</p>")

    # 7
    S.append(h2(7, secs[6]))
    S.append(table(["", "DISCOVERY", "VALIDATION", "TEST", "HOLDOUT", "DSR 1985–2024", "DSR post-2014"],
                   [[k, *[f"{v[p_]['sharpe']:.2f} [{v[p_]['ci95'][0]:.2f}, {v[p_]['ci95'][1]:.2f}]" for p_ in ("DISCOVERY", "VALIDATION", "TEST", "HOLDOUT")],
                     f(v["DSR_1985_2024"]), f(v["DSR_post2014"])] for k, v in sts.items() if k in ("F7", "F2", "F3", "B0_sleeve_rp")]))
    S.append('<p class="col">' + tag("FACT") + f" PBO {sts['PBO_dev_1985_2013']['pbo']:.3f} over {sts['PBO_dev_1985_2013']['N_variants']} configs. "
             f"{sts['n_trials_futures']} futures trials in total. No family is significant after Holm in the TEST or HOLDOUT windows alone. "
             f"MinTRL to reject Sharpe ≤ 0 at 95%: SR 0.5 → {sts['MinTRL_years']['SR0.5']} years; SR 0.7 → {sts['MinTRL_years']['SR0.7']} years. "
             + tag("UNCERTAINTY") + " Significance comes from the long cross-market record, not from recent windows.</p>")

    # 8
    S.append(h2(8, secs[7]))
    S.append(table(["Sleeve", "1980s", "1990s", "2000s", "2010s", "2020s", "slope/decade (t)", "pre → post 2010"],
                   [[k, *[f(v["mean_by_decade"].get(d)) for d in ("1980s", "1990s", "2000s", "2010s", "2020s")], f"{v['annual_sharpe_slope_per_decade']:.2f} ({v['slope_t']:.1f})",
                     f"{v['pre2010_sharpe']:.2f} → {v['post2010_sharpe']:.2f}"] for k, v in td.items() if k in ("T", "C", "B0")]))
    S.append(table(["TSMOM by class", "1980s", "1990s", "2000s", "2010s", "2020s"], [[c, *[f(v.get(d)) for d in ("1980s", "1990s", "2000s", "2010s", "2020s")]] for c, v in td["tsmom_by_class_decade"].items()]))

    # 9
    S.append(h2(9, secs[8]))
    rows = [[k, f(v["TRAIN"]["net"]), f(v["TRAIN"]["gross"]), st(v["verdict"])] for k, v in c16.items() if "TRAIN" in v]
    m16 = c16["H16e_BTC_MVRV_TIMING"]["binary"]["TRAIN"]
    rows.append(["H16e BTC MVRV timing", f(m16["sharpe"]), f"resid {m16['resid']:.2f}", st(c16["H16e_BTC_MVRV_TIMING"]["verdict"])])
    rows.append(["H18 XS continuation (4-weekly)", f"VAL {c18['VALIDATION']['net']:.2f}", f"TEST {c18['TEST']['net']:.2f}", st(c18["verdict"])])
    S.append(table(["Crypto hypothesis (Coin Metrics, top-30 point-in-time)", "TRAIN 2017–20 net", "gross / other", "Verdict"], rows))
    S.append('<p class="col">' + tag("FACT") + " Coin Metrics community data (CC BY-NC 4.0, research only) includes some dead coins, which reduces survivorship bias without removing it. "
             "Crypto cross-sectional momentum, reversal, on-chain value (MVRV) and network growth all failed after realistic costs. MVRV timing is just lower-beta BTC.</p>")

    # 10
    S.append(h2(10, secs[9]))
    g = pf["add_CT1_third_risk_sharpe_gain"]
    S.append('<p class="col">' + tag("FACT") + f" Weekly correlation of CT1 with the futures sleeves is {pf['corr']['CT1']['B0']:.2f}, and about 0 in the futures book's worst weeks. "
             f"Adding CT1 at 1/3 of the risk raised 2015–24 Sharpe by {g['point']:.2f} (90% CI {g['ci90'][0]:.2f}–{g['ci90'][1]:.2f}). " + tag("ESTIMATE") +
             " Using CT1's post-2021 Sharpe (~0.4), the forward gain is about +0.1. Its role is a small, divisible diversifying sleeve.</p>")

    # 11
    S.append(h2(11, secs[10]))
    pp = f9r["periods"]
    S.append(table(["F9 (frozen)", "DISCOVERY (clean)", "VALIDATION*", "TEST (contam.)", "HOLDOUT (contam.)"], [
        ["net Sharpe [95% CI]", *[f"{pp[k]['sharpe']:.2f} [{pp[k]['sharpe_ci95'][0]:.2f}, {pp[k]['sharpe_ci95'][1]:.2f}]" for k in pp]],
        ["gross Sharpe", *[f(pp[k]["gross_sharpe"]) for k in pp]], ["ann. return / vol", *[f"{pp[k]['ann_ret']:.1%} / {pp[k]['ann_vol']:.1%}" for k in pp]],
        ["max DD / skew", *[f"{pp[k]['max_dd']:.0%} / {pp[k]['skew']:.2f}" for k in pp]], ["costs p.a. / turnover", *[f"{pp[k]['cost_ann']:.1%} / {pp[k]['turnover_ann']:.0f}×" for k in pp]],
        ["residual vs long RP (beta)", *[f"{pp[k]['residual_sharpe']:.2f} ({pp[k]['beta']:.2f})" for k in pp]], ["2× / 3× costs", *[f"{pp[k]['net_sharpe_2x_cost']:.2f} / {pp[k]['net_sharpe_3x_cost']:.2f}" for k in pp]]]))
    S.append('<p class="col">*F9 (equal risk across trend and carry sleeves, buffered) was chosen after seeing 1995–2013, so its VALIDATION is not clean. Status: PROMISING, not ELIGIBLE. '
             "Its sensitivity grid (trend mix 0.3–0.7 × buffer 0–0.2) is flat. <code>config/f9_spec.json</code> freezes it, with kill rules (25% drawdown; drift z < −2 after 252 days) and a conservative monitoring expectation of SR 0.5 at 10% vol. "
             "<code>scripts/paper_futures_step.py</code> runs the simulated paper book from user-supplied pysystemtrade-format data. It uses whole contracts, simulated next-close fills, data guards and checkpoints, and never connects to a broker.</p>")

    # 12
    S.append(h2(12, secs[11]))
    S.append('<ul class="col">' + "".join(f"<li>{x}</li>" for x in [
        "No prospective evidence yet. The futures TEST/HOLDOUT and BTC 2024–26 are now used.",
        "The trend/carry edge has decayed (§8). Forward Sharpe expectation 0.5–0.8, possibly lower.",
        "The edge is cost-sensitive. The cost model is the repository's estimates, not measured fills.",
        "Leverage is 7–11× gross notional. Margin, broker and operational risk are not modelled.",
        "Prop firms: futures firms' intraday-flat rules are incompatible with multi-day trend/carry. Crypto prop rules are unverified because official sites are unreachable.",
        "Not testable with reachable data: microstructure/order flow, options/volatility risk premium, macro events, spot–perp basis, survivorship-free crypto universe.",
        "Universe curation: the futures list is a current practitioner's list, and the crypto set is curated. Both carry mild survivorship bias."]) + "</ul>")

    # 13
    S.append(h2(13, secs[12]))
    S.append('<ol class="col">' + "".join(f"<li>{x}</li>" for x in [
        "Supply updated futures data (2024-04 → today) and run the F9 paper book daily. Review at 6 and 12 months, and compare fills and costs with the model.",
        "Run the CT1 and CT1-LF crypto paper books (spot and perp separately) at 0.30× book as a small diversifying sleeve.",
        "Acquire Binance public data, including delisted symbols, for a survivorship-free crypto universe and real perp basis.",
        "If real fills become available, calibrate slippage per instrument and re-run gen13/14 at measured costs.",
        "Do not repeat: regime/timing layers, weekly crypto cross-sections at 30 bp, MVRV timing, re-tuning on used periods."]) + "</ol>")
    S.append('<pre class="col"><code>python -m pytest -q tests          # 88 tests\nbash scripts/run_v6.sh             # all V6 experiments (re-runs tagged repro)\n'
             'python scripts/v6_registry.py     # v6/V6_HYPOTHESIS_REGISTRY.csv\npython scripts/paper_futures_step.py --data-dir DIR --capital 1000000</code></pre>')
    S.append('<p class="col">Documents: <code>v6/V6_MASTER_PLAN.md</code>, <code>V6_RESEARCH_LOG.md</code>, <code>V6_HYPOTHESIS_REGISTRY.csv</code>, <code>V6_DATA_CATALOG.md</code>, '
             "<code>V6_RESULTS.md</code>, <code>V6_STATISTICAL_AUDIT.md</code>, <code>V6_NEXT_ACTIONS.md</code>.</p>")
    S.append("</main>")
    return "\n".join(S)


def main():
    out = ROOT / "reports" / "v6_research_report.html"
    out.write_text(build())
    print("wrote", out)


if __name__ == "__main__":
    main()
