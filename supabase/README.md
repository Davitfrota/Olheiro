# Supabase

## Migrations

| Arquivo | Conteúdo |
|---|---|
| `20260820000000_initial_schema.sql` | Schema Fase 0 — ligas, partidas, odds, priors, judgments, predictions |
| `20260820005000_unaccent_extension.sql` | Extensão `unaccent` para normalização textual em SQL |
| `20260820010000_seed_team_aliases.sql` | Seed inicial de aliases para resolver nomes entre APIs |

Entidades-chave alinhadas ao [pipeline de raciocínio](../docs/pipeline-raciocinio.md):

- `statistical_priors` — estágio 0 (Poisson/Elo, código)
- `match_context` + `match_absences` — context pack estruturado
- `prediction_judgments` — cache `(match, market, odds_hash, context_hash)`
- `predictions` + `prediction_results` — histórico público de acurácia

## Aplicar localmente

```bash
supabase db reset   # ou supabase migration up
```

