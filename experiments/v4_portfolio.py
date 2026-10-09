"""Multi-strategy crypto portfolio with nested validation: weights chosen on 2018-03..2021-12 ONLY, evaluated 2022-01..2023-09.
Components (frozen rules): CT1 on BTC (Bitstamp), CT1 on ETH (mirror ETHUSDT; exploratory-grade data). Candidates for
weighting: BTC-only, equal weight, inverse-vol, min-variance (2-asset closed form) - the selection itself is part of the test."""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qpl.backtesting import vector as VB
from qpl.data import crypto as CD
from qpl.research import crypto_factory as CF, factory as F
from qpl.strategies import crypto as CS
ROOT = Path(__file__).resolve().parents[1]
raw = pd.read_csv(ROOT / "data/raw/dukascopy/crypto/ethusdt/ETHUSDT_D1.csv", sep="\t"); raw.columns = [c.lower() for c in raw.columns]
eth = raw.set_index(pd.DatetimeIndex(pd.to_datetime(raw["time"], utc=True)).as_unit("ns"))[["open", "high", "low", "close"]].astype(float).sort_index()
btc = CD.btc_bars("1D").loc["2014-06-01":]
fb, _ = CF.btc_funding()
fe = pd.Series(0.0001, index=pd.date_range("2017-08-01", "2023-09-12", freq="8h", tz="UTC")); a = CD.funding_binance_2020_2024("ETH")
c = fe.index.intersection(a.index); fe.loc[c] = a.loc[c].to_numpy()
R = pd.DataFrame({"BTC": VB.daily(VB.run(btc, CS.trend_ensemble(btc, {}), 7.0, fb), at="realized")["net"],
                  "ETH": VB.daily(VB.run(eth, CS.trend_ensemble(eth, {}), 7.0, fe), at="realized")["net"]}).dropna()
SEL, TEST = R.loc["2018-03-01":"2021-12-31"], R.loc["2022-01-01":"2023-09-09"]
cov = SEL.cov().to_numpy(); vol = np.sqrt(np.diag(cov))
iv = (1 / vol) / (1 / vol).sum()
inv = np.linalg.inv(cov); mv = inv.sum(axis=1) / inv.sum()
W = {"BTC_only": np.array([1.0, 0.0]), "equal": np.array([0.5, 0.5]), "inverse_vol": iv, "min_variance": np.clip(mv, 0, 1) / np.clip(mv, 0, 1).sum()}
out = {"corr_sel": float(SEL.corr().iloc[0, 1]), "corr_test": float(TEST.corr().iloc[0, 1]), "weights": {k: v.round(3).tolist() for k, v in W.items()}, "sel": {}, "test": {}}
for k, w in W.items():
    out["sel"][k] = VB.stats(SEL @ w); out["test"][k] = VB.stats(TEST @ w)
chosen = max(W, key=lambda k: out["sel"][k]["sharpe"])
out["chosen_on_selection_window"] = chosen
out["chosen_test_sharpe"] = out["test"][chosen]["sharpe"]
out["btc_only_test_sharpe"] = out["test"]["BTC_only"]["sharpe"]
(ROOT / "results/v4_portfolio.json").write_text(json.dumps(out, indent=1, default=float))
F.append({"kind": "analysis", "stage": "portfolio_nested", "result_file": "results/v4_portfolio.json",
          "summary": {"chosen": chosen, "test_sharpe": out["chosen_test_sharpe"], "btc_only_test": out["btc_only_test_sharpe"]}})
print(json.dumps({k: out[k] for k in ("corr_sel", "corr_test", "weights", "chosen_on_selection_window", "chosen_test_sharpe", "btc_only_test_sharpe")}, indent=1))
print({k: (round(out["sel"][k]["sharpe"], 2), round(out["test"][k]["sharpe"], 2), round(out["test"][k]["max_dd"], 2)) for k in W})
