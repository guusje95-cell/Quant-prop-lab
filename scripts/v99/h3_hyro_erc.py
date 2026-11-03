"""H3 (research/v99/h3_protocol.json): HyroTrader deployment grid for v9.9e (ERC). Writes results/v99/h3_hyro_erc.json."""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
from qpl.hub import income as IN


def series():
    f = ROOT / "results/v99/v99e_series.parquet"
    if f.exists():
        return pd.read_parquet(f)["v9.9e"]
    import r48_stress as S, r53b_checks as K
    from qpl.lab.erc import erc_weights
    Ev = S.per_event(); idx = S.idx; H = S.V8.copy(); ex = {}
    for k, L in Ev.items():
        H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
    b, _ = K.with_weights(lambda: K.capped_series(H, ex), lambda D, sleeves, weiss_scale=0.5: erc_weights(D, sleeves, weiss_scale, 0.5))
    b.to_frame("v9.9e").to_parquet(f); return b


def main():
    unit = series(); plan = [{"preset": "HyroTrader Two-Step $200k", "start_day": 0, "budget": 3}]; rows = []
    for sr in (1.65, 2.0, 2.25):
        sc = dict(IN.SCENARIOS["base"], live_sharpe=sr)
        for risk in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
            r = IN.simulate(unit, sc, plan, risk=risk, stop_frac=0.5, n_paths=400)
            rows.append({"sharpe": sr, "risk": risk, "net_2y_mean": round(r["horizon_net_eur_mean"]), "p10": round(r["horizon_net_eur_p10_p50_p90"][0]), "P_loss": round(r["P_net_loss_over_horizon"], 3)})
    D = pd.DataFrame(rows); c = D[(D.sharpe == 2.0) & (D.P_loss <= 0.20)].sort_values("net_2y_mean").iloc[-1]
    out = {"choice at 2.0": c.to_dict(), "grid": rows}
    print(D.to_string(index=False)); (ROOT / "results/v99/h3_hyro_erc.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
