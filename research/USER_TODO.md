# To do on your PC (when home)

1. **Extra futures roots** (priority order: UB ultra bond, NKD Nikkei, PL platinum, TN ultra 10y, EMD MidCap): double-click `get_futures_extra.bat`.
   - It shows the Databento cost per root first, then downloads roots in that order while the running total stays within the amount you type (~$50 credit left).
   - Then: `git pull --no-edit`, `git add research_data/databento`, `git commit -m "databento extra roots"`, `git push`.
2. **VIX / VXN / VVIX history** (free, CBOE): double-click `get_vix_data.bat`.
   - Then: `git pull --no-edit`, `git add research_data/more2`, `git commit -m "vix data"`, `git push`.
3. **Dukascopy daily history 2003-2026** (free, slow: about 1 hour, resumable): double-click `get_dukascopy_daily.bat`. Needed for the gold/platinum test and the 2003-2010 backcasts.
   - Then: `git pull --no-edit`, `git add research_data/dukascopy_daily`, `git commit -m "dukascopy daily"`, `git push`.
4. Earlier open items: Deribit download (`get_deribit_fast.bat`, then push); check BF spreads for SNX/INJ/HBAR/SUI/OP in MT5; one demo round trip to see whether the commission is per deal or per round trip.
