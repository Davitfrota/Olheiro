-- Fase 0: permite anon inserir/atualizar statistical_priors (ingestão/backtest).
-- Remover na Fase 1 em favor de service_role apenas.
CREATE POLICY statistical_priors_anon_insert ON statistical_priors FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY statistical_priors_anon_update ON statistical_priors FOR UPDATE TO anon USING (true) WITH CHECK (true);
