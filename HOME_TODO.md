# Thuis te doen (bijgewerkt 2026-10-30)

Volgorde aanhouden. Alles is gratis, zonder account of sleutel, en plaatst geen orders.

1. **`git pull`** in de map Quant-prop-lab.
2. **Paper v9.8 starten:** sluit het v96-venster, dubbelklik **`paper_v98_start.bat`** (laat open staan). Gebruikt de al gedownloade v96-data.
3. **Quant Trading Hub starten:** dubbelklik **`hub_start.bat`** (laat open staan) of eenmalig **`hub_task_scheduler.bat`** (dan draait hij elke 15 min zonder venster).
4. **Dashboard:** **`hub_dashboard.bat`** -> http://localhost:8502
5. **`get_bybit_announcements.bat`**: Bybit listings/delistings voor onderzoek R2 (pusht zelf).
6. **`get_prop_rules.bat`**: bewaart de officiele regelpagina's van de prop firms (pusht zelf). Daarna in het dashboard (Prop Firm Center -> Rules & sources) de regels die je echt op de site leest als "verified" vastleggen, met URL en letterlijk citaat.
7. Optioneel: **`get_wiki_attention.bat`** (Wikipedia-aandacht, Gen459).
8. Na een paar dagen paper: **`paper_v98_share.bat`** zodat de resultaten in de hub en bij Claude komen.

Daarna tegen Claude zeggen: "thuis gedaan".

## Nog open vragen / beslissingen
- Mails aan HyroTrader / CFT over bots + Nederland (`research/SUPPORT_EMAILS.md`) als die nog niet verstuurd zijn.
- Hub-agenda: 'proposed' items (Weiss volle weging, fill-meting) goedkeuren of niet (`research/hub/agenda.json`).

---
## Eerder (historisch, 2026-10-19)
# To do at home (for Claude's research)

**New (2026-10-19):** double-click `get_more_data.bat`. It takes about 30-60 minutes, needs no account or key, and you push it afterwards (see the window). It covers Coinbase altcoins, the Korean premium, Bitstamp and Fear & Greed; the tests for it are already registered in `config/gen102_protocol.json`.

Double-click each file in the `Quant-prop-lab` folder, wait until it says Done, then push (commands below).

1. **`get_coinbase.bat`**: Coinbase BTC/ETH hourly, about 10-20 min.
   - Used for Gen88, the Coinbase-premium test (`config/gen88_protocol.json`). Its rules are already registered.
2. **`get_binance_extra.bat`**: about 40 more Binance coins, several hours; it keeps the PC awake itself.
   - Used for Gen80, the breadth test: premium carry, cascade and dip-buy on more coins.
3. **`paper_v5_share.bat`**: shares the paper-trading results for the weekly reconciliation check.
4. **Optional:** a Databento futures trial (`get_databento_check_cost.bat` shows the cost first; do not pay without deciding).
   - Used for the index near-misses at futures costs.

**After 1-3:**
```
git pull --no-edit
git add research_data paper_trading
git commit -m "data from home"
git push
```
Then tell Claude: "data is pushed".

**Before buying a CFD challenge:**
- Ask the firm in writing whether crypto CFDs can be swap-free (FundedNext: add-on, +10% fee).
- Ask what the crypto swap rate is.

## Decisions Claude needs from you
1. **Switch paper trading from v5 to v6** (v5 + deleveraging bounce)? Answer yes or no.
2. **Which CFD firm do you want to use?** Ask about swap-free first:
   - FundedNext: swap-free add-on;
   - FTMO and BrightFunded: ask support.
3. **Databento futures trial:** yes or no. It is optional and has a cost, so check that first.
