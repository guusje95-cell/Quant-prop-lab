# To do on your PC (when home)

1. **Extra futures roots** (Ultra bonds UB/TN, Nikkei NKD, MidCap EMD): double-click `get_futures_extra.bat`.
   - It shows the Databento cost first; it only downloads if the cost is at most the amount you type (~$50 credit left).
   - Then: `git pull --no-edit`, `git add research_data/databento`, `git commit -m "databento extra roots"`, `git push`.
2. **VIX / VXN / VVIX history** (free, CBOE): double-click `get_vix_data.bat`.
   - Then: `git pull --no-edit`, `git add research_data/more2`, `git commit -m "vix data"`, `git push`.
3. Earlier open items: Deribit download (`get_deribit_fast.bat`, then push); check BF spreads for SNX/INJ/HBAR/SUI/OP in MT5; one demo round trip to see whether the commission is per deal or per round trip.
