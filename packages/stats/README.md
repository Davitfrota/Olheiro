# Scouter Stats

Motor estatístico Python — estágio 0 do pipeline de raciocínio.

## Responsabilidade

- Calcular `statistical_priors` (λ, p_prior, se_prior, derived)
- Expor contrato Pydantic consumido pelo backend Go
- **Não** classifica risco, **não** chama LLM, **não** gera texto

Ver [docs/pipeline-raciocinio.md](../../docs/pipeline-raciocinio.md).

## Setup

```bash
cd packages/stats
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

## Spike de APIs

```bash
# .env na raiz do repo (com ou sem aspas nas chaves)
scouter-spike
```

O spike carrega `.env` automaticamente e inclui:
- API-Football (Brasileirão, plano free: temporadas 2022–2024)
- The Odds API (prioriza `soccer_brazil_campeonato`)
- Cruzamento de nomes de times entre as duas fontes

Exit codes: `0` ok, `1` erro de API, `2` keys ausentes.

## Backtest (Fase 0)

```bash
# Fonte padrão: matches no Supabase (temporada completa)
scouter-backtest --source supabase --persist

# Ou via API-Football (amostra)
scouter-backtest --source api --season 2024 --max-fixtures 80
```

Calcula Brier score do prior Poisson vs resultados reais. Baseline uniforme = 0.667.

**Resultado Brasileirão 2024 (Supabase, 372 jogos scored):**
- Brier médio: **0.6315** (bate uniforme)
- Acurácia argmax: 44.9%
- Priors persistidos em `statistical_priors`

## Judgment pipeline (Fase 0.5)

```bash
scouter-judge --dry-run
scouter-judge
```

Lê `statistical_priors` + `odds_snapshots` (+ `match_context`/`match_absences`),
aplica value gate + risk vetos, grava `prediction_judgments` e `predictions`.

## Context ingest (lesões + escalações)

```bash
scouter-context --season 2024 --lineups-limit 10
```

## Testes

```bash
pytest
```

## Contrato de saída (Prior)

```python
from scouter_stats.poisson import TeamStrength, build_prior

prior = build_prior(
    match_id="br-2026-flamengo-juventude",
    home=TeamStrength(attack=1.35, defense=0.85),
    away=TeamStrength(attack=0.75, defense=1.05),
    matches_home_season=12,
    matches_away_season=12,
)
print(prior.model_dump(by_alias=True))
```
