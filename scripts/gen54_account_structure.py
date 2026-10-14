"""Gen54a: prop ACCOUNT STRUCTURE for steadier monthly income. Strategy fixed: C* + BTC leads (Gen53), challenge 1.0x /
funded 0.4x, replayed on real hourly prices 2022-2026. Each program runs 24 months from a start date (every 15 days);
accounts can start together or staggered; each account re-buys after a fail up to its own budget of 5.
Writes results/gen54_account_structure.csv."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import gen52_optimize as G
import gen52_extra_check as X
from qpl.lab import propfirms as PF, strategies as S

cs = S.CStarTrend(); sig = cs.signal(G.CR, {**cs.defaults(), "btc_leads": True})
w, _ = G.backtest(sig, 30, 0.0)
FIRM = {"CFT": PF.PRESETS["Crypto Fund Trader 1-Phase $100k"], "FTMO": PF.PRESETS["FTMO 2-Step $100k"]}
SER = {}
for k, f in FIRM.items():
    hc = X.hourly(w, 1.0, 0, 0, f.daily_loss); hf = X.hourly(w, 0.4, 0, 0, f.daily_loss)
    SER[k] = (hc, hf)
idx = SER["CFT"][0].index
cal = ((idx - idx[0]).days).to_numpy()


def account_cash(firm, start_row, end_row):
    hc, hf = SER[firm]
    rc = [hc[c].to_numpy() for c in ("net", "worst", "best")]; rf = [hf[c].to_numpy() for c in ("net", "worst", "best")]
    led = PF._ledger(*rc, *rf, cal, start_row, end_row, FIRM[firm], 5)
    cash = np.diff(np.concatenate([[0.0], led["wealth"]]))
    return pd.Series(cash, index=idx[start_row:end_row])


STRUCTURES = {
    "1 x CFT": [("CFT", 0)],
    "3 x CFT, same day": [("CFT", 0), ("CFT", 0), ("CFT", 0)],
    "3 x CFT, staggered 0/2/4 months": [("CFT", 0), ("CFT", 61), ("CFT", 122)],
    "1 x FTMO": [("FTMO", 0)],
    "1 CFT + 1 FTMO, same day": [("CFT", 0), ("FTMO", 0)],
    "2 CFT + 2 FTMO, staggered 0/1/2/3 months": [("CFT", 0), ("FTMO", 30), ("CFT", 61), ("FTMO", 91)],
    "6 accounts (3 CFT + 3 FTMO), staggered every month": [("CFT", 0), ("FTMO", 30), ("CFT", 61), ("FTMO", 91), ("CFT", 122), ("FTMO", 152)],
}
rows = []
H = 730
starts = [s for s in range(0, len(idx), 15) if cal[-1] - cal[s] >= H]
for name, accts in STRUCTURES.items():
    res = []
    for s in starts:
        end = int(np.searchsorted(cal, cal[s] + H))
        tot = pd.Series(0.0, index=idx[s:end])
        for firm, off in accts:
            a = int(np.searchsorted(cal, cal[s] + off))
            if a < end:
                tot = tot.add(account_cash(firm, a, end), fill_value=0.0)
        m = tot.groupby(np.arange(len(tot)) // 30.4).sum()              # program months 0..23
        later = m.iloc[6:]                                               # months 7-24 (after the first challenges)
        roll3 = m.rolling(3).sum().iloc[6:]
        res.append({"net": tot.sum(), "fees": -tot[tot < 0].sum(), "pos_months": (later > 0).mean(), "payout_months": (later > 0).mean(),
                    "avg_month": later.mean(), "median_month": later.median(), "worst_3m": roll3.min(), "profit": tot.sum() > 0})
    r = pd.DataFrame(res)
    row = {"structure": name, "accounts": len(accts), "programs": len(r), "net_avg": r.net.mean(), "net_p10": r.net.quantile(0.1),
           "net_p50": r.net.median(), "fees_avg": r.fees.mean(), "P_profit": r.profit.mean(), "months7_24_with_net_income": r.pos_months.mean(),
           "avg_monthly_income_m7_24": r.avg_month.mean(), "median_monthly_income_m7_24": r.median_month.mean(), "worst_3_months_avg": r.worst_3m.mean(),
           "net_per_account": r.net.mean() / len(accts)}
    rows.append(row)
    print(f"{name:52s} net avg {row['net_avg']:8.0f} p10 {row['net_p10']:8.0f} P(profit) {row['P_profit']:.0%} | months with income {row['months7_24_with_net_income']:.0%} "
          f"| avg/month {row['avg_monthly_income_m7_24']:6.0f} | worst 3 mo {row['worst_3_months_avg']:7.0f} | fees {row['fees_avg']:6.0f}", flush=True)
pd.DataFrame(rows).to_csv(ROOT / "results/gen54_account_structure.csv", index=False)
