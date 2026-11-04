# Businessplan prop-accounts (2026-11-04, op basis van de gevalideerde cijfers, VAL-5)

Alles hieronder zijn **simulaties**, geen beloftes. Ze gebruiken de planning-Sharpe (backtest min de "geluk-correctie" voor 2.038 tests),
de regels van de firms zoals bekend (nog niet allemaal officieel geverifieerd) en geen belasting. Echte resultaten wijken af.

## 1. Welke boeken, welke firms

| Prioriteit | Firm | Boek | Planning-Sharpe | Status |
|---|---|---|---|---|
| 1 | HyroTrader (Hyro-platform, $200K Two-Step) | crypto v9.9e | ~2.0 | paper-gate ~begin januari |
| 2 | Propr ($100K, Hyperliquid) | crypto (HL-versie) | ~1.6 | na HyroTrader |
| 3 | BrightFunded ($200K Classic, swap-free) | CFD bf2.8 | ~1.55 | CFD-gate ~half december + swap-vraag |
| - | Topstep / FTMO e.d. | dagelijks-vlak index-boek | ~0 na deflatie | alleen paper / dry-run |
| - | futures-swing firm (PropShopTrader) | futures + CX4 | ~0.7-0.8 | MBT/MET niet bevestigd; laag |

## 2. Verwachting per account over 2 jaar (simulaties)

| Account | Risico | Gemiddeld netto | Slechte 10% (p10) | Kans op verlies | Bron |
|---|---|---|---|---|---|
| HyroTrader $200K (planning 2.0) | 1.75 | ~EUR 89k | ~EUR 8k | ~6% | H3 |
| idem bij tegenvaller (planning 1.65) | 1.5 | ~EUR 68k | ~EUR 3k | ~9% | H3 |
| BrightFunded $200K (planning 1.48-1.7) | 1.75 | ~EUR 54-69k | ~EUR -4k | ~12-16% | H2 |
| Propr 3 x $100K (ranking-model, optimistischer) | 1.0 | ~USD 71k | ~USD 8k | ~8% | M1 (Gen332-ledger) |

Lees dit zo: het **gemiddelde** is wat je over veel "levens" zou verdienen; in 1 op 10 gevallen is het niet meer dan de p10.
De accounts hangen samen (crypto vs CFD ~0,75): een slechte crypto-periode is meestal ook een slechte CFD-periode.

Monte Carlo (VAL-5, 1 jaar bij 10% volatiliteit, met het planning-rendement): crypto mediaan max drawdown -5,8% (1 op 20: -10%),
kans op een verliesjaar 3%; CFD -6,5% (1 op 20: -12%), verliesjaar 8%.

## 3. Kosten en geld dat je moet vrijhouden

| Post | Bedrag | Opmerking |
|---|---|---|
| HyroTrader $200K Two-Step | ~USD 969 | terug bij de eerste uitbetaling |
| BrightFunded $200K Classic | ~EUR 700-1.000 | + swap-free add-on; terug bij uitbetaling (check) |
| Propr $100K | prijs nog checken | per account |
| Reserve voor 1 herkansing per firm | ~zelfde bedrag nog eens | een challenge kan mislukken (kans ~10-20%) |
| Databento (futures-paper) | centen per dag | |

**Aanrader:** start met alleen HyroTrader en houd ~USD 2.000 vrij (challenge + 1 herkansing). Pas na de eerste uitbetaling volgende firms.

## 4. Tijdlijn

| Wanneer | Stap | Voorwaarde |
|---|---|---|
| nu - december | paper + schaduwen + dry-run bots, weekrapport | jij: draaien en wekelijks pushen |
| half december | CFD-gate (bf2.6 / bf2.8) | z niet < -2, geen bot-fouten |
| begin januari | crypto-gate (v9.8 56 dagen, v9.9e-schaduw) | idem; daarna jouw akkoord |
| januari | HyroTrader-challenge kopen, `hyro_probe.bat`, echte Hyro-koppeling (eerst dry-run op het echte account) | live-checklist |
| ~maart (na eerste uitbetaling of 2 goede maanden) | Propr | |
| na de CFD-gate + swap-antwoord | BrightFunded | |
| Q1-Q2 2027 | nieuwe event-tests (collectors), mogelijke vervanging van zwakke sleeves | vooraf vastgelegd (future_protocols.json) |

## 5. Wanneer stoppen of afschalen
- Paper of live > 2 standaardfouten onder de verwachting (weekrapport z < -2): niet opschalen, eerst uitzoeken.
- Een sleeve 90 paper-dagen z < -2 en 12 maanden negatief: gewicht halveren (vooraf vastgelegde regel).
- Een firm verandert regels of vraagt om uitleg: STOP-bestand, eerst lezen.

## 6. Wat dit NIET is
Geen financieel advies; belasting (inkomstenbelasting / ondernemer?) met een adviseur bespreken. De simulaties gaan uit van
regels die deels uit reviewsites komen; `get_prop_rules.bat` + de dashboards van de firms zijn leidend.
