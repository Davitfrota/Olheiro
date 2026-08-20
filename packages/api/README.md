# Scouter API (Go/Fiber)

Backend inicial da Fase 0/1.

## Endpoints

- `GET /health`
- `GET /v1/predictions?limit=50&published=true`
- `POST /v1/ingestion/fixtures`
- `POST /v1/analysis/value-gate`

## Run

```bash
cd packages/api
# precisa de SUPABASE_URL e SUPABASE_ANON_KEY no .env da raiz
go run ./cmd/api
```

Porta padrão: `8080` (`SCOUTER_API_PORT` para sobrescrever).

## Exemplo

```bash
curl http://localhost:8080/v1/predictions?limit=5
```
