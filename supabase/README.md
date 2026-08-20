# Supabase

## Migrations

| Arquivo | Conteúdo |
|---|---|
| `20260820000000_initial_schema.sql` | Schema Fase 0 — ligas, partidas, odds, priors, judgments, predictions |

Entidades-chave alinhadas ao [pipeline de raciocínio](../docs/pipeline-raciocinio.md):

- `statistical_priors` — estágio 0 (Poisson/Elo, código)
- `match_context` + `match_absences` — context pack estruturado
- `prediction_judgments` — cache `(match, market, odds_hash, context_hash)`
- `predictions` + `prediction_results` — histórico público de acurácia

## Aplicar localmente

```bash
supabase db reset   # ou supabase migration up
```
