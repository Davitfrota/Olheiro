# Supabase

## Migrations

| Arquivo | Conteúdo |
|---|---|
| `20260820000000_initial_schema.sql` | Schema Fase 0 — ligas, partidas, odds, priors, judgments, predictions |
| `20260820005000_unaccent_extension.sql` | Extensão `unaccent` para normalização textual em SQL |
| `20260820007500_seed_brasileirao_teams.sql` | Liga piloto + 20 times do Brasileirão 2024 |
| `20260820010000_seed_team_aliases.sql` | Seed inicial de aliases para resolver nomes entre APIs |

## Projeto remoto

- **Ref:** `ggeyvjhvdvxbxjdrexoa`
- **URL:** `https://ggeyvjhvdvxbxjdrexoa.supabase.co`
- Migrations aplicadas via MCP Supabase (Cursor)

Entidades-chave alinhadas ao [pipeline de raciocínio](../docs/pipeline-raciocinio.md):

- `statistical_priors` — estágio 0 (Poisson/Elo, código)
- `match_context` + `match_absences` — context pack estruturado
- `prediction_judgments` — cache `(match, market, odds_hash, context_hash)`
- `predictions` + `prediction_results` — histórico público de acurácia

## Aplicar localmente

```bash
supabase db reset   # ou supabase migration up
```

