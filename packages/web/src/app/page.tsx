type Prediction = {
  id: string;
  match_id: string;
  market: string;
  selection: string;
  model_probability: number | null;
  market_probability: number | null;
  edge: number | null;
  confidence_score: number | null;
  risk_label: string | null;
  value_decision: string;
  is_free_tier: boolean;
  published_at: string | null;
  created_at: string;
  home_team?: string | null;
  away_team?: string | null;
  kickoff_at?: string | null;
  match_status?: string | null;
  home_score?: number | null;
  away_score?: number | null;
  actual_outcome?: string | null;
  was_correct?: boolean | null;
  settled_at?: string | null;
};

type Accuracy = {
  id: string;
  market: string;
  risk_label: string | null;
  total_predictions: number;
  correct_predictions: number;
  accuracy_pct: number;
};

function pct(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function riskTone(label: string | null) {
  if (label === "conservative") return { bg: "#d7ebe0", fg: "#166534" };
  if (label === "moderate") return { bg: "#f3e7c8", fg: "#854d0e" };
  if (label === "risky") return { bg: "#f3d6d0", fg: "#9a3412" };
  return { bg: "#e8e4db", fg: "#5b685f" };
}

function formatKickoff(iso: string | null | undefined) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

function matchTitle(p: Prediction) {
  if (p.home_team && p.away_team) return `${p.home_team} × ${p.away_team}`;
  return p.match_id.slice(0, 8);
}

function scoreLine(p: Prediction) {
  if (p.home_score == null || p.away_score == null) return null;
  return `${p.home_score}–${p.away_score}`;
}

function apiBase() {
  return process.env.SCOUTER_API_ORIGIN ?? "http://127.0.0.1:8080";
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${apiBase()}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const [predictions, accuracy] = await Promise.all([
    fetchJson<{ count: number; items: Prediction[] }>("/v1/predictions?limit=30"),
    fetchJson<{ count: number; items: Accuracy[] }>("/v1/accuracy"),
  ]);

  const items = predictions?.items ?? [];
  const snapshots = accuracy?.items ?? [];
  const apiDown = !predictions;
  const settled = items.filter((p) => p.was_correct != null);
  const hits = settled.filter((p) => p.was_correct).length;

  return (
    <main
      style={{
        maxWidth: 960,
        margin: "0 auto",
        padding: "48px 20px 80px",
      }}
    >
      <header style={{ marginBottom: 40 }}>
        <p
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 14,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--pitch)",
            margin: 0,
          }}
        >
          Scouter IA
        </p>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(2.2rem, 5vw, 3.4rem)",
            lineHeight: 1.05,
            margin: "10px 0 12px",
            maxWidth: 16 * 16,
          }}
        >
          Palpites com risco explícito
        </h1>
        <p style={{ margin: 0, color: "var(--muted)", maxWidth: 520 }}>
          Análise estatística + mercado. Não é casa de apostas — conteúdo 18+ com
          responsabilidade.
        </p>
        {!apiDown && settled.length > 0 ? (
          <p style={{ margin: "14px 0 0", color: "var(--muted)", fontSize: 14 }}>
            Nesta lista: {hits}/{settled.length} settled corretos
          </p>
        ) : null}
      </header>

      {apiDown ? (
        <p
          style={{
            padding: "16px 18px",
            border: "1px solid var(--line)",
            background: "#fff8f0",
            color: "var(--warn)",
          }}
        >
          API indisponível em <code>:8080</code>. Suba com{" "}
          <code>go run ./cmd/api</code> em <code>packages/api</code>.
        </p>
      ) : null}

      {snapshots.length > 0 ? (
        <section style={{ marginBottom: 36 }}>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 20,
              margin: "0 0 14px",
            }}
          >
            Acurácia settled
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
            }}
          >
            {snapshots.map((s) => (
              <div
                key={s.id}
                style={{
                  borderTop: "3px solid var(--pitch)",
                  padding: "14px 0 8px",
                }}
              >
                <div style={{ fontSize: 13, color: "var(--muted)" }}>
                  {s.market} · {s.risk_label ?? "sem label"}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: 28,
                    marginTop: 4,
                  }}
                >
                  {Number(s.accuracy_pct).toFixed(0)}%
                </div>
                <div style={{ fontSize: 13, color: "var(--muted)" }}>
                  {s.correct_predictions}/{s.total_predictions}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: 12,
            marginBottom: 14,
          }}
        >
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: 20,
              margin: 0,
            }}
          >
            Predictions
          </h2>
          <span style={{ color: "var(--muted)", fontSize: 14 }}>
            {items.length} itens
          </span>
        </div>

        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {items.map((p) => {
            const tone = riskTone(p.risk_label);
            const score = scoreLine(p);
            const when = formatKickoff(p.kickoff_at);
            return (
              <li
                key={p.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  gap: 12,
                  padding: "16px 0",
                  borderBottom: "1px solid var(--line)",
                }}
              >
                <div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: 18,
                      marginBottom: 4,
                    }}
                  >
                    {matchTitle(p)}
                    {score ? ` · ${score}` : ""}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 8,
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <strong style={{ fontSize: 14 }}>
                      {p.market.toUpperCase()} · {p.selection}
                    </strong>
                    <span
                      style={{
                        fontSize: 12,
                        padding: "2px 8px",
                        background: tone.bg,
                        color: tone.fg,
                      }}
                    >
                      {p.risk_label ?? "unlabeled"}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--muted)" }}>
                      {p.value_decision}
                    </span>
                    {p.match_status ? (
                      <span style={{ fontSize: 12, color: "var(--muted)" }}>
                        {p.match_status}
                      </span>
                    ) : null}
                  </div>
                  <div style={{ fontSize: 14, color: "var(--muted)" }}>
                    modelo {pct(p.model_probability)} · mercado{" "}
                    {pct(p.market_probability)} · edge {pct(p.edge)}
                    {when ? ` · ${when}` : ""}
                  </div>
                </div>
                <div style={{ textAlign: "right", minWidth: 88 }}>
                  {p.was_correct == null ? (
                    <span style={{ color: "var(--muted)", fontSize: 13 }}>
                      aberto
                    </span>
                  ) : (
                    <span
                      style={{
                        color: p.was_correct ? "var(--ok)" : "var(--bad)",
                        fontFamily: "var(--font-display)",
                        fontSize: 18,
                      }}
                    >
                      {p.was_correct ? "acerto" : "erro"}
                    </span>
                  )}
                  {p.actual_outcome ? (
                    <div style={{ fontSize: 12, color: "var(--muted)" }}>
                      real: {p.actual_outcome}
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>

        {!apiDown && items.length === 0 ? (
          <p style={{ color: "var(--muted)" }}>Nenhuma prediction publicada.</p>
        ) : null}
      </section>
    </main>
  );
}
