# Scouter IA

Aplicativo de análise esportiva movido por IA — cruza estatísticas de futebol com odds de mercado e entrega palpites classificados por nível de risco, com explicação em linguagem natural.

**Não é uma casa de apostas.** Ferramenta de análise e conteúdo; não processa apostas nem movimenta dinheiro de jogo.

## Stack (planejada)

| Camada | Tecnologia |
|---|---|
| API | Go + Fiber |
| Modelagem estatística | Python (Poisson/Elo) |
| Orquestração LLM | Padrão RAG + intent detection |
| Banco de dados | PostgreSQL via Supabase |
| Pagamentos | Asaas (assinatura freemium) |
| Web | Next.js |
| Android | React Native |
| Push notifications | Firebase Cloud Messaging |
| Observabilidade IA | Helicone |

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

- **Fase 0** — Fundação de dados (ingestão, schema, validação Poisson)
- **Fase 1** — MVP (palpites básicos, auth, paywall, Web + Android)
- **Fase 2** — Camada de IA explicativa + histórico de acurácia
- **Fase 3** — Value bets, alertas de odds, personalização
- **Fase 4** — Expansão (outros esportes, afiliação)

Ver [docs/planejamento.md](./docs/planejamento.md) para o documento completo.

## Licença

Proprietário — Davi Tavares Frota © 2026
