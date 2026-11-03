"""H2 (research/v99/h2_protocol.json): BrightFunded deployment grid for bf2.8. Writes results/v99/h2_bf_deploy.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
from qpl.hub import income as IN
PRESET = "BrightFunded Two-Step Classic $200k"


def series():
    f = ROOT / "results/v99/bf28_series.parquet"
    if f.exists():
        return pd.read_parquet(f)["bf2.8"]
    import c10b_true_cap as T, c3_ensembles as E, cfd_book as CB
    from qpl.live import cfd_extra as X
    CB.measured_costs()
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0); S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    b = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    b = b.assign(**{"trend 4h": E.trend(R, (15, 20, 30)), "alt kimchi": E.altk(R, (0.75, 1.0, 1.25))})
    s = T.book(b, 1.0, 4.0); s.to_frame("bf2.8").to_parquet(f); return s


def main():
    unit = series(); rows = []
    plans = {"one account": [{"preset": PRESET, "start_day": 0, "budget": 3}],
             "two accounts (+180 d)": [{"preset": PRESET, "start_day": 0, "budget": 3}, {"preset": PRESET, "start_day": 180, "budget": 3}]}
    for sr in (1.2, 1.48, 1.7):
        sc = dict(IN.SCENARIOS["base"], live_sharpe=sr)
        for pn, plan in plans.items():
            for risk in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
                for stop in (0.4, 0.5, 0.6):
                    r = IN.simulate(unit, sc, plan, risk=risk, stop_frac=stop, n_paths=400)
                    rows.append({"sharpe": sr, "plan": pn, "risk": risk, "stop": stop, "net_2y_mean": round(r["horizon_net_eur_mean"]),
                                 "p10": round(r["horizon_net_eur_p10_p50_p90"][0]), "P_loss": round(r["P_net_loss_over_horizon"], 3)})
    D = pd.DataFrame(rows); out = {"choice": {}, "grid": rows}
    for pn in plans:
        c = D[(D.sharpe == 1.48) & (D.plan == pn) & (D.P_loss <= 0.25)].sort_values("net_2y_mean").iloc[-1]
        g = lambda sr: D[(D.sharpe == sr) & (D.plan == pn) & (D.risk == c.risk) & (D.stop == c.stop)].iloc[0][["net_2y_mean", "p10", "P_loss"]].to_dict()
        out["choice"][pn] = {"risk": float(c.risk), "stop": float(c.stop), "at 1.48": g(1.48), "at 1.2": g(1.2), "at 1.7": g(1.7),
                             "risk 1.5 / 0.5 at 1.48": D[(D.sharpe == 1.48) & (D.plan == pn) & (D.risk == 1.5) & (D.stop == 0.5)].iloc[0][["net_2y_mean", "p10", "P_loss"]].to_dict()}
    print(json.dumps(out["choice"], indent=1, default=str)); (ROOT / "results/v99/h2_bf_deploy.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
