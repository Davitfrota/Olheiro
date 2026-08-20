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
# Copie .env.example para .env na raiz e preencha as chaves
set API_FOOTBALL_KEY=...
set THE_ODDS_API_KEY=...
scouter-spike
```

Exit codes: `0` ok, `1` erro de API, `2` keys ausentes (esperado sem .env).

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
