-- Scouter IA — schema inicial (Fase 0)
-- Alinhado a docs/pipeline-raciocinio.md

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE market_type AS ENUM (
  'h2h',           -- 1x2
  'totals',        -- over/under
  'btts',
  'double_chance',
  'corners'
);

CREATE TYPE match_status AS ENUM (
  'scheduled',
  'live',
  'finished',
  'postponed',
  'cancelled'
);

CREATE TYPE risk_label AS ENUM (
  'conservative',
  'moderate',
  'risky'
);

CREATE TYPE value_decision AS ENUM (
  'VALUE',
  'NOISE',
  'ABSTAIN'
);

CREATE TYPE prediction_status AS ENUM (
  'draft',
  'published',
  'abstained',
  'void'
);

CREATE TYPE subscription_plan AS ENUM (
  'free',
  'subscriber'
);

CREATE TYPE subscription_status AS ENUM (
  'active',
  'past_due',
  'cancelled',
  'trialing'
);

CREATE TYPE data_source AS ENUM (
  'api_football',
  'the_odds_api',
  'sofascore',
  'manual'
);

CREATE TYPE absence_status AS ENUM (
  'confirmed_out',
  'doubtful',
  'suspended',
  'returned'
);

CREATE TYPE player_importance AS ENUM (
  'low',
  'medium',
  'high'
);

CREATE TYPE lineup_status AS ENUM (
  'UNKNOWN',
  'PROBABLE',
  'CONFIRMED'
);

CREATE TYPE ai_ledger_status AS ENUM (
  'reserved',
  'confirmed',
  'released'
);

-- ---------------------------------------------------------------------------
-- Core: leagues, teams, entity resolution
-- ---------------------------------------------------------------------------
CREATE TABLE leagues (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT NOT NULL UNIQUE,          -- e.g. brasileirao-serie-a
  name          TEXT NOT NULL,
  country       TEXT NOT NULL,
  season        TEXT NOT NULL,                 -- e.g. 2026
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE teams (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id     UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  slug          TEXT NOT NULL,
  name          TEXT NOT NULL,
  short_name    TEXT,
  attack_strength  NUMERIC(6,4),               -- Poisson λ component
  defense_strength NUMERIC(6,4),
  elo_rating    NUMERIC(8,2),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (league_id, slug)
);

CREATE TABLE team_aliases (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id       UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  source        data_source NOT NULL,
  external_id   TEXT NOT NULL,
  external_name TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source, external_id)
);

CREATE INDEX idx_team_aliases_team ON team_aliases(team_id);

-- ---------------------------------------------------------------------------
-- Matches & stats
-- ---------------------------------------------------------------------------
CREATE TABLE matches (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id       UUID NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
  home_team_id    UUID NOT NULL REFERENCES teams(id),
  away_team_id    UUID NOT NULL REFERENCES teams(id),
  kickoff_at      TIMESTAMPTZ NOT NULL,
  status          match_status NOT NULL DEFAULT 'scheduled',
  home_score      SMALLINT,
  away_score      SMALLINT,
  venue           TEXT,
  venue_anomaly   JSONB,                       -- portões fechados, altitude, etc.
  round           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (home_team_id <> away_team_id)
);

CREATE TABLE match_mappings (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id      UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  source        data_source NOT NULL,
  external_id   TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source, external_id)
);

CREATE INDEX idx_matches_kickoff ON matches(kickoff_at);
CREATE INDEX idx_matches_league_kickoff ON matches(league_id, kickoff_at);
CREATE INDEX idx_matches_status ON matches(status);

CREATE TABLE match_stats (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id        UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  home_xg         NUMERIC(5,2),
  away_xg         NUMERIC(5,2),
  home_shots      SMALLINT,
  away_shots      SMALLINT,
  home_corners    SMALLINT,
  away_corners    SMALLINT,
  home_yellow     SMALLINT,
  away_yellow     SMALLINT,
  home_red        SMALLINT,
  away_red        SMALLINT,
  raw             JSONB NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (match_id)
);

-- ---------------------------------------------------------------------------
-- Context pack inputs (qualitative layer)
-- ---------------------------------------------------------------------------
CREATE TABLE match_context (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id              UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  lineup_status         lineup_status NOT NULL DEFAULT 'UNKNOWN',
  lineup_confirmed_at   TIMESTAMPTZ,
  rest_days_home        SMALLINT,
  rest_days_away        SMALLINT,
  congestion_home_7d    INTEGER,               -- minutos do XI provável
  congestion_away_7d    INTEGER,
  table_context         JSONB NOT NULL DEFAULT '{}',  -- need, position, games_left
  tournament_state      JSONB NOT NULL DEFAULT '{}',  -- already_qualified, etc.
  missing_fields        TEXT[] NOT NULL DEFAULT '{}',
  information_completeness NUMERIC(4,3) CHECK (information_completeness BETWEEN 0 AND 1),
  pack_hash             TEXT NOT NULL,           -- sha256 do JSON canônico
  pack                  JSONB NOT NULL,          -- context pack completo
  fetched_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (match_id, pack_hash)
);

CREATE INDEX idx_match_context_match ON match_context(match_id, fetched_at DESC);

CREATE TABLE match_absences (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id        UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  team_id         UUID NOT NULL REFERENCES teams(id),
  player_name     TEXT NOT NULL,
  player_external_id TEXT,
  absence_status  absence_status NOT NULL,
  role            TEXT,                          -- creator, striker, keeper...
  importance      player_importance NOT NULL DEFAULT 'medium',
  xg_share_90d    NUMERIC(5,4),
  minutes_share   NUMERIC(5,4),
  source          data_source NOT NULL,
  reported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (match_id, team_id, player_name, absence_status)
);

CREATE INDEX idx_match_absences_match ON match_absences(match_id);

-- ---------------------------------------------------------------------------
-- Odds (time series)
-- ---------------------------------------------------------------------------
CREATE TABLE bookmakers (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug          TEXT NOT NULL UNIQUE,          -- pinnacle, bet365...
  name          TEXT NOT NULL,
  is_sharp      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE odds_snapshots (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id      UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  bookmaker_id  UUID NOT NULL REFERENCES bookmakers(id),
  market        market_type NOT NULL,
  line          NUMERIC(4,1),                  -- e.g. 2.5 for totals
  outcomes      JSONB NOT NULL,                -- { "home": 1.40, "draw": 4.60, "away": 8.50 }
  overround     NUMERIC(5,4),
  source        data_source NOT NULL DEFAULT 'the_odds_api',
  captured_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  odds_hash     TEXT NOT NULL                  -- hash canônico para cache do pipeline
);

CREATE INDEX idx_odds_match_market_time ON odds_snapshots(match_id, market, captured_at DESC);
CREATE INDEX idx_odds_hash ON odds_snapshots(odds_hash);

-- ---------------------------------------------------------------------------
-- Statistical prior (estágio 0 — código, não LLM)
-- ---------------------------------------------------------------------------
CREATE TABLE statistical_priors (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id            UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  model_version       TEXT NOT NULL,           -- poisson-dc-v0.1
  calibration_bucket  TEXT NOT NULL,           -- brasileirao-1x2
  lambda_home         NUMERIC(6,4) NOT NULL,
  lambda_away         NUMERIC(6,4) NOT NULL,
  p_prior             JSONB NOT NULL,          -- { home, draw, away }
  derived             JSONB NOT NULL DEFAULT '{}',  -- over_25, btts...
  se_prior            JSONB NOT NULL DEFAULT '{}',  -- standard errors por outcome
  sample              JSONB NOT NULL DEFAULT '{}',  -- matches_home_season, thin_data...
  already_in_model    TEXT[] NOT NULL DEFAULT '{}',
  computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (match_id, model_version)
);

CREATE INDEX idx_priors_match ON statistical_priors(match_id, computed_at DESC);

-- ---------------------------------------------------------------------------
-- Pipeline judgment (cache + audit trail)
-- ---------------------------------------------------------------------------
CREATE TABLE prediction_judgments (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id                UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  prior_id                UUID NOT NULL REFERENCES statistical_priors(id),
  context_id              UUID REFERENCES match_context(id),
  odds_snapshot_id        UUID REFERENCES odds_snapshots(id),
  market                  market_type NOT NULL,
  selection               TEXT NOT NULL,       -- home, over_25, yes_btts...
  -- Números travados pelo pipeline
  p_prior_selection       NUMERIC(6,4),
  p_adj                   NUMERIC(6,4),
  se_adj                  NUMERIC(6,4),
  p_fair                  NUMERIC(6,4),
  edge                    NUMERIC(6,4),
  value_decision          value_decision NOT NULL,
  risk_label              risk_label,
  prediction_status       prediction_status NOT NULL DEFAULT 'draft',
  -- Cache key
  odds_hash               TEXT NOT NULL,
  context_hash            TEXT NOT NULL,
  cache_key               TEXT NOT NULL UNIQUE,  -- match_id:market:odds_hash:context_hash
  -- Artefatos do pipeline
  extracted_signals       JSONB NOT NULL DEFAULT '[]',
  adjustments             JSONB NOT NULL DEFAULT '{}',  -- δλ aplicados
  critic_verdict          JSONB,                          -- hidden_risks, action
  veto_reasons            TEXT[] NOT NULL DEFAULT '{}',
  pipeline_version        TEXT NOT NULL DEFAULT 'v0.1',
  judged_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_judgments_match_market ON prediction_judgments(match_id, market, judged_at DESC);

-- ---------------------------------------------------------------------------
-- Published predictions (o que o usuário vê)
-- ---------------------------------------------------------------------------
CREATE TABLE predictions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  judgment_id         UUID NOT NULL REFERENCES prediction_judgments(id) UNIQUE,
  match_id            UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  market              market_type NOT NULL,
  selection           TEXT NOT NULL,
  model_probability   NUMERIC(6,4),
  market_probability  NUMERIC(6,4),
  edge                NUMERIC(6,4),
  confidence_score    NUMERIC(5,4) CHECK (confidence_score BETWEEN 0 AND 1),
  risk_label          risk_label,
  value_decision      value_decision NOT NULL,
  is_free_tier        BOOLEAN NOT NULL DEFAULT FALSE,
  explanation         TEXT,                    -- LLM estágio 8; NULL no MVP Fase 1
  published_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_predictions_published ON predictions(published_at DESC) WHERE published_at IS NOT NULL;
CREATE INDEX idx_predictions_match ON predictions(match_id);

CREATE TABLE prediction_results (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id       UUID NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  actual_outcome      TEXT NOT NULL,
  was_correct         BOOLEAN,
  settlement_reason   TEXT NOT NULL DEFAULT 'finished',  -- finished | void | postponed
  settled_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (prediction_id)
);

-- ---------------------------------------------------------------------------
-- Users, subscriptions, alerts
-- ---------------------------------------------------------------------------
CREATE TABLE profiles (
  id                  UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name        TEXT,
  birth_date          DATE,
  age_verified        BOOLEAN NOT NULL DEFAULT FALSE,
  plan                subscription_plan NOT NULL DEFAULT 'free',
  risk_preference     risk_label,              -- filtro assinante
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  asaas_customer_id   TEXT,
  asaas_subscription_id TEXT UNIQUE,
  status              subscription_status NOT NULL DEFAULT 'active',
  current_period_start TIMESTAMPTZ,
  current_period_end  TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);

CREATE TABLE alerts (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  match_id            UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  market              market_type NOT NULL,
  min_edge_threshold  NUMERIC(5,4),
  odds_change_pct     NUMERIC(5,4),            -- alerta se odd mover X%
  is_active           BOOLEAN NOT NULL DEFAULT TRUE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, match_id, market)
);

-- ---------------------------------------------------------------------------
-- AI cost ledger (padrão reserve-then-confirm)
-- ---------------------------------------------------------------------------
CREATE TABLE ai_usage_ledger (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id            UUID REFERENCES matches(id) ON DELETE SET NULL,
  judgment_id         UUID REFERENCES prediction_judgments(id) ON DELETE SET NULL,
  stage               TEXT NOT NULL,             -- signal_extractor | critic | explainer
  model               TEXT NOT NULL,
  tokens_in           INTEGER NOT NULL DEFAULT 0,
  tokens_out          INTEGER NOT NULL DEFAULT 0,
  cost_usd            NUMERIC(10,6) NOT NULL DEFAULT 0,
  status              ai_ledger_status NOT NULL DEFAULT 'reserved',
  helicone_request_id TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  confirmed_at        TIMESTAMPTZ
);

CREATE INDEX idx_ai_ledger_match ON ai_usage_ledger(match_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Accuracy aggregates (histórico público)
-- ---------------------------------------------------------------------------
CREATE TABLE accuracy_snapshots (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_start        DATE NOT NULL,
  period_end          DATE NOT NULL,
  market              market_type NOT NULL,
  risk_label          risk_label,
  total_predictions   INTEGER NOT NULL,
  correct_predictions INTEGER NOT NULL,
  accuracy_pct        NUMERIC(5,2) NOT NULL,
  methodology_version TEXT NOT NULL DEFAULT 'v1',
  computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (period_start, period_end, market, risk_label, methodology_version)
);

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_leagues_updated BEFORE UPDATE ON leagues
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_teams_updated BEFORE UPDATE ON teams
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_matches_updated BEFORE UPDATE ON matches
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_profiles_updated BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_subscriptions_updated BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS (placeholders — políticas detalhadas na Fase 1)
-- ---------------------------------------------------------------------------
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Predictions públicas (free tier vê subset via view/API)
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY predictions_public_read ON predictions
  FOR SELECT USING (published_at IS NOT NULL);

CREATE POLICY profiles_own ON profiles
  FOR ALL USING (auth.uid() = id);

CREATE POLICY alerts_own ON alerts
  FOR ALL USING (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Seed: bookmakers comuns
-- ---------------------------------------------------------------------------
INSERT INTO bookmakers (slug, name, is_sharp) VALUES
  ('pinnacle', 'Pinnacle', TRUE),
  ('bet365', 'Bet365', FALSE),
  ('betfair', 'Betfair', FALSE)
ON CONFLICT (slug) DO NOTHING;
