-- PostgREST RETURNING needs SELECT on inserted rows (including abstained).
DROP POLICY IF EXISTS predictions_public_read ON predictions;
CREATE POLICY predictions_public_read ON predictions
  FOR SELECT
  USING (true);

DROP POLICY IF EXISTS prediction_judgments_public_read ON prediction_judgments;
CREATE POLICY prediction_judgments_public_read ON prediction_judgments
  FOR SELECT
  USING (true);
