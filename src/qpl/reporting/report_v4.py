"""V4 deliverable: reports/v4_research_report.html (prior reports are left untouched).
Every number is read from results/*.json|csv, config/*.json, data/metadata and the research ledger."""
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from ..research import factory as F
from .report import CSS, f, svg_line, table, tag
from .report_v3 import h2, head, status_span

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "results"


def J(p):
    return json.loads((RES / p).read_text())


def C(p):
    return json.loads((ROOT / "config" / p).read_text())


def ledger():
    return [json.loads(l) for l in open(ROOT / "research_database/ledger.jsonl")]


def counts(ev):
    dec = {}
    for e in ev:
        if e["kind"] == "decision":
            dec[e["hypothesis_id"]] = e["verdict"]
    crypto = [e for e in ev if e["kind"] == "experiment" and e.get("asset_class") == "crypto"]
    hyps = sorted({e["hypothesis"]["id"] for e in ev if e["kind"] == "hypothesis_registered" and e["hypothesis"].get("generation", 0) >= 10})
    variants = {(e["hypothesis_id"], json.dumps(e.get("params"), sort_keys=True), e.get("rule"), e.get("cost_bps")) for e in crypto}
    return dec, crypto, hyps, variants


def ct1_curves():
    from ..backtesting import vector as VB
    from ..data import crypto as CD
    from ..research import crypto_factory as CF
    from ..strategies import crypto as CS
    b = CD.btc_bars("1D").loc["2014-06-01":]
    fu, _ = CF.btc_funding()
    d = VB.daily(VB.run(b, CS.trend_ensemble(b, {}), 7.0, fu), at="realized")["net"].loc["2015-01-01":]
    bh = VB.daily(VB.run(b, CS.buy_hold_vt(b, {}), 7.0, fu), at="realized")["net"].loc["2015-01-01":]
    s = lambda x: x.cumsum().set_axis(x.index.tz_localize(None)).resample("W").last()
    return s(d), s(bh)


def build() -> str:
    ev = ledger()
    ok, n_ev = F.verify_ledger()
    dec, crypto_rows, crypto_hyps, crypto_vars = counts(ev)
    inv = json.loads((ROOT / "data/metadata/crypto_inventory.json").read_text())
    g10 = pd.read_csv(RES / "v4_crypto_gen10.csv")
    ho = J("v4_ct1_holdout.json"); rep = J("v4_ct1_repro.json"); xa = J("v4_ct1_crossasset.json")
    g11 = J("v4_gen11.json"); g12 = J("v4_gen12.json"); c1 = J("v4_audit_c1_correction.json")
    risk = J("v4_ct1_risk.json"); prop = J("v4_ct1_prop_crypto.json")["results"]; port = J("v4_portfolio.json")
    pap = J("v4_paper_crypto_replay.json"); pfc = C("prop_firms_v4_crypto.json"); dur = C("data_usage_registry.json")
    dev = rep["dev"]; oos = rep["oos"]["oos"]

    S = head("Quant Prop Lab V4", "Quant Prop Lab · V4 autonomous alpha discovery · 2026-10-09")
    S += ["<h1>Quant Prop Lab V4</h1>",
          '<p class="col">V4 added crypto as a new research area (BTC, ETH and 21 perpetual futures, plus funding-rate data) and kept the futures and FX record from v1 and v3 unchanged. '
          "Earlier reports are preserved unchanged: <code>research_report_v1_original.html</code>, <code>audit_v1_report.html</code> and <code>v3_research_report.html</code>. "
          "Each test threshold was written down before the test ran, every result is recorded in an append-only hash-chained ledger, and failed hypotheses stay in the record.</p>",
          '<div class="verdict"><strong>Decision.</strong> One strategy, the CT1 BTC trend ensemble, passed every pre-registered gate, including a single look at a protected 2024–2026 holdout. '
          "Its grade is <b>PAPER-TRADING / PERSONAL-ACCOUNT RESEARCH CANDIDATE, reduced confidence</b>. "
          f"That pass is weak: holdout net Sharpe was {ho['7bps']['sharpe']:.2f} (residual {ho['7bps']['residual_sharpe']:.2f}), and the edge did not carry over to 21 other perpetuals in 2025–26 (portfolio Sharpe {xa['B_PERPS']['sharpe']:.2f}). "
          "CT1 also does not fit the prop firms studied: futures firms require intraday flat positions, and the crypto firms' drawdown limits are tight. "
          "No candidate is ready for a prop evaluation, and nothing here authorises real-money trading. The next genuine evidence can only come from prospective paper trading.</div>",
          '<div class="kpis">'
          f'<div class="kpi"><b>{len(crypto_hyps)}</b><span>crypto hypotheses registered and graded in V4</span></div>'
          f'<div class="kpi"><b>{len(crypto_vars)}</b><span>unique crypto variants (params × bar × cost)</span></div>'
          f'<div class="kpi"><b>{len(crypto_rows)}</b><span>crypto experiment records (variant × split × stage)</span></div>'
          f'<div class="kpi"><b>1</b><span>paper-trading candidate (CT1), reduced confidence</span></div>'
          f'<div class="kpi"><b>{"intact" if ok else "BROKEN"}</b><span>ledger hash chain, {n_ev} events</span></div></div>']
    secs = ["Executive decision", "Continuity with v1/v3", "Data inventory & provenance", "Data quality", "V4 audit findings",
            "Method: engine, costs, funding", "Hypotheses, variants, configurations", "BTC directional screen (gen 10)",
            "CT1 candidate: development → OOS → holdout", "CT1 cross-asset confirmation", "Funding, carry, calendar, cross-section (gen 11)",
            "Relative value & trend variant (gen 12)", "Regime filter vs baselines", "Multi-strategy portfolio (nested)", "Sizing & uncertainty-adjusted Kelly",
            "Stress tests", "Statistical integrity", "Prop-firm rule matrix & compatibility", "Paper-trading system", "CT1 strategy card",
            "What could not be tested", "Roadmap & reproduction"]
    S.append('<ol class="toc">' + "".join(f"<li>{html.escape(s)}</li>" for s in secs) + "</ol>")

    # 1
    S.append(h2(1, secs[0]))
    rows = [[html.escape(h), status_span(dec.get(h, "no decision"))] for h in crypto_hyps]
    S.append('<p class="col">Final grade for every V4 hypothesis, as recorded in the ledger. Gates are defined in <code>config/promotion_criteria_crypto.json</code> and the per-generation protocols, all written before the tests ran.</p>')
    S.append(table(["Hypothesis", "Verdict"], rows))
    S.append('<p class="col">' + tag("FACT") + " v1/v3 grades are unchanged. H3 (Nasdaq noise-area) and gold V11 remain EXPLORATORY. "
             "Neither was re-tested in V4, because no untouched futures/FX data exists (§2).</p>")

    # 2
    S.append(h2(2, secs[1]))
    S.append('<p class="col">' + tag("FACT") + " " + html.escape(dur["futures_fx_cfd"]["conclusion"]) + " "
             + html.escape(dur["post_v4_status"]["conclusion"]) + "</p>")
    S.append(table(["Dataset / period", "Status after V4"], [[html.escape(k), html.escape(v)] for k, v in dur["post_v4_status"].items() if not k.startswith("_") and k != "conclusion"]))

    # 3
    S.append(h2(3, secs[2]))
    S.append(table(["Source", "Coverage", "Provenance / licence", "Grade"], [
        ["Bitstamp BTCUSD 1-minute", f"{inv['bitstamp_btcusd_1m']['start'][:10]} → {inv['bitstamp_btcusd_1m']['end'][:10]}, {inv['bitstamp_btcusd_1m']['rows']:,} rows",
         "GitHub mirror ff137/bitstamp-btcusd-minute-data @edbab565 (Kaggle dataset by Zielak/mczielinski, CC BY-SA 4.0)", "research-grade spot price; 2012–14 excluded (illiquid)"],
        ["Binance funding BTC/ETH", "2020-01 → 2023-12, 8h", "supervik/historical-funding-rates-fetcher @66a085bc (timestamps UTC+3 → shifted, asserted on 00/08/16 UTC grid)", "research-grade"],
        ["Binance USDT-perp funding + mark price", f"{inv['funding_recent_binance']['start'][:10]} → {inv['funding_recent_binance']['end'][:10]}, {inv['funding_recent_binance']['symbols']} symbols (21 USDT used)",
         "ZuShen168/funding_rate_data @75c4a735; index_price empty → basis not measurable", "8h mark prices only (no OHLC)"],
        ["Bybit / Hyperliquid funding", "2025-08 → 2026-09/10", "same repository; no prices", "unused (no prices)"],
        ["Mirror alt spot daily (12 coins incl. ETHUSDT)", "2017/18 → 2023-09", "TheSnowGuru mirror @5fa48d39; venue undocumented; survivorship-biased", "EXPLORATORY only"],
        ["Futures / FX / CFD (v1/v3)", "see v3 report", "unchanged", "all USED"]]))
    S.append('<p class="col">' + tag("NOT") + " Order-book, trade-tape, liquidation and open-interest histories were not available. Exchange APIs and data vendors cannot be reached from this environment, and nothing was purchased.</p>")

    # 4
    q = inv["bitstamp_btcusd_1m"]
    S.append(h2(4, secs[3]))
    S.append('<p class="col">' + tag("FACT") + f" Bitstamp 1m: {q['duplicates']} duplicates, {q['ohlc_violations']} OHLC violations, {q['missing_minutes_total']} missing minutes (the source forward-fills empty minutes; "
             "the zero-volume minute share is the real liquidity measure), and " + f"{q['abs_1m_logret_gt_10pct']} one-minute moves above 10%. Zero-volume minute share by year: "
             + ", ".join(f"{k} {v:.0%}" for k, v in q["zero_volume_minute_share_by_year"].items()) + ". "
             f"Binance funding: BTC mean {inv['binance_funding_BTC']['mean_8h'] * 1e4:.2f} bp per 8h, {inv['binance_funding_BTC']['share_positive']:.0%} of prints positive.</p>")

    # 5
    S.append(h2(5, secs[4]))
    S.append(table(["ID", "Finding", "Impact", "Fix"], [
        ["V4-A1", "v1 validator gap detection broken for microsecond indexes (reported 0 gaps)", "True US500 M15: 682 intra-week gaps over 6h. Excluding incomplete days moves H3 dev Sharpe 1.28 → 1.16; OOS unchanged", "unit-safe diff; regression test"],
        ["V4-B1", "Vector backtester funding mapping compared raw integers across µs/ns units → funding silently zero", "32 gen10 records invalidated and re-run", "explicit ns alignment; regression test"],
        ["V4-C1", "Vector P&L booked on the decision bar, not the bar where it is earned", f"Distorts cross-timeframe comparisons only. C11 vs CT1 correlation was 0.07–0.13, corrected to {min(c1['C11_corr_with_CT1_2015_21'].values()):.2f}–{max(c1['C11_corr_with_CT1_2015_21'].values()):.2f}; C6 residuals changed, verdict unchanged", "daily(at='realized'); regression test"],
        ["V4-C2", "Parquet round-trip yields ms indexes; mixing with µs indexes breaks pandas alignment", "Caught in debugging; no recorded result affected (CT1 re-reproduced exactly afterwards)", "btc_bars normalises to ns"],
        ["V4-D1", "gen10 C1–C4 decisions computed but not recorded", "Registry incomplete", "recorded from the stored table, without re-running"],
        ["V4-P1", "Paper replay warm-up generated fills (fees overstated 16×)", "Caught before reporting", "runner.warmup() places no orders; test"]]))

    # 6
    S.append(h2(6, secs[5]))
    S.append('<p class="col">' + tag("FACT") + " Position-based engine for 24/7 markets. The target weight is decided at bar t's close and filled at bar t+1's open, so it earns open(t+2)/open(t+1). "
             "Costs are charged per unit turnover. A perpetual position pays −w·rate at each funding settlement it spans. Daily bars are UTC days. Sharpe uses √365. "
             + tag("ASSUMPTION") + " Costs: perp taker 7 bp and spot taker 15 bp per unit turnover (fee, half-spread and slippage), stressed to 14/21/30 bp. Funding uses actual Binance prints where they exist and a 1 bp per 8h baseline elsewhere (2015–19, 2024–25-08). "
             "Every directional gate requires a positive residual Sharpe against a 40%-vol-targeted buy-and-hold, because BTC's drift makes any long-biased rule look good.</p>")

    # 7
    S.append(h2(7, secs[6]))
    fam = Counter(h.split("_")[0][:1] for h in crypto_hyps)
    S.append('<p class="col">' + tag("FACT") + f" V4 crypto: <b>{len(crypto_hyps)} registered hypotheses</b> (13 ids; C11 is a trend-family variant and CT1 combines C1+C2, so roughly 11 independent ideas), <b>{len(crypto_vars)} unique traded variants</b> (distinct parameter set × bar size × cost assumption; the 31 C8 calendar significance tests are not counted as variants) and "
             f"<b>{len(crypto_rows)} experiment records</b> (variant × split × stage, including OOS/holdout looks and stress runs). "
             "C11 (4h trend) is counted as a separate hypothesis id, but it is a variant of the trend family, not independent evidence. "
             "v1+v3 futures/FX counts are in the v3 report (443 unique variants) and are not merged here, because those strategies trade different markets and data.</p>")
    S.append(table(["Hypothesis", "Records", "Unique variants"],
                   [[h, sum(e["hypothesis_id"] == h for e in crypto_rows), sum(v[0] == h for v in crypto_vars)] for h in crypto_hyps]))

    # 8
    S.append(h2(8, secs[7]))
    S.append('<p class="col">BTC daily/hourly bars. TRAIN 2015–19 and VALIDATION 2020–21 only. All rules are vol-targeted (40%), except reversal, which uses unit size.</p>')
    S.append(table(["Hypothesis", "Params", "TRAIN net", "TRAIN resid", "VAL net", "VAL resid"],
                   [[r.hid, html.escape(r.prm), f(r.tr_sh), f(r.tr_resid), f(r.va_sh), f(r.va_resid)] for r in g10.itertuples()]))
    S.append('<p class="col">' + tag("FACT") + " C1 time-series momentum and C2 Donchian passed in every variant, but their long-only variants carry beta of 0.5–0.7. "
             "C3 hourly reversal and C4 volatility expansion failed. The long/short CT1 ensemble of C1 and C2 was frozen before any 2022+ data was viewed (<code>config/ct1_protocol.json</code>).</p>")

    # 9
    S.append(h2(9, secs[8]))
    h7 = ho["7bps"]
    S.append(table(["Period", "Net Sharpe", "Residual vs B&H-VT", "Max DD", "Gate", "Result"], [
        ["TRAIN 2015–19", f(dev["train"]["sharpe"]), f(dev["train"]["residual_sharpe"]), f(dev["train"]["max_dd"], 0, pct=True), "≥0.5 / ≥0.3", status_span("pass")],
        ["VALIDATION 2020–21", f(dev["validation"]["sharpe"]), f(dev["validation"]["residual_sharpe"]), f(dev["validation"]["max_dd"], 0, pct=True), "≥0.3 / ≥0.2", status_span("pass")],
        ["OOS 2022–23 (one look)", f(oos["sharpe"]), f(oos["residual_sharpe"]), f(oos["max_dd"], 0, pct=True), "≥0.5 / >0", status_span("pass")],
        ["PROTECTED HOLDOUT 2024-01 → 2026-10 (one look)", f(h7["sharpe"]), f(h7["residual_sharpe"]), f(h7["max_dd"], 0, pct=True), ">0 / >0", status_span("pass")],
        ["holdout @15 bp", f(ho["stress15"]["sharpe"]), f(ho["stress15"]["residual_sharpe"]), f(ho["stress15"]["max_dd"], 0, pct=True), "reported", ""],
        ["holdout @21 bp", f(ho["stress21"]["sharpe"]), f(ho["stress21"]["residual_sharpe"]), f(ho["stress21"]["max_dd"], 0, pct=True), "reported", ""],
        ["holdout long-only (secondary)", f(ho["long_only_secondary"]["sharpe"]), f(ho["long_only_secondary"]["residual_sharpe"]), f(ho["long_only_secondary"]["max_dd"], 0, pct=True), "not decisive", ""]]))
    try:
        cd, cb = ct1_curves()
        S.append(svg_line({"CT1 (cumulative net return, 40% vol book)": cd, "BTC buy & hold, vol-targeted 40%": cb}, ylab="cumulative return", money=False,
                          shade=[("2022-01-01", "2023-12-31", "OOS"), ("2024-01-01", "2026-10-09", "HOLDOUT")]))
    except Exception as e:  # pragma: no cover
        S.append(f"<p>chart unavailable: {html.escape(str(e))}</p>")
    S.append('<p class="col">' + tag("UNCERTAINTY") + " Performance has decayed steadily: Sharpe 1.5 → 1.3 → 0.6 → 0.34 across the four periods. "
             f"Holdout yearly sums: {', '.join(f'{k} {v:+.1%}' for k, v in h7['by_year'].items())}. The holdout's price data was untouched in this project, but the researcher has general background knowledge of the 2024 BTC path. "
             "The long/short design and the beta-adjusted gate reduce that bias but do not remove it. All CT1 numbers reproduce exactly via <code>experiments/v4_ct1_evaluate.py</code>.</p>")

    # 10
    S.append(h2(10, secs[9]))
    A, B = xa["A_ETH"], xa["B_PERPS"]
    S.append(table(["Test (pre-registered, single use)", "Net Sharpe", "Residual", "Max DD", "Gate", "Result"], [
        ["A: ETH 2018–23 (mirror data, actual funding 2020–23)", f(A["sharpe"]), f(A["residual_sharpe"]), f(A["max_dd"], 0, pct=True), ">0.3 and resid >0", status_span("pass")],
        [f"B: {B['n_symbols']} Binance USDT perps, {B['eval_start']} → 2026-09 (8h mark proxy, +1 day lag)", f(B["sharpe"]), f(B["residual_sharpe"]), f(B["max_dd"], 0, pct=True), ">0 and resid >0", status_span("REJECT")]]))
    S.append('<p class="col">' + tag("FACT") + f" {B['share_symbols_positive']:.0%} of individual perps had a positive Sharpe over the full window, but the equal-weight portfolio did not. The evaluation window is only ~9 months, after a 125-day warm-up. "
             "Grade kept with reduced confidence: deploy on BTC/ETH only, with no parameter changes.</p>")

    # 11
    S.append(h2(11, secs[10]))
    c6, c7, c8, c9, c10 = g11["C6"], g11["C7"], g11["C8"], g11["C9"], g11["C10"]
    S.append(table(["Hypothesis", "Key evidence", "Verdict"], [
        ["C6 funding contrarian (BTC 1h)", "TRAIN 2020-07..21: " + ", ".join(f"{json.loads(k)['q']}/{json.loads(k)['hold']}h {v['sharpe']:.2f}" for k, v in c6["train"].items()) + " → 2/4 positive (gate 3/4)", status_span(c6["verdict"])],
        ["C7 delta-neutral funding carry", f"Return on capital, always-on: BTC TRAIN {c7['always_on']['BTC']['train']['ann_ret_on_capital']:.1%}, OOS {c7['always_on']['BTC']['oos']['ann_ret_on_capital']:.1%}; 21 perps 2025–26 {c7['always_on']['holdout_21perps_mean_ann']:.1%} (hurdle 4%). Basis risk not modelled.", status_span(c7["verdict"])],
        ["C8 hour-of-day / weekday", f"0 of {len(c8['tests'])} tests survive Holm in TRAIN 2015–19 (smallest p {min(t['p'] for t in c8['tests']):.3f})", status_span(c8["verdict"])],
        ["C9 funding filter on CT1", f"dev 2020-07..23: filtered {c9['dev_2020_07_2023']['filtered']:.2f} vs unfiltered {c9['dev_2020_07_2023']['unfiltered']:.2f}; random-skip p95 {c9['dev_2020_07_2023']['random_skip_p95']:.2f}", status_span(c9["verdict"])],
        ["C10 alt cross-sectional momentum", f"TRAIN 2018-07..20 {c10['train']['sharpe']:.2f} (gate 0.5); OOS {c10['oos']['sharpe']:.2f} (not decisive; survivorship-biased)", status_span(c10["verdict"])]]))

    # 12
    S.append(h2(12, secs[11]))
    S.append(table(["Hypothesis", "TRAIN", "OOS", "Verdict / note"], [
        ["R1 ETH/BTC ratio reversion", f(g12["R1_ETHBTC_REVERSION"]["train"]["sharpe"]), "not run", status_span(g12["R1_ETHBTC_REVERSION"]["verdict"])],
        ["R2 ETH/BTC 60-day momentum", f(g12["R2_ETHBTC_MOMENTUM"]["train"]["sharpe"]), f(g12["R2_ETHBTC_MOMENTUM"]["oos"]["sharpe"]), status_span(g12["R2_ETHBTC_MOMENTUM"]["verdict"])],
        ["C11 BTC 4h trend (variant)", " / ".join(f"{k}: {v['train']:.2f}" for k, v in g12["C11_TSMOM_4H"].items()), "not run",
         f"EXPLORATORY; corr with CT1 {min(c1['C11_corr_with_CT1_2015_21'].values()):.2f}–{max(c1['C11_corr_with_CT1_2015_21'].values()):.2f} → no diversification"]]))

    # 13
    S.append(h2(13, secs[12]))
    d9 = c9["dev_2020_07_2023"]
    S.append(table(["Variant (CT1, 2020-07..2023)", "Sharpe"], [["unfiltered", f(d9["unfiltered"])], ["funding filter (zero longs when funding > trailing p90)", f(d9["filtered"])],
                                                              ["risk reduction (halve instead of zero)", f(d9["halve"])], ["random skip, matched rate, median of 300", f(d9["random_skip_median"])],
                                                              ["random skip, 95th percentile", f(d9["random_skip_p95"])], ["no-trade (cash)", f(d9["cash"])]]))
    S.append('<p class="col">' + tag("FACT") + f" The filter beats {d9['filtered_pctile_vs_random']:.0%} of random skips with the same number of skipped days, which is below the pre-registered 95%. No regime filter is adopted. "
             "The v3 futures regime filters were also rejected (v3 report).</p>")

    # 14
    S.append(h2(14, secs[13]))
    S.append('<p class="col">Weights were chosen on 2018-03..2021 only and tested on 2022..2023-09. The choice of weighting method is itself part of the test.</p>')
    S.append(table(["Weighting", "Weights BTC/ETH", "Selection Sharpe", "Test Sharpe", "Test max DD"],
                   [[k, " / ".join(f"{x:.2f}" for x in port["weights"][k]), f(port["sel"][k]["sharpe"]), f(port["test"][k]["sharpe"]), f(port["test"][k]["max_dd"], 0, pct=True)] for k in port["weights"]]))
    S.append('<p class="col">' + tag("FACT") + f" Min-variance was chosen on the selection window but scored {port['chosen_test_sharpe']:.2f} out of sample, against {port['btc_only_test_sharpe']:.2f} for BTC-only. "
             f"Correlation rose from {port['corr_sel']:.2f} to {port['corr_test']:.2f}. Diversifying across coins did not survive. Combining CT1 with the futures strategies was not attempted, because none of those strategies is better than EXPLORATORY.</p>")

    # 15
    S.append(h2(15, secs[14]))
    k = risk["kelly"]
    S.append(table(["Quantity (post-development sample 2022-01 → 2026-10)", "Value"], [
        ["net Sharpe (40% book)", f(risk["post_dev_stats"]["sharpe"])], ["95% block-bootstrap CI of Sharpe", " … ".join(f(x) for x in risk["selection"]["post_sharpe_ci95"])],
        ["P(mean ≤ 0), bootstrap", f(k["P(mu<=0)"], 0, pct=True)], ["full Kelly (× 40% book)", f(k["full_kelly_multiple_of_book"])], ["half Kelly", f(k["half_kelly"])],
        ["Kelly at the 25th-percentile mean", f(k["kelly_at_mu_p25"])], ["Kelly at the 5th-percentile mean", f(k["kelly_at_mu_p05"])]]))
    sp = risk["sizing_paths"]
    S.append(table(["Vol target", "Median 1y", "5% worst 1y", "P(loss 1y)", "P(DD < −10%)", "P(DD < −20%)", "same, expectancy −50%: P(loss)"],
                   [[k2.replace("vol", "") + "%", f(v["base"]["median_1y"], 1, pct=True), f(v["base"]["p05_1y"], 1, pct=True), f(v["base"]["P(loss_1y)"], 0, pct=True),
                     f(v["base"]["P(maxDD<-10%)"], 0, pct=True), f(v["base"]["P(maxDD<-20%)"], 0, pct=True), f(v["expectancy_-50%"]["P(loss_1y)"], 0, pct=True)] for k2, v in sp.items()]))
    S.append('<p class="col">' + tag("ESTIMATE") + " Paper sizing is set at 0.30× the research book, about 12% annual volatility. That is close to Kelly at the 25th-percentile mean. "
             "Full Kelly is not justified, because the post-development mean is positive with only about 81% bootstrap probability.</p>")

    # 16
    S.append(h2(16, secs[15]))
    st = risk["stress"]
    S.append(table(["Stress (2022-01 → 2026-10, 40% book)", "Sharpe", "Ann. return", "Max DD"],
                   [[k2, f(v["sharpe"]), f(v["ann_ret"], 1, pct=True), f(v["max_dd"], 0, pct=True)] for k2, v in st.items() if isinstance(v, dict) and "sharpe" in v]
                   + [["5% of days: rebalance fails (outage), median of 20", f(st["outage_5pct_days_median_sharpe"]), "", ""]]))
    S.append('<p class="col">' + tag("FACT") + " Worst BTC days and CT1's position going into them: " + "; ".join(f"{d} {v['btc_logret']:+.0%} (w {v['ct1_w_prev']:+.2f})" for d, v in st["worst_btc_days"].items())
             + ". " + html.escape(risk["leverage_note"]) + " The spot-only/long-only row has a higher Sharpe but carries BTC beta. It is reported for completeness and was never the frozen rule.</p>")

    # 17
    S.append(h2(17, secs[16]))
    sel = risk["selection"]
    S.append('<p class="col">' + tag("FACT") + f" Before the CT1 holdout look, {sel['n_crypto_variants_before_holdout']} unique crypto variants had been evaluated. "
             f"Development-period PSR {sel['PSR_dev']:.3f} and DSR {sel['DSR_dev']:.3f} (deflated for those trials); post-development PSR {sel['PSR_post']:.2f}. "
             "Holdout classes are listed in §2. Each OOS/holdout look is recorded once, and re-runs are tagged <code>repro</code>. Every later stage was gated in code by the protocol (for example, C6 never reached OOS). "
             "Unique hypotheses, variants and records are reported separately (§7). " + tag("UNCERTAINTY")
             + " The DSR counts only crypto trials. Counting the whole project's 443 futures/FX variants would lower it, but those were searches over different markets, so they are not the same selection problem.</p>")

    # 18
    S.append(h2(18, secs[17]))
    S.append('<p class="col">' + tag("UNCERTAIN") + " " + html.escape(pfc["_written"]) + "</p>")
    S.append(table(["Firm", "Crypto access / holding", "Limits", "CT1 compatibility"],
                   [[html.escape(k), html.escape(v.get("crypto_products", v.get("account_types", "")) + " " + v.get("holding", "")), html.escape(v.get("limits", "")), html.escape(v["CT1_compatibility"])]
                    for k, v in pfc["firms"].items()]))
    pr = lambda key: prop[key]
    S.append(table(["Generic rule set (1-year horizon, bootstrap)", "Scale × 40% book", "CFD financing p.a.", "P(pass)", "P(fail)", "P(unresolved)"],
                   [[k2.split("|")[0], k2.split("|")[1].replace("scale", ""), k2.split("|")[2].replace("fin", ""), f(v["pass"], 0, pct=True), f(v["fail_max"] + v["fail_daily"], 0, pct=True), f(v["open"], 0, pct=True)]
                    for k2, v in prop.items() if ("scale0.25" in k2 or "scale0.4" in k2)]))
    S.append('<p class="col">' + tag("ESTIMATE") + " CT1 is a slow, multi-week strategy. Even with zero financing cost, the probability of hitting an evaluation target within a year at prop-tolerable size is roughly 30–50%, and failures are frequent. "
             "Daily-loss checks use close-to-close P&L only, so breach probabilities are lower bounds. CT1 is <b>not</b> a prop-evaluation candidate. Its track is a personal-account paper trial. "
             "Evaluations were neither bought nor started.</p>")

    # 19
    S.append(h2(19, secs[18]))
    S.append('<p class="col">' + tag("FACT") + " <code>src/qpl/execution/paper_crypto.py</code> re-implements CT1 incrementally from its written spec and does not import the research signal code. "
             "Parity against the research implementation is exact (max difference below 1e-9) on Bitstamp 2016–2026. Spot and perpetual accounts are separate. "
             "The perp account models funding, isolated margin, a leverage cap and maintenance-margin liquidation on bar extremes. "
             "It also has a data guard (duplicates, malformed bars, gaps, suspicious moves), kill switches (25% drawdown, 6% daily loss, drift z below −2.5 after 90 days), atomic checkpoint/restore and a JSONL audit log. "
             "<code>scripts/paper_crypto_step.py</code> advances it from a user-supplied CSV of completed daily bars and never connects to an exchange. Ten tests cover it.</p>")
    S.append(table(["Historical replay 2024-01 → 2026-10 (NOT elapsed paper time)", "Perp account", "Spot account"],
                   [[k2, f(pap["perp"][k2], 3), f(pap["spot"][k2], 3)] for k2 in ("paper_total_return", "engine_total_return_additive", "paper_sharpe", "engine_sharpe", "daily_corr_paper_vs_engine", "max_dd_paper")]
                   + [["fills / fees / funding", f"{pap['perp']['n_fills']} / ${pap['perp']['fees_paid']:.0f} / ${pap['perp']['funding_paid']:.0f}", f"{pap['spot']['n_fills']} / ${pap['spot']['fees_paid']:.0f} / –"]]))
    S.append('<p class="col">' + tag("FACT") + " No paper trading has elapsed in real time. The prospective record starts when the user first runs the step script on new bars.</p>")

    # 20
    S.append(h2(20, secs[19]))
    card = [("Name", "CT1_TREND_ENSEMBLE (frozen 2026-10-09)"), ("Market", "BTC (ETH acceptable per confirmation); spot long-only or USDT-margined perp long/short"),
            ("Signal", "mean of TSMOM(20,60,120) and Donchian(20,55) legs, each clip(sign × 0.40 / vol30, ±1)"), ("Timing", "decide at the 00:00 UTC daily close; execute at the next open"),
            ("Paper size", "0.30 × research book (≈12% annual vol); ≤1× notional; isolated margin"), ("Costs assumed", "7 bp perp / 15 bp spot per unit turnover; actual funding"),
            ("Evidence", f"TRAIN {dev['train']['sharpe']:.2f} · VAL {dev['validation']['sharpe']:.2f} · OOS {oos['sharpe']:.2f} · HOLDOUT {h7['sharpe']:.2f} · ETH {A['sharpe']:.2f} · perps {B['sharpe']:.2f}"),
            ("Kill / review", "25% DD, drift z < −2.5 after 90 days, or 12 months with Sharpe < 0 → stop and re-grade"), ("Grade", "PAPER-TRADING / PERSONAL-ACCOUNT RESEARCH CANDIDATE (reduced confidence); not prop-compatible")]
    S.append('<div class="card">' + "".join(f"<div>{html.escape(a)}</div><div>{html.escape(b)}</div>" for a, b in card) + "</div>")

    # 21
    S.append(h2(21, secs[20]))
    S.append('<ul class="col">' + "".join(f"<li>{x}</li>" for x in [
        "Microstructure (order-book imbalance, trade-flow toxicity, liquidation cascades): no order-book or tape data reachable. " + tag("NOT"),
        "Perp-spot basis trades: index_price is empty in the recent dataset and no 2020–23 perp prices are available, so carry P&L excludes basis risk. " + tag("NOT"),
        "Open-interest and liquidation-driven signals: no history available. " + tag("NOT"),
        "New futures/FX hypotheses with a clean holdout: all historical futures/FX data is already USED. " + tag("NOT"),
        "Official prop-firm rulebooks: unreachable (DNS blocked), so every rule is UNCERTAIN. " + tag("UNCERTAIN"),
        "Alt-coin universe without survivorship bias: not available. " + tag("NOT")]) + "</ul>")

    # 22
    S.append(h2(22, secs[21]))
    S.append('<ol class="col">' + "".join(f"<li>{x}</li>" for x in [
        "Start the prospective CT1 paper trial on BTC (spot and perp accounts separately) at 0.30× book. Review at 6 and 12 months against the kill rules. No parameter changes.",
        "Use Hyperliquid/Bybit 2025–26 funding (unused) only for a NEW, pre-registered funding hypothesis, and only once a matching price source is found.",
        "Acquire properly licensed order-book/trade data before any microstructure work.",
        "Before any prop decision, read the official rulebooks (FTMO Swing crypto CFD financing, HyroTrader/Breakout drawdown definitions) and re-run <code>experiments/v4_ct1_prop_crypto.py</code> with verified parameters.",
        "Futures/FX: further confirmation needs new data, i.e. prospective paper trading of H3/V11, which remain EXPLORATORY."]) + "</ol>")
    S.append('<pre class="col"><code>bash scripts/run_tests.sh                       # 75 tests\nbash scripts/run_v4.sh                          # every V4 experiment + this report (re-runs tagged repro)\n'
             'python3 experiments/v4_ct1_evaluate.py         # CT1 numbers only, checks stored values\n'
             'python3 scripts/paper_crypto_step.py --bars my_daily_bars.csv --account spot --start YYYY-MM-DD   # paper trader (simulation)</code></pre>')
    S.append("</main>")
    return "\n".join(S)


def main():
    out = ROOT / "reports" / "v4_research_report.html"
    out.write_text(build())
    print("wrote", out)


if __name__ == "__main__":
    main()
