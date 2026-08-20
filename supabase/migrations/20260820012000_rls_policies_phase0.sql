-- RLS policies para Fase 0:
-- Leitura pública em tabelas de dados esportivos.
-- Escrita via service_role (backend) + anon temporário para ingestão dev.

-- Public read
CREATE POLICY leagues_public_read ON leagues FOR SELECT USING (true);
CREATE POLICY teams_public_read ON teams FOR SELECT USING (true);
CREATE POLICY team_aliases_public_read ON team_aliases FOR SELECT USING (true);
CREATE POLICY matches_public_read ON matches FOR SELECT USING (true);
CREATE POLICY match_mappings_public_read ON match_mappings FOR SELECT USING (true);
CREATE POLICY match_stats_public_read ON match_stats FOR SELECT USING (true);
CREATE POLICY match_context_public_read ON match_context FOR SELECT USING (true);
CREATE POLICY match_absences_public_read ON match_absences FOR SELECT USING (true);
CREATE POLICY bookmakers_public_read ON bookmakers FOR SELECT USING (true);
CREATE POLICY odds_snapshots_public_read ON odds_snapshots FOR SELECT USING (true);
CREATE POLICY statistical_priors_public_read ON statistical_priors FOR SELECT USING (true);
CREATE POLICY prediction_judgments_public_read ON prediction_judgments FOR SELECT USING (true);
CREATE POLICY prediction_results_public_read ON prediction_results FOR SELECT USING (true);
CREATE POLICY accuracy_snapshots_public_read ON accuracy_snapshots FOR SELECT USING (true);
CREATE POLICY ai_usage_ledger_public_read ON ai_usage_ledger FOR SELECT USING (true);

-- Service role write (backend ingestion)
CREATE POLICY leagues_service_write ON leagues FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY teams_service_write ON teams FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY team_aliases_service_write ON team_aliases FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY matches_service_write ON matches FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY match_mappings_service_write ON match_mappings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY match_stats_service_write ON match_stats FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY match_context_service_write ON match_context FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY match_absences_service_write ON match_absences FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY bookmakers_service_write ON bookmakers FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY odds_snapshots_service_write ON odds_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY statistical_priors_service_write ON statistical_priors FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY prediction_judgments_service_write ON prediction_judgments FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY prediction_results_service_write ON prediction_results FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY accuracy_snapshots_service_write ON accuracy_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY ai_usage_ledger_service_write ON ai_usage_ledger FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Anon insert (temporário Fase 0 — remover na Fase 1)
CREATE POLICY matches_anon_insert ON matches FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY match_mappings_anon_insert ON match_mappings FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY match_stats_anon_insert ON match_stats FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY bookmakers_anon_insert ON bookmakers FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY odds_snapshots_anon_insert ON odds_snapshots FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY bookmakers_anon_update ON bookmakers FOR UPDATE TO anon USING (true) WITH CHECK (true);
CREATE POLICY match_mappings_anon_update ON match_mappings FOR UPDATE TO anon USING (true) WITH CHECK (true);
