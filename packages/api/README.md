# Scouter API (Go/Fiber)

Backend inicial da Fase 0/1.

## Endpoints scaffold

- `GET /health`
- `POST /v1/ingestion/fixtures`
- `POST /v1/analysis/value-gate`

## Run

```bash
cd packages/api
go run ./cmd/api
```

Porta padrão: `8080` (`SCOUTER_API_PORT` para sobrescrever).

## Exemplo value-gate

```bash
curl -X POST http://localhost:8080/v1/analysis/value-gate \
  -H "Content-Type: application/json" \
  -d '{
    "p_adj": 0.58,
    "se_adj": 0.08,
    "p_fair": 0.68,
    "information_completeness": 0.55,
    "thin_data": true,
    "k_multiplier": 1.75,
    "completeness_threshold": 0.7
  }'
```
