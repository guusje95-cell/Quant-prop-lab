# Thuis te doen (bijgewerkt 2026-11-01)

Volgorde aanhouden. Alles is papier / simulatie: er worden nergens orders geplaatst.

1. **`git pull`** in de map Quant-prop-lab.
2. **Paper v9.8 starten:** sluit het v96-venster, dubbelklik **`paper_v98_start.bat`** (laat open staan).
3. **NIEUW - CFD paper (bf2.6) weer starten:** dubbelklik **`paper_bf26_start.bat`** (laat open staan, naast v9.8). Draaide eerder maar 4 dagen.
   De hub maakt er automatisch schaduw-accounts van: zonder carry (de eerlijke versie), alleen index-CFD's, alleen crypto-CFD's.
4. **NIEUW - orderboek-logger:** dubbelklik **`book_logger_start.bat`** (laat open staan). Alleen openbare Bybit-data, geen sleutel, geen orders.
   Eerste regel moet zeggen "20 of 20 coins answered".
5. **NIEUW - futures paper:** dubbelklik **`futures_paper_update.bat`**. Plak je Databento-sleutel (blijft alleen in dat venster).
   Hij toont eerst GRATIS de prijs; typ daarna het maximum (bijv. 1) of 0 om niets te kopen. Daarna 1x per dag draaien.
5b. **NIEUW - korte-rente-futures (futures-onderzoek):** **`get_futures_stir.bat`** (zelfde Databento-sleutel). Toont eerst gratis de prijs; typ het maximum dat je wilt uitgeven (of 0). Pusht zelf.
5c. **NIEUW - prijsopgave opties-data:** **`get_options_quote.bat`** (zelfde sleutel). Downloadt en kost NIETS, toont alleen prijzen en pusht die. Daarna beslis jij.
6. **Quant Trading Hub starten:** **`hub_start.bat`** (laat open staan) of eenmalig **`hub_task_scheduler.bat`**.
7. **Dashboard:** **`hub_dashboard.bat`** -> http://localhost:8502
8. **`get_bybit_announcements.bat`**: Bybit listings/delistings voor onderzoek R2 (pusht zelf).
9. **`get_prop_rules.bat`**: officiele regelpagina's; daarna in het dashboard de regels die je echt leest als "verified" vastleggen (URL + citaat).
10. Optioneel: **`get_wiki_attention.bat`**.
11. Na een paar dagen: **`paper_v98_share.bat`** en **`paper_bf26_share.bat`**, en voor futures + logger:
    `git add paper_trading/futures paper_trading/book_logs research_data/databento_live` -> commit -> push.

## Nieuw (1-11): Coinbase-short paper (v9.9-kandidaat R16)
- Alleen **`git pull`** en de hub herstarten (`hub_start.bat`). De hub draait elk uur de job **cbshort_paper**: hij kijkt (openbare
  Coinbase-API, geen sleutel, geen orders) of er een nieuwe coin op Coinbase is gekomen en houdt een paper-short bij in
  `paper_trading/cbshort/`. In het dashboard verschijnt schaduw-account **v98:plus_coinbase_short** naast v9.8. v9.8 zelf verandert niet.
- Af en toe meepushen: `git add paper_trading/cbshort paper_trading/venueshort paper_trading/fdshort paper_trading/addshort paper_trading/hodlershort paper_trading/eventdata research_data/coinbase_listings research_data/upbit_listings` -> commit -> push (die map bevat nu ook `warnings_*.csv`: Upbit-waarschuwingen per coin, voor later onderzoek).
- **Waar zie je het?** Alleen na een HERSTART van de hub (sluit het hub-venster, dubbelklik `hub_start.bat`). Binnen een uur (eerste ingest):
  * Paper Trading -> tab **Shadow accounts**: `v98:plus_coinbase_short`, `v98:venue_sleeve_coinbase`, `v98:venue_sleeve_coinbase_upbit` `v98:venue_coinbase_plus_futures_delisting` **`v99cand:all`** (het nieuwe 'beste portfolio': alles samen) `v99cand:all_plus_add` (ALL + Binance-'Add'-short, R34) en `v99cand:all_plus_add_hodler` (+ HODLer-airdrop-short, R42).
  * Performance -> Source **Paper** -> kies die accounts naast paper:v98.
  * Performance -> Source **Backtest** -> Book **"Crypto v9.9 candidates (best portfolio = ALL)"**: de backtest-curve van alles samen naast v9.8 (standaard: beide met de low-cap-limiet).
  Zolang er geen nieuwe listing is, lopen de schaduwen exact gelijk met v9.8 (de short-sleeve staat dan op 0).

## Nieuw (30-10 avond)
- **`get_prop_rules.bat`** nog een keer: nu ook FundedNext, The5ers, SizeProp, Breakout, HyroTrader-platformpagina's en de BloFin API-docs.
- **`venue_check_blofin.bat`**: welke v9.8-posities op BloFin handelbaar zijn (geen sleutel, geen orders).
- Op brightfunded.com de FAQ 'Can You Trade With an EA?' en weekend/overnight lezen en in het dashboard vastleggen.
- Bij HyroTrader (chat/support) vragen: welke coins zijn verhandelbaar op het Hyro-platform, en worden nieuwe listings snel toegevoegd? (zie research/SUPPORT_EMAILS.md)

Daarna tegen Claude zeggen: "thuis gedaan".

## Later (futures price-action onderzoek, geparkeerd tot na crypto + CFD)
- Push een keer `research_data/dukascopy/XAUUSD_5m.parquet` (goud 5-minuten) als je toch pusht; nodig voor het futures-price-action-onderzoek later.

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
