-- Allow anon write/select for qualitative context tables (phase 0 without service_role).
DROP POLICY IF EXISTS match_absences_anon_insert ON match_absences;
CREATE POLICY match_absences_anon_insert ON match_absences FOR INSERT TO anon WITH CHECK (true);
DROP POLICY IF EXISTS match_absences_anon_update ON match_absences;
CREATE POLICY match_absences_anon_update ON match_absences FOR UPDATE TO anon USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS match_absences_anon_select ON match_absences;
CREATE POLICY match_absences_anon_select ON match_absences FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS match_context_anon_insert ON match_context;
CREATE POLICY match_context_anon_insert ON match_context FOR INSERT TO anon WITH CHECK (true);
DROP POLICY IF EXISTS match_context_anon_update ON match_context;
CREATE POLICY match_context_anon_update ON match_context FOR UPDATE TO anon USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS match_context_anon_select ON match_context;
CREATE POLICY match_context_anon_select ON match_context FOR SELECT TO anon USING (true);

DROP POLICY IF EXISTS match_mappings_anon_select ON match_mappings;
CREATE POLICY match_mappings_anon_select ON match_mappings FOR SELECT TO anon USING (true);
