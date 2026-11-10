# Live-checklist per firm (opgesteld 2026-11-03)

Alles wat hier staat is voor het moment dat een paper-gate geslaagd is EN jij akkoord geeft. Tot dan draaien alle bots in dry-run
(er gaat nergens een order uit). Live order-versturen is in de code bewust nog NIET gebouwd; dat volgt per firm pas na jouw OK.

## Algemeen (voor elke firm)

**Vóór de start (eenmalig)**
- [ ] Paper-gate van het boek geslaagd (v9.8: ~begin januari; bf2.6/bf2.8: ~half december) en planning-Sharpe nog in lijn.
- [ ] Officiële firm-regels vastgelegd (`get_prop_rules.bat`) en in het dashboard als "verified" gemarkeerd: daily loss, max loss
      (statisch of trailing), consistency, toegestane instrumenten, bots/EA, weekend/overnight, nieuwsregels, landen (NL).
- [ ] Minimaal 2 weken dry-run op hetzelfde platform zonder fouten (`bot_state_*/status.json`: `consecutive_errors` = 0).
- [ ] Noodknop getest: bestand `STOP` in de state-map -> bot sluit alles binnen 5 minuten (zie tests/test_bot_safety.py).
- [ ] PC: stroom-/slaapstand uit, automatische Windows-updates buiten handelsuren, tweede internetverbinding (telefoon-hotspot) bekend.

**Ingebouwde veiligheid (getest, 243 tests)**
- Corrupt state-bestand -> bot herstelt van de back-up (`state.json.bak`), anders start hij vlak.
- Boek of targets onleesbaar -> bot houdt posities kort vast; na **6 uur** zonder geldig boek sluit hij alles.
- Boek ouder dan 6 uur met open posities -> alles sluiten.
- Ongeldige doelwaarden (NaN/inf) -> die coin wordt gesloten, rest gaat door.
- Te grote doelpositie (bug) -> harde bovengrens op de totale positie (dagelijks-vlak: 3x equity x risico; crypto-CFD: 1:5).
- Daily stop -> vlak tot de volgende (UTC-)dag. Kill-switch (`STOP`) -> direct alles sluiten.
- `status.json` per bot: laatste ronde, actie, fout, aantal fouten op rij (de hub / het weekrapport leest dit).

**Dagelijks (2 minuten)**
- [ ] `status.json` van elke bot: `ok: true`, laatste ronde < 10 minuten oud.
- [ ] Equity in het firm-dashboard ~ equity in de bot (verschil > 0,5% van het account = uitzoeken).
- [ ] Afstand tot daily loss en max loss in het dashboard.

**Stoppen (STOP-bestand zetten en mij laten kijken) als**
- 3 of meer fouten op rij, of posities in het dashboard die de bot niet kent.
- Verlies op een dag > 2% van het account (de bot stopt zelf bij 2,5%; dit is de vroege waarschuwing).
- Paper/live loopt > 2 standaardfouten achter de backtest (weekrapport: z < -2).
- De firm verandert regels of vraagt om uitleg over je trading.

## 1. HyroTrader (crypto v9.9e) - prioriteit 1
- Account: Two-Step $200K (Hyro-platform; live Bybit-data, geen Bybit-account nodig).
- Risico **1.5** (H3: met ERC-weging is 1,5 de robuuste keuze; 1,75 alleen bij een duidelijk betere start), daily stop **0.5** van de
  5%-limiet (bot: 2,5% van het startsaldo).
- Regels om op te letten: low-cap/Innovation-coins samen <= 4,5% van het startsaldo (de bot capt dit al), funded notional <= 2x
  (bot: 1,9x), 5% daily / 10% max loss.
- Bot: `bot_v99_dryrun.bat` nu; live pas met de echte Hyro-adapter (wacht op jouw `tools.json` van `hyro_probe.bat`).
- Verwachting (planning ~2,05 in de backtest; **~1,9 met de echte live-vertraging, ~1,95 met de Weiss-timer**, EX-1/EX-1c):
  ~EUR 80-86k gemiddeld over 2 jaar, kans op verlies ~6-7% (simulatie, geen garantie).

## 2. Propr (crypto, Hyperliquid) - prioriteit 2
- Account: $100K; risico **1.0** (trailing drawdown!).
- Regels: hefboom crypto 2x, BTC/ETH/SOL 10x (bot leest de limieten live), fee 0,075% per kant; coins die Hyperliquid niet heeft
  worden overgeslagen.
- Bot: `bot_propr_dryrun.bat` (API-sleutel alleen in het venster typen, leest alleen).
- Verwachting: planning ~1,6.

## 3. BrightFunded (CFD bf2.8) - prioriteit 3
- Account: Two-Step Classic $200K, swap-free add-on. **Eerst navragen: dekt swap-free ook US100/US500?** (zo niet: C13-variant).
- Risico **1.75**, daily stop **0.5** (H2).
- Regels: crypto-CFD hefboom 1:5 (bot capt), geen orders binnen +-6 min rond rood nieuws (`config/news_blackouts.json` bijhouden),
  weekend aanhouden toegestaan.
- Bot: `bot_bf27_mt5_dryrun.bat` (MT5 ingelogd laten; handelt sinds 2026-11-10 het **bf2.8**-boek). Kosten: netto handelen + band
  ($1.000) en de echte BrightFunded-spreads (CN-4) zitten erin.
- Verwachting (planning ~1,55 in de backtest; **~1,4 met de live-vertraging, ~1,45 met de Weiss-timer**): ~EUR 45-50k over 2 jaar
  per account, kans op verlies ~15-18%.

## Audit 2026-11-10: nieuwe punten
- [ ] **Weiss-timer** (laatste vrijdag van de maand, 08:00:0x en 10:00:0x UTC, marktorders): in de dry-run-logs controleren dat de
      orders binnen ~1 minuut na 08:00 en 10:00 staan (`weiss_timer` in de bot-uitvoer). De eerstvolgende: vrijdag 27 november 2026.
- [ ] **Nieuwsblokkades**: `config/news_blackouts.json` wordt nu automatisch gevuld met FOMC (14:00 en 14:30 ET). CPI en
      banencijfers (08:30 ET) met de hand toevoegen in `config/news_manual.json` vanuit de BrightFunded-nieuwskalender.
- [ ] **Snellere live-boekbouwer** (open): de paper-run start om hh:06 en het boek is er pas rond hh:12-15. Elk kwartier
      vertraging kost ~0,15 Sharpe (EX-1), waarvan de Weiss-timer ~0,05-0,07 terugwint. Een live-boekbouwer die om hh:00:30 rekent,
      zou nog ~0,06 per boek winnen. Bouwen vóór de eerste live-maand, eerst naast de paper valideren.
- [x] Bots handelen de juiste kandidaten: MT5 = bf2.8, Hyro/Propr = v9.9e met ERC-weging (was bf2.7 en inverse-vol).

## Later en klein: dagelijks-vlak index-boek (Topstep / FTMO / FundedNext / The5ers)
- Pas na 2-3 maanden dry-run (`bot_dailyflat_mt5_dryrun.bat`, op een MT5-demo).
- Vlak 15:55-18:00 ET en in het weekend (CFD-firms: optioneel tot 16:55 met `--cfd-1655`, geen voordeel na netto kosten).
- Topstep: alleen via de officiële TopstepX-API (adapter nog niet gebouwd); vermoedelijk geen VPS/VPN toegestaan; NL-toelating checken.
- Verwachting: planning ~0,5-0,6; doel is spreiding naast crypto (correlatie ~0), niet het hoofdinkomen.

## Volgorde en geld
1. HyroTrader (1 account). 2. Na de eerste uitbetaling of 2 maanden goed draaien: Propr. 3. BrightFunded zodra de CFD-gate en de
swap-vraag rond zijn. Tweede accounts pas na een uitbetaling (de accounts bewegen samen: correlatie crypto/CFD ~0,75).
