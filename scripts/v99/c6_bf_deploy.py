"""v9.9 C6 (research/v99/c6_protocol.json): BrightFunded deployment grid for the bf2.7 candidate. Writes results/v99/c6_bf_deploy.json."""
import json
import sys
import time
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import c1_cfd_port as C
from qpl.hub import income as IN
from qpl.live import cfd_extra as X
PRESET = "BrightFunded Two-Step Classic $200k"


def main():
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    base = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    unit = C.book(base)
    plans = {"one account": [{"preset": PRESET, "start_day": 0, "budget": 3}],
             "two accounts (+180 d)": [{"preset": PRESET, "start_day": 0, "budget": 3}, {"preset": PRESET, "start_day": 180, "budget": 3}]}
    rows = []; t0 = time.time()
    for sr in (1.0, 1.36, 1.7):
        sc = dict(IN.SCENARIOS["base"], live_sharpe=sr)
        for pn, plan in plans.items():
            for risk in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
                for stop in (0.4, 0.5, 0.6):
                    r = IN.simulate(unit, sc, plan, risk=risk, stop_frac=stop, n_paths=400)
                    rows.append({"sharpe": sr, "plan": pn, "risk": risk, "stop": stop, "net_2y_mean": round(r["horizon_net_eur_mean"]),
                                 "p10": round(r["horizon_net_eur_p10_p50_p90"][0]), "p50": round(r["horizon_net_eur_p10_p50_p90"][1]),
                                 "P_loss": round(r["P_net_loss_over_horizon"], 3), "days_to_cash": r["median_days_to_first_cash"]})
        print(sr, round(time.time() - t0), flush=True)
    D = pd.DataFrame(rows)
    pick = {}
    for pn in plans:
        cand = D[(D.sharpe == 1.36) & (D.plan == pn) & (D.P_loss <= 0.25)]
        if len(cand):
            b = cand.sort_values("net_2y_mean").iloc[-1]
            at1 = D[(D.sharpe == 1.0) & (D.plan == pn) & (D.risk == b.risk) & (D.stop == b.stop)].iloc[0]
            pick[pn] = {"risk": float(b.risk), "stop": float(b.stop), "at 1.36": b[["net_2y_mean", "p10", "p50", "P_loss"]].to_dict(),
                        "same cell at 1.0": at1[["net_2y_mean", "p10", "P_loss"]].to_dict(), "at 1.7": D[(D.sharpe == 1.7) & (D.plan == pn) & (D.risk == b.risk) & (D.stop == b.stop)].iloc[0][["net_2y_mean", "p10", "P_loss"]].to_dict()}
    cur = D[(D.risk == 2.0) & (D.stop == 0.5)]
    out = {"choice (decision rule)": pick, "current setting risk 2.0 / stop 0.5": cur.to_dict("records"), "grid": rows}
    print(json.dumps({k: out[k] for k in ("choice (decision rule)", "current setting risk 2.0 / stop 0.5")}, indent=1, default=str))
    (ROOT / "results/v99/c6_bf_deploy.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
