-- Hub-native paper engine: per-account state (restart-safe), simulated fills and position snapshots.
CREATE TABLE paper_engine_state (
  account_id INTEGER PRIMARY KEY REFERENCES paper_accounts(id), last_bar TEXT, equity REAL NOT NULL, held TEXT NOT NULL,
  pending_cost REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
CREATE TABLE paper_fills (
  account_id INTEGER NOT NULL REFERENCES paper_accounts(id), ts TEXT NOT NULL, coin TEXT NOT NULL, delta_weight REAL NOT NULL,
  price REAL, notional_usd REAL, cost_usd REAL, PRIMARY KEY (account_id, ts, coin));
CREATE TABLE paper_positions (
  account_id INTEGER NOT NULL REFERENCES paper_accounts(id), ts TEXT NOT NULL, coin TEXT NOT NULL, weight REAL NOT NULL, notional_usd REAL,
  PRIMARY KEY (account_id, ts, coin));
