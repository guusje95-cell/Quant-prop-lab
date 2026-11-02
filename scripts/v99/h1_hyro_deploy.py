"""H1 (research/v99/h1_protocol.json): HyroTrader deployment grid for the v9.9 candidate. Writes results/v99/h1_hyro_deploy.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from qpl.hub import income as IN


def main():
    unit = pd.read_parquet(ROOT / "results/v99/m1_series_bybit.parquet")["capped"]
    plan = [{"preset": "HyroTrader Two-Step $200k", "start_day": 0, "budget": 3}]; rows = []
    for sr in (1.6, 1.95, 2.2):
        sc = dict(IN.SCENARIOS["base"], live_sharpe=sr)
        for risk in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
            for stop in (0.4, 0.5, 0.6):
                r = IN.simulate(unit, sc, plan, risk=risk, stop_frac=stop, n_paths=400)
                rows.append({"sharpe": sr, "risk": risk, "stop": stop, "net_2y_mean": round(r["horizon_net_eur_mean"]), "p10": round(r["horizon_net_eur_p10_p50_p90"][0]),
                             "p50": round(r["horizon_net_eur_p10_p50_p90"][1]), "P_loss": round(r["P_net_loss_over_horizon"], 3)})
    D = pd.DataFrame(rows); c = D[(D.sharpe == 1.95) & (D.P_loss <= 0.20)].sort_values("net_2y_mean").iloc[-1]
    cur = D[(D.risk == 1.5) & (D.stop == 0.5)]
    out = {"choice": {"risk": float(c.risk), "stop": float(c.stop), "at 1.95": c[["net_2y_mean", "p10", "p50", "P_loss"]].to_dict(),
                      "at 1.6": D[(D.sharpe == 1.6) & (D.risk == c.risk) & (D.stop == c.stop)].iloc[0][["net_2y_mean", "p10", "P_loss"]].to_dict(),
                      "at 2.2": D[(D.sharpe == 2.2) & (D.risk == c.risk) & (D.stop == c.stop)].iloc[0][["net_2y_mean", "p10", "P_loss"]].to_dict()},
           "current risk 1.5 / stop 0.5": cur.to_dict("records"), "grid": rows}
    print(json.dumps({k: out[k] for k in ("choice", "current risk 1.5 / stop 0.5")}, indent=1, default=str))
    (ROOT / "results/v99/h1_hyro_deploy.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
