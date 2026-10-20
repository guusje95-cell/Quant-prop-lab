"""Gen254 (config/gen254_protocol.json): four more crypto XS ideas in v7. Writes results/gen254.json."""
import json
import numpy as np
import pandas as pd
import v7lab as L
B, END = L.B, L.END
out = {}; save = lambda: json.dump(out, open(L.ROOT / "results/gen254.json", "w"), indent=1)
C = B.coins(); P = B.panel("close", "1D", C).loc[:END]; R = P.pct_change(fill_method=None)
QV = B.panel("quote_volume", "1D", C).loc[:END].replace(0, np.nan)
TB = B.panel("taker_buy_volume", "1D", C).loc[:END]; VV = B.panel("volume", "1D", C).loc[:END].replace(0, np.nan)
met = {c: B.metrics(c) for c in C}
oi = pd.DataFrame({c: m["sum_open_interest_value"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c, m in met.items()}).reindex(P.index)
tt = pd.DataFrame({c: m["sum_toptrader_long_short_ratio"].pipe(lambda z: z.where(z > 0)).resample("1D").last() for c, m in met.items()}).reindex(P.index)
L.judge("A OI growth (low long)", L.perp(L.xs(-np.log(oi / oi.shift(7)))), out); save()
L.judge("B taker imbalance momentum", L.perp(L.xs(((2 * TB - VV) / VV).rolling(7, min_periods=5).mean())), out); save()
L.judge("C Amihud illiquidity", L.perp(L.xs((R.abs() / QV).rolling(30, min_periods=20).mean())), out); save()
L.judge("D top-trader ratio change", L.perp(L.xs(np.log(tt / tt.shift(7)))), out, dev_start=str(tt.dropna(how="all").index[0].date())); save()
