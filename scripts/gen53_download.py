"""Yahoo daily candles for 54 historically top-20 coins (incl. collapsed ones) -> data/lab/crypto_pit_yahoo_1d.parquet."""
import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import download as DL
COINS = ["BTC-USD","ETH-USD","XRP-USD","BCH-USD","LTC-USD","EOS-USD","XLM-USD","ADA-USD","TRX-USD","BNB-USD","XMR-USD","NEO-USD","DASH-USD","ETC-USD",
         "XEM-USD","ZEC-USD","XTZ-USD","VET-USD","LINK-USD","DOT-USD","SOL-USD","AVAX-USD","DOGE-USD","SHIB-USD","POL28321-USD","LUNC-USD","LUNA20314-USD",
         "FTT-USD","UNI7083-USD","ATOM-USD","ALGO-USD","FIL-USD","ICP-USD","NEAR-USD","APT21794-USD","SUI20947-USD","BSV-USD","CRO-USD","OMG-USD",
         "QTUM-USD","ICX-USD","ONT-USD","BTG-USD","LSK-USD","WAVES-USD","HBAR-USD","THETA-USD","AXS-USD","SAND-USD","MANA-USD","EGLD-USD","KSM-USD","HNT-USD","PEPE24478-USD"]
fr = {}
for s in COINS:
    for k in range(3):
        try:
            fr[s.split("-")[0].rstrip("0123456789")] = DL.yahoo(s, "2017-01-01"); break
        except Exception as e:
            time.sleep(3)
    time.sleep(0.3)
print(len(fr), DL.save(fr, "crypto_pit_yahoo_1d", "1d"))
