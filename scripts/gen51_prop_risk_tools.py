"""Gen51 (config/gen51_protocol.json): prop-specific risk tools on frozen C*. Writes results/gen51_prop_risk_tools.csv."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import data as D, propfirms as PF, scorecard as SC, strategies as S

cr = D.list_sources()["Binance spot majors (daily, 2017+)"]()
d = SC.run(S.CStarTrend, cr, SC.SETUPS["C* trend + breakout (E2)"])["daily"]
rows = []
for firm in ("Crypto Fund Trader 1-Phase $100k", "FTMO 2-Step $100k", "Crypto Fund Trader 2-Phase $100k"):
    base = PF.PRESETS[firm]
    for tag, f in (("plain C*", base), ("G51a daily stop 75%", PF.replace(base, stop_frac=0.75)),
                   ("G51b cushion scaling", PF.replace(base, cushion_scale=True)),
                   ("G51c both", PF.replace(base, stop_frac=0.75, cushion_scale=True))):
        a = PF.attempts(d, f, 1.0); p = PF.pipeline(d, f, 5, 1, 1.0, 0.4, horizon_days=730)
        row = {"firm": firm, "variant": tag, "pass_per_attempt": a["P_pass"], "fail_daily": a["P_fail_daily"], "fail_max": a["P_fail_max"],
               "median_days_to_pass": a["median_days_to_pass"], "funded_within_5": p["P_funded"], "bought": p["bought"], "fees": p["fees"],
               "payouts": p["paid"], "net_mean": p["net_mean"], "net_p50": p["net_p50"], "net_p10": p["net_p10"], "P_profit": p["P_profit"],
               "funded_breaches": p["funded_breaches"]}
        rows.append(row)
        print(f"{firm:34s} {tag:22s} pass {a['P_pass']:.0%} (daily {a['P_fail_daily']:.0%} max {a['P_fail_max']:.0%}) days {a['median_days_to_pass']:.0f} | "
              f"funded {p['P_funded']:.0%} bought {p['bought']:.1f} net {p['net_mean']:7.0f} p50 {p['net_p50']:7.0f} p10 {p['net_p10']:7.0f} P(profit) {p['P_profit']:.0%}", flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen51_prop_risk_tools.csv", index=False)
