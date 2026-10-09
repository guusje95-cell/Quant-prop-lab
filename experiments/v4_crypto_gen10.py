"""V4 generation 10: BTC directional hypotheses on Bitstamp spot (perp funding model). TRAIN+VALIDATION only."""
from __future__ import annotations
import itertools, json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.research import crypto_factory as CF, factory as F

ROOT = Path(__file__).resolve().parents[1]
H = {
 "C1_TSMOM": (F.Hypothesis("C1_TSMOM", "crypto/trend", "BTC returns are positively autocorrelated over 1-4 month horizons (time-series momentum).",
      "Slow diffusion of information, herding and leverage cycles in a retail-heavy market (Liu & Tsyvinski 2021 'Risks and Returns of Cryptocurrency').",
      "TRAIN net Sharpe < 0.5 or residual vs buy&hold-VT < 0.3 for all variants.", "Bitstamp BTCUSD daily", "lookback {20,60,120} x long/short vs long/flat",
      "vol-targeted buy & hold", "config/promotion_criteria_crypto.json",
      sources=[{"title": "Liu & Tsyvinski (2021) Risks and Returns of Cryptocurrency, RFS", "url": "https://doi.org/10.1093/rfs/hhaa113", "published": "2021", "sample": "2011-2018", "limitations": "weekly data; pre-2019"}], generation=10),
      "tsmom", [dict(lookback=L, long_only=lo) for L, lo in itertools.product([20, 60, 120], [False, True])], "1D"),
 "C2_DONCHIAN": (F.Hypothesis("C2_DONCHIAN", "crypto/breakout", "Breakouts of N-day channels continue in BTC.",
      "Trend-following flows and stop cascades.", "Same as C1.", "Bitstamp BTCUSD daily", "n {20,55} x long/short vs long-only",
      "vol-targeted buy & hold", "config/promotion_criteria_crypto.json", generation=10),
      "donchian", [dict(n=n, long_only=lo) for n, lo in itertools.product([20, 55], [False, True])], "1D"),
 "C3_REVERSAL": (F.Hypothesis("C3_REVERSAL", "crypto/mean reversion", "Extreme 1-hour BTC moves partially reverse over the next 4-12 hours.",
      "Liquidity-driven overshoots (forced liquidations, thin books) revert as liquidity returns.",
      "TRAIN net Sharpe < 0.5 for all variants.", "Bitstamp BTCUSD hourly", "k {3,4} sigma x hold {4,12} h", "zero", "config/promotion_criteria_crypto.json", generation=10),
      "reversal", [dict(k=k, hold=h) for k, h in itertools.product([3, 4], [4, 12])], "1h"),
 "C4_VOL_EXPANSION": (F.Hypothesis("C4_VOL_EXPANSION", "crypto/volatility", "A daily range-expansion bar closing at its extreme predicts continuation over the next 1-5 days.",
      "Volatility clustering plus information arrival; expansion bars mark regime transitions.", "Same as C1.", "Bitstamp BTCUSD daily",
      "x {1.5,2.0} x hold {1,5} days", "vol-targeted buy & hold", "config/promotion_criteria_crypto.json", generation=10),
      "vol_expansion", [dict(x=x, hold=h) for x, h in itertools.product([1.5, 2.0], [1, 5])], "1D"),
}
rows = []
for hid, (hyp, sig, grid, rule) in H.items():
    hyp.register()
    for prm in grid:
        r = CF.evaluate(hyp, sig, prm, rule=rule, stage="gen10_screen")
        t, v = r["periods"]["train"], r["periods"]["validation"]
        rows.append(dict(hid=hid, prm=json.dumps(prm), tr_sh=t["sharpe"], tr_gross=t["gross_sharpe"], tr_resid=t.get("residual_sharpe"),
                         tr_beta=t.get("beta_to_buyhold"), bh_tr=t["buyhold_vt_sharpe"], va_sh=v["sharpe"], va_resid=v.get("residual_sharpe"),
                         bh_va=v["buyhold_vt_sharpe"], turn=t["turnover_ann"], long_t=t["share_time_long"], short_t=t["share_time_short"]))
df = pd.DataFrame(rows); df.to_csv(ROOT / "results" / "v4_crypto_gen10.csv", index=False)
pd.set_option("display.width", 220, "display.max_colwidth", 60)
print(df.round(2).to_string())
