# Scouter IA

Aplicativo de análise esportiva movido por IA — cruza estatísticas de futebol com odds de mercado e entrega palpites classificados por nível de risco, com explicação em linguagem natural.

**Não é uma casa de apostas.** Ferramenta de análise e conteúdo; não processa apostas nem movimenta dinheiro de jogo.

## Stack

| Camada | Tecnologia | Status |
|---|---|---|
| API | Go + Fiber | Scaffold (Fase 0) |
| Modelagem estatística | Python (Poisson) | Implementado |
| Orquestração LLM | Padrão RAG + intent detection | Fase 2 |
| Banco de dados | PostgreSQL via Supabase | Implementado |
| Pagamentos | Asaas (assinatura freemium) | Fase 1 |
| Web | Next.js | Fase 1 |
| Android | React Native | Fase 1 |
| Push notifications | Firebase Cloud Messaging | Fase 3 |
| Observabilidade IA | Helicone | Fase 2 |

## Estrutura do monorepo

```
scouter-ia/
├── docs/           # Planejamento, specs e decisões arquiteturais
├── packages/
│   ├── api/        # Backend Go/Fiber
│   ├── stats/      # Motor estatístico Python
│   ├── web/        # Frontend Next.js
│   └── mobile/     # App React Native
└── supabase/       # Migrations e config do banco
```

## Roadmap

- **Fase 0** — Fundação de dados (ingestão, schema, validação Poisson) — **concluída**
- **Fase 1** — MVP (palpites básicos, auth, paywall, Web + Android) — **em andamento**
- **Fase 2** — Camada de IA explicativa + histórico de acurácia
- **Fase 3** — Value bets, alertas de odds, personalização
- **Fase 4** — Expansão (outros esportes, afiliação)

## Documentação

- [Planejamento](./docs/planejamento.md)
- [Pipeline de raciocínio](./docs/pipeline-raciocinio.md) — arquitetura de julgamento sob incerteza

## Fase 0 (concluída)

- [x] Schema SQL (`supabase/migrations/`)
- [x] Motor estatístico Python (`packages/stats/`)
- [x] Spike de APIs com chaves reais
- [x] Backtest Poisson vs resultados reais (Brasileirão 2024, Brier **0.6315** em 372 jogos)
- [x] Scaffold inicial da API Go/Fiber (`packages/api/`)
- [x] Seed inicial de `team_aliases` (`supabase/migrations/20260820010000_seed_team_aliases.sql`)
- [x] MCP Supabase configurado e autenticado (`.cursor/mcp.json`)
- [x] Migrations aplicadas no projeto remoto (`ggeyvjhvdvxbxjdrexoa`)
- [x] Seed Brasileirão 2024 — 20 times + 5 aliases cross-API
- [x] Pipeline de ingestão (`scouter-ingest`) — 380 matches + 328 odds
- [x] Priors Poisson persistidos (`statistical_priors`, 372 rows)

## Supabase

Projeto remoto: `ggeyvjhvdvxbxjdrexoa`  
URL: `https://ggeyvjhvdvxbxjdrexoa.supabase.co`

Migrations remotas aplicadas via MCP:
1. `initial_schema`
2. `unaccent_extension`
3. `seed_brasileirao_teams`
4. `seed_team_aliases`

## Licença

Proprietário — Davi Tavares Frota © 2026

