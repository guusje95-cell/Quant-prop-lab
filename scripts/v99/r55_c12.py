"""R55 / C12 (research/v99/r55_c12_protocol.json, FLAGGED). python scripts/v99/r55_c12.py r55|c12 -> results/v99/<name>.json"""
import json
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts", "scripts/v99", "src"):
    sys.path.insert(0, str(ROOT / p))
import crypto_sleeves as CS
import r54_weiss_grid as G
from qpl.lab.erc import erc_weights


def weiss_ens():
    return sum(G.weiss(p, e) for p in (1, 2) for e in (9, 10, 11)) / 6


def r55():
    import r48_stress as S
    Ev = S.per_event(); idx = S.idx; H = S.V8.copy(); ex = {}
    for k, L in Ev.items():
        H[S.NAMES[k]] = sum((h for _, _, h, _ in L), pd.Series(0.0, index=idx)); ex[S.NAMES[k]] = sum((g for _, _, _, g in L), pd.Series(0.0, index=idx))
    orig = CS.v5_weights; CS.v5_weights = lambda D, sleeves, weiss_scale=0.5: erc_weights(D, sleeves, weiss_scale, 0.5)
    try:
        ref = S.capped(H, ex); r = S.capped(H.assign(**{"Weiss expiry": weiss_ens().reindex(idx).fillna(0.0)}), ex)
    finally:
        CS.v5_weights = orig
    return {"v9.9e (ERC)": ref, "v9.9e + Weiss ensemble": r}


def c12():
    import c10b_true_cap as T, c3_ensembles as E, cfd_book as CB, c1_cfd_port as C
    from qpl.live import cfd_extra as X
    CB.measured_costs()
    BH = pd.read_parquet(ROOT / "results/v99/bf26_sleeves_dump.parquet").drop(columns="port"); idx = BH.index
    R = CB.hourly_returns(idx[-1]).reindex(idx).fillna(0.0); S = X.sleeves(pd.date_range("2021-01-01", idx[-1], freq="h"))
    b = BH.drop(columns=["premium carry", "premium carry BF"]).assign(**{k: v.reindex(idx).fillna(0.0) for k, v in S.items()})
    b = b.assign(**{"trend 4h": E.trend(R, (15, 20, 30)), "alt kimchi": E.altk(R, (0.75, 1.0, 1.25))})
    w1 = G.weiss(1, 10).reindex(idx).fillna(0.0); we = weiss_ens().reindex(idx).fillna(0.0)
    return {"bf2.8 (as built)": C.full(T.book(b, 1.0, 4.0)), "bf2.8, Weiss re-implemented (pre 1h / exit 10)": C.full(T.book(b.assign(**{"Weiss expiry": w1}), 1.0, 4.0)),
            "bf2.8 + Weiss ensemble": C.full(T.book(b.assign(**{"Weiss expiry": we}), 1.0, 4.0))}


if __name__ == "__main__":
    name = sys.argv[1]; out = r55() if name == "r55" else c12()
    print(json.dumps(out, indent=1)); (ROOT / f"results/v99/{name}_combo.json").write_text(json.dumps(out, indent=1))
