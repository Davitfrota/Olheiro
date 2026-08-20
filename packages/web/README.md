# Scouter IA Web

Lista mínima de predictions + acurácia settled.

```bash
# terminal 1 — API Go
cd packages/api
go run ./cmd/api

# terminal 2 — Next.js
cd packages/web
npm run dev
```

Abra http://localhost:3000 — o rewrite `/api/scouter/*` aponta para `SCOUTER_API_ORIGIN` (default `http://127.0.0.1:8080`).
