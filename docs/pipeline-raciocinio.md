# Pipeline de raciocínio — Scouter IA

**Status:** spec de design (não é código)  
**Data:** Agosto 2026  
**Princípio constitucional:** o LLM não é a fonte da probabilidade. Código produz número. LLM classifica evidência, aplica playbook e explica. LLM nunca “ajusta no feeling”.

Este documento define o julgamento sob incerteza — o núcleo do produto. Erro aqui não é bug de UX: é o scouter dando conselho ruim com aparência de conselho bom.

---

## 0. Por que o desenho ingênuo falha

O desenho que *parece* óbvio:

> Poisson gera 72% de vitória do mandante → LLM lê lesões/motivação → “na verdade é 61%” → classifica risco → escreve o texto.

Isso é exatamente o tipo de tarefa em que um modelo mais fraco (e muitos modelos fortes, sem restrição) **soa calibrado sem estar**. Três falhas estruturais:

1. **Double counting.** Mando de campo já está no Poisson. Sequência recente já está no Elo. O LLM soma de novo.
2. **Ajuste sem incerteza.** O modelo reduz a probabilidade e *aumenta* a confiança (“agora tenho a informação da lesão”). O correto é o oposto: sair do prior calibrado **alarga** o intervalo.
3. **Sem direito a calar.** Tipster sempre tem palpite. Um scouter calibrado se abstém. Se o pipeline não tiver `ABSTAIN` como saída de primeira classe, ele vai forçar recomendação em cima de ruído.

A analogia correta não é “chat que analisa futebol”. É o pipeline já validado na Reforma Tributária:

```
intent → playbook → retrieval → validação → geração → juiz
```

Lá, o modelo não inventa alíquota. Aqui, o modelo não inventa probabilidade.

| Reforma Tributária | Scouter IA |
|---|---|
| Intent jurídico | Intent de mercado (1x2, O/U, BTTS…) |
| Playbook (quais artigos, o que é proibido afirmar) | Playbook (quais sinais cabem, caps, o que é proibido double-count) |
| Retrieval (leis, âncoras, FAQ) | Context pack estruturado (stats, odds, desfalques, tabela) |
| Validator / sanitizer (só restringe claims) | Crítico assimétrico (só piora risco ou abstém) |
| Geração (texto grounded) | Explicação (texto grounded nos números já travados) |
| Juiz | Juiz de consistência + linguagem (sem certeza, sem “investimento”) |

Custo: o julgamento roda **uma vez por** `(match_id, market, odds_hash, context_hash)` e é cacheado. Assinante não dispara LLM. Helicone atribui custo ao jogo, não ao usuário.

---

## 1. Quem é dono de cada número

| Artefato | Dono | LLM pode? |
|---|---|---|
| `p_prior` (Poisson/Elo) | Código | Ler. Nunca reescrever. |
| `λ_home`, `λ_away` | Código | Ler. |
| Sinais qualitativos tipados | LLM extrai; código valida fonte | Classificar. Não inventar magnitude. |
| `δ` de ajuste (caps do playbook) | Código | Não. |
| `p_adj`, intervalo de credibilidade | Código | Não. |
| `p_fair` (odd desvigada) | Código | Não. |
| `edge`, decisão value / ruído / abster | Código | Não. |
| Label de risco | Código + veto do crítico | Só piorar (nunca promover a “conservador”). |
| Texto de explicação | LLM | Sim, depois dos números travados. |

Regra de ouro: **se o LLM desaparecer, o produto ainda emite palpite estatístico + abstenção**. O LLM adiciona sinais e explicação. Não é o cérebro da probabilidade.

---

## 2. Pipeline (8 estágios)

```
[0 Prior estatístico]          código
        │
        ▼
[1 Intent de mercado]          classificador / regras
        │
        ▼
[2 Context pack]               retrieval estruturado (não RAG solto)
        │
        ▼
[3 Extração de sinais]         LLM schema-constrained
        │
        ▼
[4 Playbooks de ajuste]        código (caps, anti-double-count)
        │
        ▼
[5 Motor de value]             código (desvig + IC + self-distrust)
        │
        ▼
[6 Calibrador de risco]        código (regras + vetos)
        │
        ▼
[7 Crítico assimétrico]        LLM caro — só piora ou abstém
        │         │
        │         └── (loop limitado) volta ao 4 se achou sinal não aplicado
        ▼
[8 Explicação + juiz]          LLM barato (texto) + juiz (consistência)
```

`ABSTAIN` pode ser emitido nos estágios 5, 6 ou 7. É sucesso, não falha.

---

## 3. Estágio 0 — Prior estatístico

Modelo-base (Fase 0): Poisson independente ou Dixon-Coles para 1x2; totais derivados da soma das λ; BTTS da independência (com correção Dixon-Coles se disponível). Elo como regularizador de força quando a amostra da temporada é curta.

Contrato de saída — o resto do pipeline só consome isto:

```json
{
  "match_id": "br-2026-flamengo-juventude",
  "model_version": "poisson-dc-v0.1",
  "sample": { "matches_home_season": 12, "matches_away_season": 12, "thin_data": false },
  "lambda": { "home": 1.84, "away": 0.71 },
  "p_prior": { "home": 0.72, "draw": 0.18, "away": 0.10 },
  "derived": { "over_25": 0.61, "btts": 0.48 },
  "already_in_model": ["home_advantage", "recent_form_via_elo"],
  "calibration_bucket": "brasileirao-1x2"
}
```

`already_in_model` é âncora anti-double-count. O playbook de mando de campo é **no-op**, salvo anomalia de venue (portões fechados, altitude extrema, estádio novo). Forma recente não é reaplicada como “momento”.

O prior precisa de **intervalo**, não só ponto. Na Fase 0 isso pode ser bootstrap residual ou regra: `se` cresce quando `thin_data`, quando λ foi estimada com n < 8, ou quando o time foi promovido. Sem intervalo não existe teste de value vs ruído.

---

## 4. Estágio 1 — Intent de mercado

Não é intent do usuário. É intent da *unidade de decisão*.

Cada mercado tem playbook próprio porque o mesmo sinal não pesa igual:

| Mercado | O que o prior já cobre bem | Sinal qualitativo que mais mexe |
|---|---|---|
| 1x2 | Força relativa + mando | Desfalque de peça tática, motivação assimétrica |
| Over/under 2.5 | λ soma | Desfalque de atacantes *e* zagueiros; ritmo (congestionamento) |
| BTTS | Independência dos ataques | Um ataque decapitado vs defesa titular |
| Dupla chance | 1x2 agregado | Só existe se 1x2 está no limiar |
| Escanteios | Fraco no Poisson de gols | Pressão territorial — **abster no MVP** se o modelo de gols for a única fonte |

Regra de produto: **não emitir palpite num mercado cujo modelo não foi calibrado**. Escanteios sem modelo de escanteios = `ABSTAIN`, não “o LLM chuta”.

---

## 5. Estágio 2 — Context pack (retrieval)

Não é RAG de texto solto. É um pacote determinístico, com campos `KNOWN` / `UNKNOWN`. `UNKNOWN` é cidadão de primeira classe — alimenta o self-distrust.

```json
{
  "lineup": { "status": "UNKNOWN", "confirmed_at": null },
  "absences": [
    { "player": "Arrascaeta", "status": "confirmed_out", "role": "creator",
      "xg_share_90d": 0.22, "minutes_share": 0.81, "source": "api-football" }
  ],
  "rest_days": { "home": 3, "away": 6 },
  "fixture_congestion": { "home_minutes_7d": 720, "away_minutes_7d": 90 },
  "table": { "home_need": "title_race", "away_need": "relegation_six_pointer" },
  "tournament_state": { "already_qualified": { "home": false, "away": false } },
  "venue_anomaly": null,
  "odds": { "book": "pinnacle", "home": 1.40, "draw": 4.60, "away": 8.50, "ts": "..." },
  "missing": ["lineup", "weather"]
}
```

Ordem de autoridade da evidência (playbook de retrieval):

1. Escalação confirmada > rumor de desfalque > “motivação”
2. Dado de tabela (posição, jogos restantes) > narrativa de “vão jogar com vontade”
3. Fonte primária (API-Football) > fallback (Sofascore) > texto livre

Se a escalação está confirmada, **motivação genérica é ignorada**. Time “já classificado” que escalou o XI titular não ganha δ de desmotivação.

---

## 6. Estágio 3 — Extração de sinais (LLM, schema-constrained)

Tarefa do modelo: *o que existe neste pacote*, não *quanto vale*.

Contrato:

```json
{
  "signals": [
    {
      "id": "sig-01",
      "type": "absence",
      "team": "home",
      "polarity": "negative_attack",
      "evidence_ids": ["absences[0]"],
      "player_importance": "high",
      "notes": "criador com 22% do xG do time em 90d"
    }
  ],
  "unused_pack_fields": ["table.away_need"],
  "double_count_risks": ["home_advantage already_in_model"],
  "information_completeness": 0.62
}
```

Proibições no system prompt:

- Não emitir probabilidade, odd, nem δ numérico.
- Todo sinal precisa de `evidence_ids` apontando para o pack. Sem evidência → sinal inválido (validator dropa).
- Não reemitir `home_advantage` nem `recent_form` se estão em `already_in_model`.
- Se `lineup.status = CONFIRMED`, não emitir sinal de `motivation` genérico.
- Completeness < 1 não é vergonha; é input do estágio 5.

Modelo: **caro** neste estágio só quando o pack é ambíguo (lesões “doubtful”, copa, times recém-promovidos). Pack limpo e 100% estruturado pode ir para modelo médio com JSON schema. O volume é por jogo, não por usuário.

---

## 7. Estágio 4 — Playbooks de ajuste (código)

O LLM escolhe o *tipo* de sinal. O playbook escolhe a *magnitude*, com teto.

Ajuste acontece em **espaço de λ (gols esperados)** ou log-odds — nunca somando pontos percentuais em cima de `p_home` (quebra o simplex e calibra mal).

### 7.1 Ausência / desfalque

```
δλ_attack = − min(cap, k * xg_share * replacement_gap)
```

- `cap` típico: 0.25–0.35 gols esperados por time (um jogo não perde 40% do ataque por um jogador, salvo goleiro).
- Três titulares: soma com **diminishing returns** (não 3 × o mesmo cap). Teto de equipe, não de jogador.
- Reposição like-for-like (reserva com xG similar) → δ ≈ 0. O LLM marca `player_importance`; o código consulta o xG share.

### 7.2 Congestionamento / descanso assimétrico

Só aplica se a diferença de descanso for ≥ 2 dias **e** minutos recentes do XI provável forem assimétricos. Magnitude pequena (cap ~0.10 λ). Elo recente já come parte disso — cap menor se `recent_form_via_elo` está no prior.

### 7.3 Mando de campo

**No-op.** Exceção: `venue_anomaly` evidenciada (portões fechados, mando invertido, altitude). Sem anomalia, o extrator que emitir `home_advantage` tem o sinal dropado pelo validator.

### 7.4 Motivação (o sinal mais perigoso)

Tipsters superestimam isso. Regras:

| Condição | δ permitido |
|---|---|
| Escalação confirmada | 0 — a escalação já materializou a motivação |
| `already_qualified` + lineup UNKNOWN + histórico de rotação nesse clube | cap pequeno em λ, e **alarga** o IC |
| Six-pointer de rebaixamento vs. meio de tabela sem grife | cap pequeno, só se a tabela está no pack |
| Narrativa sem fato de tabela | 0 |

Motivação nunca vira palpite sozinha. É modificador residual.

### 7.5 Composição e incerteza

Dois efeitos obrigatórios depois de qualquer |δλ| > 0:

1. Recalcular `p_adj` a partir das λ ajustadas (simplex intacto).
2. **Alargar** o intervalo: `se_adj² = se_prior² + τ² * |δλ|`.

Sair do prior calibrado **aumenta** incerteza. O produto não pode ficar “mais certo porque leu o jornal”.

`τ` é hiperparâmetro a calibrar no backtest (Fase 0/1). Até lá, ser conservador em `τ` (largo) é o default certo.

---

## 8. Estágio 5 — Value bet: sinal vs ruído

Fórmula conceitual:

```
p_fair = desvig(odds)          # overround removido (multiplicativo ou Shin)
edge   = p_adj − p_fair
```

`edge > 0` **não** é value. Value é:

```
publicar VALUE iff
  edge > k * se_adj            # k ∈ [1.5, 2.0] no MVP
  AND information_completeness ≥ θ
  AND mercado calibrado (não liga obscura sem histórico)
  AND crítico não vetou
```

Caso contrário:

| Situação | Saída |
|---|---|
| `|edge| ≤ k * se_adj` | `NOISE` — mercado e modelo concordam dentro do erro |
| completeness baixa | `ABSTAIN` |
| `thin_data` e edge não é enorme | `ABSTAIN` |
| edge grande **contra** o mercado | possível `VALUE`, mas risco sobe de categoria (ver §9) |

**Self-distrust (o modelo desconfiar de si):**

- Amostra curta, promovido, copa com XI misto, lineup UNKNOWN, |δλ| grande → `se_adj` sobe. O teste `edge > k * se` fica mais duro. O sistema se cala em vez de forçar.
- Discordância enorme vs. mercado (ex.: modelo 55%, mercado 72%) é *evidência contra o modelo* até existir razão estrutural documentada no pack (desfalque confirmado que o mercado ainda não precificou, ou o contrário). Sem razão → `ABSTAIN`, não “achei value”.

Desvig: nunca comparar `p_adj` com `1/odd` cru. Odd 1.40 com overround de 6% não é 71,4% fair.

Kelly **não** entra no MVP de produto (não somos banca). Edge normalizado pode existir internamente para ranquear, não para sugerir stake.

---

## 9. Estágio 6 — Calibração de risco (o erro pior possível)

**Conservador ≠ favorito.**

Favorito com 3 desfalques *parece* conservador e é o pior conselho que o scouter pode dar: alta confiança cosmética em cima de prior obsoleto.

### 9.1 Definição operacional

| Label | Significa de verdade |
|---|---|
| `conservador` | Modelo e mercado **concordam**, informação **completa**, ajustes **pequenos**, intervalo **não cruza** a próxima opção, nenhum red flag qualitativo aberto. |
| `moderado` | Lean claro, mas IC mais largo, **ou** um sinal qualitativo de impacto médio, **ou** edge leve. |
| `arriscado` | Está **fadeando o mercado**, **ou** |δλ| grande, **ou** informação incompleta, **ou** o ajuste **inverteu** o prior. |
| `ABSTAIN` | Qualquer veto abaixo. Não publicar palpite naquele mercado. |

Implicação de produto que o doc original não tinha: **não existe “value bet conservador”**. Se você afirma que o mercado está errado, isso é no mínimo `moderado`, em geral `arriscado`. Conservador é andar *com* o mercado e com o modelo, em jogo informacionalmente limpo.

### 9.2 Vetos duros — nunca pode ser `conservador` se

- Lineup `UNKNOWN` **e** ≥ 2 desfalques de importância `high` (confirmados ou doubtful).
- ≥ 3 titulares fora (mesmo com lineup).
- Pick discorda do mercado em mais de `X` pp sem razão estrutural no pack (`X` inicial: 8 pp em 1x2).
- `thin_data` ou completeness < 0.7.
- O crítico (§10) apontou hidden risk não mitigado.
- O palpite é value (edge passou o teste). Value herda no mínimo `moderado`.

Caso canônico: time a 1.40, Poisson 72%, três titulares fora, `p_adj` cai para 58%, mercado ainda ~68% fair.

- Palpite “casa conservador” = **proibido**.
- Value na casa = **não** (`p_adj` < `p_fair`).
- Saída honesta: `ABSTAIN` em 1x2, ou dupla chance / under se o playbook desses mercados passar nos gates — com label `moderado` ou `arriscado`, nunca `conservador`.

### 9.3 Score interno (não é o label)

```
robustness = 1
  − incompleteness
  − sensitivity_to_one_more_injury
  − |δλ| / λ_prior
  − 1[disagrees_market]
```

O label é discretização **com vetos**. Não é argmax de um softmax do LLM.

Sensibilidade: se um desfalque a mais (o próximo “doubtful”) inverteria o pick, o label sobe. Conservador exige que o pick sobreviva a um choque razoável.

---

## 10. Estágio 7 — Crítico assimétrico (LLM caro)

Depois do label, um segundo passo — o equivalente ao sanitizer/juiz da Taxiana que **só restringe**.

Pergunta única:

> Qual o fator que faria este conselho *parecer* sólido e ser ruim? Se existir e não tiver sido aplicado, vete.

Contrato de saída:

```json
{
  "hidden_risks": [
    { "claim": "três desfalques no favorito não foram suficientes para impedir label conservador",
      "severity": "high", "action": "veto_conservative" }
  ],
  "action": "downgrade" | "abstain" | "pass",
  "cannot_upgrade": true
}
```

Assimetría explícita no prompt: **é inválido** o crítico promover `arriscado` → `conservador`. Só `pass`, `downgrade` ou `abstain`.

Loop de volta ao estágio 4: no máximo **uma** vez, e só se o hidden risk tiver `evidence_ids` no pack que o extrator pulou. Sem evidência no pack, o crítico não inventa lesão — ele **alarga incerteza / abstém**.

Este é o estágio que justifica modelo caro. Não é geração de texto. É o julgamento “desconfie de nós mesmos”.

Quando rodar o caro:

- Sempre que o calibrador quiser emitir `conservador`.
- Sempre que `edge` passar o teste de value.
- Amostragem nos demais (orçamento Helicone).

---

## 11. Estágio 8 — Explicação + juiz

Números já travados entram como JSON read-only. O texto **não pode** contradizer `p_adj`, label, nem a decisão `VALUE|NOISE|ABSTAIN`.

Modelo barato serve: a tarefa agora é escrita, não julgamento.

Proibições de linguagem (juiz, checklist automático + LLM):

- Sem “certeza”, “garantido”, “vai ganhar”.
- Sem “investimento”, “renda”, “lucro fácil” (Lei 14.790).
- Sem inventar desfalque, escalação ou odd que não está no JSON.
- Se a saída é `ABSTAIN`, o texto explica *por que calamos*, não substitui por um palpite “de coragem”.
- Probabilidades em linguagem humana batem com os números (“cerca de 6 em 10”, não “deve ganhar fácil”).

Se o juiz falha: regenerar texto (barato) ou bloquear publicação. Nunca “corrigir” o número para casar com a prosa.

---

## 12. System design dos prompts (não da infra)

Três prompts. Três contratos. Nenhum deles pede “analise o jogo e dê um palpite”.

### 12.1 Extrator (`role: signal_extractor`)

```
Você extrai sinais de um context pack. Você não calcula probabilidade.

Já está no modelo estatístico (NÃO reemitir): {already_in_model}.

Regras:
- Todo sinal exige evidence_ids do pack.
- Sem evidência → omita.
- lineup CONFIRMED anula motivation genérica.
- UNKNOWN é válido; reporte em information_completeness.
- Saída: JSON no schema X. Nada fora do schema.
```

### 12.2 Crítico (`role: asymmetric_critic`)

```
Você é o sanitizer. Só pode pass / downgrade / abstain.
É erro grave promover confiança.

Pergunte: o que faria este palpite parecer conservador e ser ruim?
Se o label for conservador e existir desfalque high / lineup UNKNOWN /
discordância de mercado / thin_data, vete.

Não invente fatos fora do pack. Sem fato → alargue incerteza ou abstain,
não invente δ.
```

### 12.3 Explicador (`role: explainer`)

```
Os números abaixo estão travados. Você não os altera.
Explique o racional em português claro, sem certeza, sem linguagem de investimento.
Se action=ABSTAIN, explique a abstenção.
Cite só evidências presentes no JSON.
```

Playbooks (como na Taxiana) são **artefatos versionados** (`playbooks/1x2.md`, `playbooks/ou25.md`), não prosa enterrada no system prompt. O orquestrador injeta só o playbook do intent de mercado.

---

## 13. Exemplo trabalhado (o caso que o produto tem que acertar)

Flamengo (casa) vs. Juventude. Odd casa 1.40. Poisson: `p_home = 0.72`, λ 1.84 / 0.71. Mercado fair ≈ 0.68. Três titulares do Flamengo confirmados fora, lineup ainda UNKNOWN. Completeness 0.55.

| Estágio | O que acontece |
|---|---|
| Prior | Casa 72% — *parece* conservador |
| Pack | 3 absences high, lineup UNKNOWN, mercado 1.40 |
| Extrator | 3 sinais `absence` / `negative_attack`; não emite mando de campo |
| Ajuste | δλ_home cap de equipe → λ 1.84 → ~1.52; `p_adj_home` ~0.58; **IC alarga** |
| Value | 0.58 − 0.68 = −0.10 → sem value na casa; possível ruído ou value no empate/visitante, mas IC largo + completeness baixa → **ABSTAIN 1x2** |
| Risco | Vetos: 3 titulares, lineup UNKNOWN, completeness < 0.7. `conservador` impossível |
| Crítico | Se alguém tentasse publicar “casa conservador”, veto imediato |
| Texto | “Não há palpite conservador neste jogo: o prior favorece o mandante, mas os desfalques e a escalação indefinida deixam o intervalo largo demais para recomendar.” |

Se o pipeline publicar “Flamengo conservador” neste jogo, o desenho falhou — independentemente de o Flamengo ganhar. Acerto de resultado não absolve erro de calibração.

---

## 14. O que a Fase 0/1 precisa medir (senão isso é opinião)

Antes de UI, o backtest tem que responder:

1. **Brier / log-loss** do prior vs. prior+ajustes, por liga. Ajuste qualitativo que piora Brier é playbook errado — desligar o sinal.
2. **Cobertura do IC:** em 70% dos jogos, o resultado cai dentro do intervalo declarado? Se o IC é teatro, o teste de value é teatro.
3. **Taxa de abstenção** por mercado. Se for ~0%, os gates não estão mordendo.
4. **Taxa de `conservador` que falha** vs. `arriscado` que falha. Conservador tem que ser *claramente* melhor. Se não for, os vetos estão frouxos.
5. **Discordância vs. mercado:** quando abstivemos por self-distrust, o mercado estava certo com que frequência? (Calibração de humildade.)

Sinal que deve piorar Brier na primeira versão e talvez seja desligado: motivação. Por isso entra com cap mínimo e evidência máxima.

---

## 15. Decisões travadas nesta sessão

1. LLM não emite probabilidade. Ponto.
2. Ajuste em λ / log-odds, com cap e diminishing returns, nunca em pontos percentuais soltos.
3. Sair do prior **alarga** incerteza.
4. `ABSTAIN` é saída de primeira classe.
5. Não existe value bet conservador.
6. Conservador ≠ favorito; vetos duros listados em §9.2.
7. Crítico é assimétrico (só piora), como o sanitizer da Taxiana.
8. Motivação cede à escalação; mando de campo já está no modelo.
9. Julgamento cacheado por jogo; explicação é texto barato em cima de JSON travado.
10. Mercado sem modelo calibrado (ex.: escanteios no MVP) = abster, não improvisar.

Aberto para a Fase 0 (números, não filosofia): valores exatos de `cap`, `τ`, `k`, `θ`, `X`. Devem sair do backtest, não de intuição.
