-- Harden Phase 1: remove temporary anon write policies; service_role keeps full write.
DROP POLICY IF EXISTS matches_anon_insert ON matches;
DROP POLICY IF EXISTS match_mappings_anon_insert ON match_mappings;
DROP POLICY IF EXISTS match_stats_anon_insert ON match_stats;
DROP POLICY IF EXISTS bookmakers_anon_insert ON bookmakers;
DROP POLICY IF EXISTS odds_snapshots_anon_insert ON odds_snapshots;
DROP POLICY IF EXISTS bookmakers_anon_update ON bookmakers;
DROP POLICY IF EXISTS match_mappings_anon_update ON match_mappings;
DROP POLICY IF EXISTS statistical_priors_anon_insert ON statistical_priors;
DROP POLICY IF EXISTS statistical_priors_anon_update ON statistical_priors;
DROP POLICY IF EXISTS prediction_judgments_anon_insert ON prediction_judgments;
DROP POLICY IF EXISTS prediction_judgments_anon_update ON prediction_judgments;
DROP POLICY IF EXISTS predictions_anon_insert ON predictions;
DROP POLICY IF EXISTS predictions_anon_update ON predictions;
DROP POLICY IF EXISTS match_absences_anon_insert ON match_absences;
DROP POLICY IF EXISTS match_absences_anon_update ON match_absences;
DROP POLICY IF EXISTS match_context_anon_insert ON match_context;
DROP POLICY IF EXISTS match_context_anon_update ON match_context;

DROP POLICY IF EXISTS predictions_service_write ON predictions;
CREATE POLICY predictions_service_write ON predictions
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);
