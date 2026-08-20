# Scouter IA — Documento de Planejamento e Estruturação

**Autor:** Davi Tavares Frota  
**Data:** Agosto 2026  
**Status:** Planejamento inicial — pré-desenvolvimento

---

## 1. Visão Geral do Produto

Um aplicativo (Android + Web) que atua como um **scouter esportivo movido por IA**: analisa partidas de futebol usando dados estatísticos e contexto qualitativo, cruza essa análise com odds de mercado em tempo real, e entrega palpites classificados por nível de risco (conservador, moderado, arriscado), com explicação em linguagem natural do racional por trás de cada recomendação.

O produto **não é uma casa de apostas** — não processa apostas, não movimenta dinheiro de jogo, não precisa de outorga/licença da SPA/MF. É uma ferramenta de análise e conteúdo, similar em natureza a tipsters profissionais ou plataformas de scouting esportivo, mas com IA fazendo o trabalho analítico e explicativo.

### 1.1 Proposta de valor

- Para o apostador: decisões mais informadas, com transparência sobre a probabilidade real vs. a odd oferecida pelo mercado (conceito de "value bet").
- Diferencial: não é só "quem vai ganhar" — é "onde o mercado está precificando errado" + explicação legível, não uma caixa-preta.
- Prova social nativa: histórico público de acurácia dos palpites, construindo confiança ao longo do tempo.

### 1.2 Escopo do MVP

- **Esporte:** somente futebol (maior disponibilidade de dados estruturados).
- **Modelo de monetização:** freemium com assinatura.
- **Plataformas:** Web e Android desenvolvidos em paralelo.

---

## 2. Considerações Legais e Regulatórias

Referência: Lei nº 14.790/2023 ("Lei das Bets"), regulamentada pela Secretaria de Prêmios e Apostas (SPA/MF), em vigor desde 1º de janeiro de 2025.

**O que se aplica ao Scouter IA:**

- Como o app não aceita apostas nem processa pagamentos de prêmios, **não está sujeito à outorga de R$30 milhões nem à licença SPA/MF** — essa exigência é para operadoras de apostas de quota fixa.
- Se o app vier a promover ou linkar casas de apostas específicas (afiliação), a comunicação promocional relacionada a apostas deve seguir as restrições da lei: proibido tratar aposta como "investimento" ou "fonte de renda", proibido direcionar a menores de 18 anos, e avisos obrigatórios devem constar quando há publicidade de operadores (ex.: "Ministério da Fazenda adverte: Apostar pode causar dependência").
- Recomendação de produto (não jurídica): incluir desde o MVP uma seção de jogo responsável / disclaimer de que os palpites são análise probabilística e não garantia de resultado, e verificação de idade mínima (18+) no cadastro.

**Nota:** este documento não constitui aconselhamento jurídico. Antes do lançamento comercial, vale uma revisão por advogado especializado em direito regulatório/apostas, especialmente se o modelo de afiliação com casas de apostas for adotado no futuro.

---

## 3. Arquitetura do Produto

### 3.1 Blocos principais

1. **Ingestão de dados** — coleta contínua de estatísticas de partidas/times/jogadores e odds de múltiplas casas.
2. **Motor de análise** — combina modelo estatístico + IA (LLM) para gerar probabilidades e explicações.
3. **Motor de classificação de risco** — categoriza cada palpite em conservador / moderado / arriscado com score de confiança.
4. **Backend/API** — orquestra ingestão, análise, auth, paywall.
5. **Clientes** — Web (Next.js) e Android (React Native).
6. **Camada de pagamento/assinatura** — gerencia o modelo freemium.
7. **Sistema de notificações** — alertas de mudança de odds, início de jogos monitorados.

### 3.2 Diagrama textual do fluxo de dados

```
[APIs externas: estatísticas + odds]
          │
          ▼
[Serviço de Ingestão (Go/Fiber)] ──► [PostgreSQL / Supabase]
          │
          ▼
[Motor Estatístico (Poisson/Elo)] ──► probabilidades brutas
          │
          ▼
[Orquestrador LLM] ──► cruza contexto qualitativo (lesões, escalação,
          │             mando de campo) + gera explicação em linguagem natural
          ▼
[Motor de Classificação de Risco] ──► conservador / moderado / arriscado
          │
          ▼
[API pública] ──► [Web (Next.js)] + [App Android (React Native)]
          │
          ▼
[Push notifications via Firebase] (mudança de odds, alertas)
```

### 3.3 Stack técnica sugerida

| Camada | Tecnologia | Observação |
|---|---|---|
| Backend/API | Go + Fiber | Reaproveita padrão já validado no Webbotss |
| Modelagem estatística | Serviço Python separado (Poisson/Elo) | Pode migrar para Go depois se performance justificar |
| Orquestração LLM / RAG | Padrão já usado na Taxiana, adaptado ao domínio esportivo | Intent detection + contexto + geração explicativa |
| Banco de dados | PostgreSQL via Supabase | Auth + DB + realtime para odds mutáveis |
| Pagamento/assinatura | Asaas | Já integrado no MindCare (modelo subconta) |
| Web | Next.js | Consistente com stack atual |
| Android | React Native | Compartilha lógica/UI com o time web durante MVP paralelo |
| Notificações push | Firebase Cloud Messaging | Padrão para RN + Web |
| Observabilidade/custo de IA | Helicone | Já em uso na Taxiana para atribuição de custo por usuário |

### 3.4 Fontes de dados avaliadas

| Fonte | Tipo | Observação |
|---|---|---|
| API-Football (RapidAPI) | Estatísticas, escalações, H2H | Bom custo-benefício, plano free para validação |
| The Odds API | Odds em tempo real, múltiplas casas | Plano free ~500 req/mês, escala por uso |
| Sofascore | Estatísticas complementares | Via scraping — mais instável, usar como fallback |

---

## 4. Modelo de Negócio (Freemium)

### 4.1 Camada Free

- 1 categoria de mercado por dia (ex.: resultado 1x2).
- Odds atuais visíveis, sem histórico.
- Score de confiança visível, sem explicação detalhada.

### 4.2 Camada Assinante

- Todos os mercados analisados (over/under, ambas marcam, dupla chance, escanteios).
- Explicação completa gerada pela IA (racional do palpite).
- Filtro por nível de risco (conservador / moderado / arriscado).
- Comparação de odds entre casas (identificação de value bets).
- Alertas push de mudança significativa de odds em jogos monitorados.
- Histórico de acurácia do scouter — **recomendado incluir desde o MVP** como diferencial de confiança e retenção.

---

## 5. Modelo de Dados (rascunho inicial)

Entidades principais a estruturar no banco:

- `teams` — times, força de ataque/defesa histórica, liga.
- `matches` — partidas, data, mando de campo, status.
- `match_stats` — estatísticas por partida (gols, escanteios, cartões, xG quando disponível).
- `odds_snapshots` — odds coletadas por casa de apostas, com timestamp (série temporal).
- `predictions` — palpite gerado, mercado, probabilidade modelada, score de confiança, categoria de risco, explicação textual.
- `prediction_results` — resultado real vs. previsto, para alimentar o histórico público de acurácia.
- `users` — auth, plano (free/assinante), preferências de risco.
- `subscriptions` — status de assinatura via Asaas.
- `alerts` — configuração de alertas de odds por usuário.

Entidades adicionais recomendadas:

- `team_aliases` — resolução de identidades entre APIs (entity resolution).
- `match_mappings` — mapeamento de partidas entre fontes externas.
- `ai_usage_ledger` — controle de custo LLM por usuário (padrão reserve-then-confirm).

---

## 6. Roadmap

### Fase 0 — Fundação de dados (1–2 semanas)

- Estruturar pipeline de ingestão (Go/Fiber) para uma liga piloto (ex.: Brasileirão).
- Popular banco com histórico de partidas e estatísticas.
- Validar o modelo estatístico básico (Poisson) contra resultados reais antes de qualquer UI.
- Critério de saída: modelo gerando probabilidades plausíveis para jogos passados, validáveis manualmente.

### Fase 1 — MVP (análise + palpite básico)

- Ingestão de odds (The Odds API) para 2–3 ligas.
- Motor de análise gerando palpites 1x2 e over/under, com score de confiança (sem explicação em linguagem natural ainda).
- Web (Next.js) e App Android (React Native) com autenticação e paywall via Asaas.
- Estrutura de camada free vs. assinante implementada.
- Disclaimers de jogo responsável e verificação de idade no cadastro.
- Critério de saída: usuário consegue se cadastrar, ver palpites gratuitos, assinar e ver mercados adicionais.

### Fase 2 — Camada de IA explicativa

- Orquestrador LLM gerando o racional em linguagem natural para cada palpite.
- Expansão de mercados (dupla chance, escanteios, ambas marcam).
- Histórico de acurácia do scouter, público e visível para todos os usuários.
- Critério de saída: todo palpite pago vem acompanhado de explicação legível e rastreável.

### Fase 3 — Inteligência de mercado e personalização

- Comparação de odds entre múltiplas casas (identificação de value bets).
- Alertas push de mudança de odds em jogos monitorados.
- Personalização por perfil de risco do usuário (recomendações adaptadas ao histórico de preferência).
- Critério de saída: sistema de alertas funcionando em produção com push notifications confiáveis.

### Fase 4 — Expansão (pós-validação de mercado)

- Avaliação de expansão para outro esporte (basquete, tênis).
- Avaliação de modelo de afiliação com casas de apostas licenciadas (requer revisão jurídica prévia).
- Escalonamento de infraestrutura de dados conforme volume de usuários.

---

## 7. Riscos e Pontos de Atenção

- **Qualidade do dado é o gargalo real:** a precisão do modelo estatístico depende diretamente da qualidade e atualização das APIs de estatística — vale validar APIs antes de comprometer arquitetura.
- **Custo de IA por usuário:** geração de explicações via LLM em escala pode ficar cara — replicar o padrão de budget ledger (reserve-then-confirm) já usado na Taxiana faz sentido aqui também.
- **Percepção de "garantia de resultado":** é crítico que a UX e a comunicação deixem claro que são probabilidades, não certezas — tanto por responsabilidade com o usuário quanto por conformidade regulatória.
- **Dependência de scraping (Sofascore):** fontes não-oficiais podem quebrar sem aviso — tratar como fallback, não como fonte primária.

---

## 8. Próximos Passos Imediatos

1. Validar acesso e limites reais das APIs escolhidas (API-Football, The Odds API) com a liga piloto.
2. Desenhar o schema completo do banco (Fase 0) em detalhe antes de codar.
3. Gerar a spec técnica detalhada da Fase 1 (telas, endpoints, fluxo de auth + paywall) usando o padrão de feature spec já estabelecido.
4. Definir nome do produto, identidade visual básica e estrutura de branding (pode reaproveitar aprendizados de design system do MindCare).
