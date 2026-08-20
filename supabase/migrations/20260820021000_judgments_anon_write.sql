-- Phase 0.5: allow anon write when service_role key is not configured yet.
-- Prefer SUPABASE_SERVICE_ROLE_KEY in production.

DROP POLICY IF EXISTS prediction_judgments_anon_insert ON prediction_judgments;
CREATE POLICY prediction_judgments_anon_insert ON prediction_judgments
  FOR INSERT TO anon
  WITH CHECK (true);

DROP POLICY IF EXISTS prediction_judgments_anon_update ON prediction_judgments;
CREATE POLICY prediction_judgments_anon_update ON prediction_judgments
  FOR UPDATE TO anon
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS predictions_anon_insert ON predictions;
CREATE POLICY predictions_anon_insert ON predictions
  FOR INSERT TO anon
  WITH CHECK (true);

DROP POLICY IF EXISTS predictions_anon_update ON predictions;
CREATE POLICY predictions_anon_update ON predictions
  FOR UPDATE TO anon
  USING (true)
  WITH CHECK (true);
