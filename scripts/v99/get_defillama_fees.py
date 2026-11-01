"""Daily fees (and TVL) per coin from DefiLlama's free public API -> research_data/defillama_fees/<COIN>.parquet (columns fees, tvl).
Protocol tokens use the protocol's fees / TVL, L1 / L2 tokens their chain's. Fixed mapping below (written before any test)."""
import json
import time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "research_data/defillama_fees"
PROTOCOL = {"AAVE": "aave", "UNI": "uniswap", "CRV": "curve-finance", "COMP": "compound-finance", "SNX": "synthetix", "SUSHI": "sushi",
            "YFI": "yearn-finance", "LDO": "lido", "DYDX": "dydx", "1INCH": "1inch-network", "RUNE": "thorchain", "GRT": "the-graph", "LINK": "chainlink"}
CHAIN = {"ETH": "Ethereum", "SOL": "Solana", "BNB": "BSC", "AVAX": "Avalanche", "TRX": "Tron", "NEAR": "Near", "ATOM": "Cosmos Hub",
         "DOT": "Polkadot", "ADA": "Cardano", "APT": "Aptos", "SUI": "Sui", "ARB": "Arbitrum", "OP": "Optimism", "ALGO": "Algorand",
         "HBAR": "Hedera", "EGLD": "MultiversX", "XTZ": "Tezos", "STX": "Stacks", "TIA": "Celestia", "ICP": "ICP", "INJ": "Injective",
         "BTC": "Bitcoin", "LTC": "Litecoin", "DOGE": "Dogecoin", "BCH": "Bitcoin Cash", "XRP": "XRPL", "XLM": "Stellar", "FIL": "Filecoin",
         "IMX": "Immutable zkEVM", "KSM": "Kusama", "ZIL": "Zilliqa", "NEO": "Neo", "THETA": "Theta", "ETC": "Ethereum Classic"}


def series(j_list, key_t, key_v):
    return pd.Series({pd.Timestamp(int(x[key_t]), unit="s").normalize(): float(x[key_v]) for x in j_list}) if j_list else pd.Series(dtype=float)


def get(url):
    for i in range(4):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True); log = {}
    for coin, slug in list(PROTOCOL.items()) + list(CHAIN.items()):
        chain = coin in CHAIN
        f = get(f"https://api.llama.fi/overview/fees/{slug.lower().replace(' ', '%20')}?excludeTotalDataChartBreakdown=true&dataType=dailyFees" if chain
                else f"https://api.llama.fi/summary/fees/{slug}?dataType=dailyFees")
        fees = pd.Series({pd.Timestamp(x[0], unit="s").normalize(): float(x[1]) for x in (f or {}).get("totalDataChart") or []}, dtype=float)
        t = get(f"https://api.llama.fi/v2/historicalChainTvl/{slug.replace(' ', '%20')}" if chain else f"https://api.llama.fi/protocol/{slug}")
        tvl = series(t, "date", "tvl") if chain and isinstance(t, list) else series((t or {}).get("tvl") or [], "date", "totalLiquidityUSD") if not chain else pd.Series(dtype=float)
        d = pd.DataFrame({"fees": fees, "tvl": tvl}).sort_index(); d = d[~d.index.duplicated(keep="last")]
        if len(d):
            d.to_parquet(OUT / f"{coin}.parquet")
        log[coin] = {"slug": slug, "kind": "chain" if chain else "protocol", "fees_days": int(fees.notna().sum()), "fees_from": str(fees.index.min()) if len(fees) else None,
                     "tvl_days": int(tvl.notna().sum()), "tvl_from": str(tvl.index.min()) if len(tvl) else None}
        print(coin, log[coin], flush=True); time.sleep(0.5)
    (OUT / "download_log.json").write_text(json.dumps({"downloaded": str(pd.Timestamp.now().floor("s")), "coins": log}, indent=1))


if __name__ == "__main__":
    main()
