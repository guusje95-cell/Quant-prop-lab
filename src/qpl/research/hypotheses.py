"""Documented hypotheses (recorded BEFORE testing). Each entry states rationale,
expected behaviour, expected failure conditions and falsification criteria."""

GEN1 = {
    "H1_ORB": {
        "family": "momentum/time-of-day", "markets": "ES, NQ, YM (proxies US500/US100/US30)", "timeframe": "15m",
        "hypothesis": "The direction of the opening range (first 15-60 min of RTH) predicts the direction of the rest of the session.",
        "rationale": "Overnight information is incorporated at the open by large participants whose order flow persists (Zarattini & Aziz 2023 ORB on QQQ); dealer gamma positioning can amplify opening moves.",
        "entry": "Either market entry at the end of the opening range in the direction of the OR candle, or OCO stop orders at OR high/low.",
        "exit": "Stop at opposite OR extreme (or fraction of OR range); optional R-multiple target; flat at 16:00 ET.",
        "risk_model": "Fixed $ risk per trade sized off the stop distance.",
        "expected_failure": "Choppy, mean-reverting sessions; low-volatility regimes; edge decay after publication.",
        "falsification": "Net Sharpe <= 0.3 on TRAIN at baseline costs for all reasonable variants, or result not shared across ES/NQ/YM, or random-direction entries at the same times perform as well.",
    },
    "H2_IM": {
        "family": "momentum/time-of-day", "markets": "ES, NQ, YM", "timeframe": "15m",
        "hypothesis": "The first half-hour return (prior close -> 10:00 ET) predicts the last half-hour return (15:30 -> 16:00).",
        "rationale": "Gao, Han, Li & Zhou (2018, JFE): late-informed traders and infrequent rebalancers (and leveraged-ETF/gamma hedging) trade in the same direction at the close.",
        "entry": "Market at 15:30 ET in the sign of the first half-hour return (optionally only if the 15:00-15:30 return agrees).",
        "exit": "Flat at 16:00 ET.", "risk_model": "Sized on daily volatility.",
        "expected_failure": "Small per-trade edge vs costs; documented weakening post-2015.",
        "falsification": "Net expectancy <= 0 after baseline costs on TRAIN.",
    },
    "H3_NOISE": {
        "family": "momentum/volatility breakout", "markets": "ES, NQ, YM", "timeframe": "15m",
        "hypothesis": "Price escaping a time-of-day volatility 'noise area' around the open signals intraday trend continuation.",
        "rationale": "Zarattini, Aziz & Barbon (2024) 'Beat the Market': intraday demand imbalances (gamma hedging, momentum traders) produce persistent intraday trends once moves exceed normal noise.",
        "entry": "Long when a 30-min check closes above max(open, prev close)*(1+m*sigma_tod), short below the symmetric lower band.",
        "exit": "Band / intraday-mean trailing exit at checks; flat at 16:00.", "risk_model": "Volatility-sized.",
        "expected_failure": "Range-bound low-vol years (e.g. 2017); whipsaw days.",
        "falsification": "Net Sharpe <= 0.3 on TRAIN or edge concentrated in a single year.",
    },
    "H4_OVERNIGHT": {
        "family": "time-of-day/session transition", "markets": "ES, NQ, YM", "timeframe": "15m",
        "hypothesis": "Equity-index futures earn a positive drift overnight, concentrated around the European open.",
        "rationale": "Boyarchenko, Larsen & Whelan (2023, RFS) 'The Overnight Drift': resolution of end-of-day dealer inventory imbalances; Lou, Polk & Skouras (2019) overnight vs intraday returns.",
        "entry": "Long at a fixed evening/overnight time in the CME session.", "exit": "Fixed morning time (<= 09:30 ET); optional ATR stop.",
        "risk_model": "Fixed contracts / ATR-sized.", "expected_failure": "Bear markets, overnight crash gaps; one trade per day means costs are a large share of the edge.",
        "falsification": "Net expectancy <= 0 after costs on TRAIN.",
    },
    "H5_GAPFADE": {
        "family": "mean reversion", "markets": "ES, NQ, YM", "timeframe": "15m",
        "hypothesis": "Moderate opening gaps partially revert toward the prior RTH close in the first hours of trading.",
        "rationale": "Overnight moves on thin liquidity overshoot; liquidity providers fade them at the open.",
        "entry": "After the first 15-min bar, fade a gap of 0.2-1.5 ATR if not yet filled.", "exit": "Target prior close; stop k*ATR; time exit.",
        "risk_model": "Stop-distance sizing.", "expected_failure": "News-driven gaps that trend (earnings seasons, macro shocks).",
        "falsification": "Net expectancy <= 0 after costs on TRAIN.",
    },
}
