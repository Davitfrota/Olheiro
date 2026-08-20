# Marca — Scouter

## Decisão de nome (proposta)

| Camada | Nome | Uso |
|---|---|---|
| **Marca / wordmark** | **Scouter** | Logo, app, falado |
| **Produto legal** | Scouter IA | Contrato, CNPJ, docs |
| **Tagline** | Análise com risco explícito | Hero, store, ads |
| **Anti-tagline** | Não é casa de apostas | Disclaimer fixo |

**Por quê Scouter:** metáfora clara (olho de olheiro), curto, internacional, não soa “tipster”.  
**Por quê não “Scouter IA” no wordmark:** “IA” envelhece e competem por atenção com o nome; fica como subtítulo.

### Alternativas (se rejeitar Scouter)

1. **Scoutia** — compacto, domínio possível  
2. **Scout Verde** / scoutverde.com — mais BR, menos premium  
3. **Scouter BR** / scouterbr.com — explícito no mercado

## Domínios checados (Vercel)

| Domínio | Status | Nota |
|---|---|---|
| scouter.com.br | indisponível | — |
| scouter.app | indisponível | — |
| **scouteria.com** | **livre · ~US$11,25/ano** | melhor match com “Scouter IA” |
| **scouterbr.com** | **livre · ~US$11,25/ano** | foco Brasil |
| **scouter.fyi** | **livre · ~US$16,50/ano** | curto, moderno |
| **scoutia.app** | **livre · ~US$9,99/ano** | app-first, barato |
| **scoutverde.com** | **livre · ~US$11,25/ano** | marca alternativa |
| scoutia.com / .app | a confirmar | — |

### Mapa de subdomínios (depois de comprar o root)

```
app.<dominio>   → Web (Next.js)
api.<dominio>   → Go API + webhook AbacatePay
www.<dominio>   → redirect → app
```

Webhook AbacatePay ficaria:

`https://api.<dominio>/v1/billing/webhooks/abacatepay?webhookSecret=...`

## Identidade visual

### Direção
Editorial esportivo · gramado + papel craft · **não** casino, **não** neon roxo, **não** tipster YouTube.

### Tokens

```css
--bg:        #F3EFE6; /* papel quente */
--bg-deep:   #E7E0D2;
--ink:       #14201A; /* quase preto-verde */
--muted:     #5B685F;
--line:      #C9C0B0;
--pitch:     #1F6B45; /* gramado — cor primária */
--pitch-soft:#D7EBE0;
--warn:      #9A3412;
--ok:        #166534;
--bad:       #991B1B;
```

### Tipografia
- **Display:** Syne (já no web) — geométrica, presença de marca  
- **Corpo:** DM Sans — legível em tip lists  

### Logo
Wordmark **SCOUTER** + marca abstrata (lente/olho + linha de campo).  
Asset gerado: `.cursor/projects/.../assets/scouter-logo-mark.png` (iterar no Figma/Paper depois).

### Tom de voz
Direto, técnico sem jargão de tipster. Sempre: probabilidade ≠ certeza. 18+.

## Próximos passos

1. Escolher root: **scouteria.com** (recomendado) ou scouterbr.com  
2. Comprar no Vercel Domains e apontar `app` + `api`  
3. Deploy web + API com esses hosts  
4. Registrar webhook AbacatePay na URL `api.`
