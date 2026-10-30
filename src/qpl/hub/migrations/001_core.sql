-- Quant Trading Hub core schema. Times are UTC ISO-8601 text; money is REAL in the stated currency (USD unless a currency column says otherwise);
-- returns are fractions of equity.

CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  entity TEXT, entity_id TEXT, details TEXT, correlation_id TEXT);
CREATE INDEX ix_audit_ts ON audit_log(ts);

CREATE TABLE alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, level TEXT NOT NULL CHECK (level IN ('info','warning','critical')),
  source TEXT NOT NULL, message TEXT NOT NULL, evidence TEXT, dedup_key TEXT, acknowledged_at TEXT, acknowledged_by TEXT);
CREATE INDEX ix_alerts_open ON alerts(acknowledged_at, ts);

-- strategies and immutable versions -----------------------------------------------------------------------------------------
CREATE TABLE strategies (
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, name TEXT NOT NULL, market TEXT NOT NULL,
  family TEXT, description TEXT, hypothesis TEXT, created_at TEXT NOT NULL);
CREATE TABLE strategy_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id INTEGER NOT NULL REFERENCES strategies(id), version TEXT NOT NULL,
  code_ref TEXT NOT NULL, params TEXT NOT NULL, config_hash TEXT NOT NULL, state TEXT NOT NULL, notes TEXT, created_at TEXT NOT NULL,
  UNIQUE (strategy_id, version), UNIQUE (strategy_id, config_hash));
CREATE TRIGGER trg_versions_immutable BEFORE UPDATE OF code_ref, params, config_hash, strategy_id, version ON strategy_versions
BEGIN SELECT RAISE(ABORT, 'strategy versions are immutable: create a new version'); END;
CREATE TABLE lifecycle_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER NOT NULL REFERENCES strategy_versions(id), from_state TEXT, to_state TEXT NOT NULL,
  use_scope TEXT, reason TEXT NOT NULL, evidence TEXT, actor TEXT NOT NULL, ts TEXT NOT NULL);

-- research ------------------------------------------------------------------------------------------------------------------
CREATE TABLE hypotheses (
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, text TEXT NOT NULL, rationale TEXT, market TEXT, family TEXT,
  registered_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', verdict TEXT, source TEXT);
CREATE TABLE experiments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, hypothesis_id INTEGER REFERENCES hypotheses(id),
  version_id INTEGER REFERENCES strategy_versions(id), kind TEXT NOT NULL, title TEXT, config TEXT, config_hash TEXT,
  code_version TEXT, data_version TEXT, periods TEXT, cost_model TEXT, seed INTEGER, registered_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('registered','queued','running','done','failed','cancelled')),
  started_at TEXT, finished_at TEXT, metrics TEXT, decision TEXT, reason TEXT, trials_added INTEGER NOT NULL DEFAULT 1,
  uses_holdout INTEGER NOT NULL DEFAULT 0, source TEXT, artifacts TEXT);
CREATE INDEX ix_exp_status ON experiments(status);
CREATE INDEX ix_exp_hash ON experiments(config_hash);

-- data catalogue ------------------------------------------------------------------------------------------------------------
CREATE TABLE datasets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, path TEXT NOT NULL, market TEXT, kind TEXT, n_files INTEGER,
  bytes INTEGER, first_ts TEXT, last_ts TEXT, fingerprint TEXT, checked_at TEXT, status TEXT, issues TEXT);

-- paper trading -------------------------------------------------------------------------------------------------------------
CREATE TABLE paper_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, version_id INTEGER REFERENCES strategy_versions(id),
  portfolio_version_id INTEGER, source_dir TEXT NOT NULL, initial_capital REAL NOT NULL, currency TEXT NOT NULL DEFAULT 'USD',
  status TEXT NOT NULL CHECK (status IN ('running','paused','stopped','archived','unknown')), config TEXT, created_at TEXT NOT NULL,
  last_ingested_at TEXT, last_data_ts TEXT);
CREATE TABLE paper_equity (
  account_id INTEGER NOT NULL REFERENCES paper_accounts(id), ts TEXT NOT NULL, ret REAL NOT NULL, equity REAL NOT NULL,
  late INTEGER, PRIMARY KEY (account_id, ts));
CREATE TABLE paper_sleeve_pnl (
  account_id INTEGER NOT NULL REFERENCES paper_accounts(id), ts TEXT NOT NULL, sleeve TEXT NOT NULL, pnl REAL NOT NULL, weight REAL,
  PRIMARY KEY (account_id, ts, sleeve));
CREATE TABLE paper_orders (
  account_id INTEGER NOT NULL REFERENCES paper_accounts(id), ts TEXT NOT NULL, coin TEXT NOT NULL, side TEXT NOT NULL, usd REAL NOT NULL,
  from_usd REAL, to_usd REAL, type TEXT, reason TEXT, PRIMARY KEY (account_id, ts, coin, side, usd));
CREATE TABLE paper_events (
  account_id INTEGER NOT NULL REFERENCES paper_accounts(id), ts TEXT NOT NULL, event TEXT NOT NULL, details TEXT,
  PRIMARY KEY (account_id, ts, event));

-- portfolios ----------------------------------------------------------------------------------------------------------------
CREATE TABLE portfolios (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, market TEXT NOT NULL, purpose TEXT, created_at TEXT NOT NULL);
CREATE TABLE portfolio_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, portfolio_id INTEGER NOT NULL REFERENCES portfolios(id), version TEXT NOT NULL,
  members TEXT NOT NULL, allocation_rule TEXT NOT NULL, rebalance_rule TEXT, config_hash TEXT NOT NULL, state TEXT NOT NULL,
  notes TEXT, created_at TEXT NOT NULL, UNIQUE (portfolio_id, version));
CREATE TRIGGER trg_pversions_immutable BEFORE UPDATE OF members, allocation_rule, config_hash, version ON portfolio_versions
BEGIN SELECT RAISE(ABORT, 'portfolio versions are immutable: create a new version'); END;

-- risk ----------------------------------------------------------------------------------------------------------------------
CREATE TABLE risk_limits (
  id INTEGER PRIMARY KEY AUTOINCREMENT, scope TEXT NOT NULL, scope_key TEXT NOT NULL, rule TEXT NOT NULL, threshold REAL NOT NULL,
  action TEXT NOT NULL, recover_below REAL, enabled INTEGER NOT NULL DEFAULT 1, UNIQUE (scope, scope_key, rule));
CREATE TABLE risk_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, scope TEXT NOT NULL, scope_key TEXT NOT NULL, rule TEXT NOT NULL,
  value REAL, threshold REAL, action TEXT NOT NULL, state TEXT NOT NULL, evidence TEXT);
CREATE TABLE risk_state (scope TEXT NOT NULL, scope_key TEXT NOT NULL, rule TEXT NOT NULL, active INTEGER NOT NULL, since TEXT,
  PRIMARY KEY (scope, scope_key, rule));

-- prop firms ----------------------------------------------------------------------------------------------------------------
CREATE TABLE prop_firms (
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, name TEXT NOT NULL, markets TEXT, platforms TEXT, website TEXT, notes TEXT);
CREATE TABLE prop_rule_sets (
  id INTEGER PRIMARY KEY AUTOINCREMENT, firm_id INTEGER NOT NULL REFERENCES prop_firms(id), account_type TEXT NOT NULL,
  version INTEGER NOT NULL, effective_from TEXT NOT NULL, superseded_at TEXT, params TEXT NOT NULL, params_hash TEXT NOT NULL,
  created_at TEXT NOT NULL, UNIQUE (firm_id, account_type, version));
CREATE TABLE prop_rule_facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, rule_set_id INTEGER NOT NULL REFERENCES prop_rule_sets(id), field TEXT NOT NULL, value TEXT,
  status TEXT NOT NULL CHECK (status IN ('verified','uncertain','assumption','not_found','ambiguous')),
  source_url TEXT, quote TEXT, checked_at TEXT, confidence TEXT, note TEXT);
CREATE TABLE compat_assessments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, version_id INTEGER REFERENCES strategy_versions(id), portfolio_version_id INTEGER,
  rule_set_id INTEGER NOT NULL REFERENCES prop_rule_sets(id), status TEXT NOT NULL
  CHECK (status IN ('verified_compatible','potentially_compatible','incompatible','insufficient_evidence')),
  reasons TEXT NOT NULL, ts TEXT NOT NULL);
CREATE TABLE challenge_sims (
  id INTEGER PRIMARY KEY AUTOINCREMENT, rule_set_id INTEGER NOT NULL REFERENCES prop_rule_sets(id), subject TEXT NOT NULL,
  returns_source TEXT NOT NULL, sharpe_level TEXT, config TEXT NOT NULL, results TEXT NOT NULL, ts TEXT NOT NULL);

-- finance -------------------------------------------------------------------------------------------------------------------
CREATE TABLE finance_tx (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN
  ('challenge_fee','subscription','data','infrastructure','software','other_expense','payout','tax_payment','capital_in','capital_out')),
  amount REAL NOT NULL, currency TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN
  ('planned','requested','approved','received','rejected','paid','cancelled')),
  firm TEXT, account TEXT, strategy TEXT, market TEXT, external_ref TEXT UNIQUE, note TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE finance_tx_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tx_id INTEGER NOT NULL REFERENCES finance_tx(id), ts TEXT NOT NULL, old_status TEXT, new_status TEXT NOT NULL, note TEXT);
CREATE TABLE income_scenarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, assumptions TEXT NOT NULL, results TEXT NOT NULL, ts TEXT NOT NULL);

-- jobs ----------------------------------------------------------------------------------------------------------------------
CREATE TABLE jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL, dedup_key TEXT, priority INTEGER NOT NULL DEFAULT 5,
  status TEXT NOT NULL CHECK (status IN ('queued','running','done','failed','cancelled','paused')),
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3, timeout_s INTEGER NOT NULL DEFAULT 3600,
  next_run_at TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, heartbeat_at TEXT, worker TEXT,
  result TEXT, error TEXT, schedule_name TEXT);
CREATE UNIQUE INDEX ux_jobs_active_dedup ON jobs(dedup_key) WHERE dedup_key IS NOT NULL AND status IN ('queued','running','paused');
CREATE INDEX ix_jobs_next ON jobs(status, next_run_at, priority);
CREATE TABLE schedules (
  name TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, every_minutes INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
  priority INTEGER NOT NULL DEFAULT 5, last_enqueued_at TEXT, quiet_hours TEXT);
CREATE TABLE backups (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, path TEXT NOT NULL, bytes INTEGER, sha256 TEXT,
  verified_at TEXT, verify_result TEXT);
