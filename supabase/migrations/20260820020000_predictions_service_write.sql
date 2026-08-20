-- Allow service_role full write on predictions (judgment pipeline)
DROP POLICY IF EXISTS predictions_service_write ON predictions;
CREATE POLICY predictions_service_write ON predictions
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);
