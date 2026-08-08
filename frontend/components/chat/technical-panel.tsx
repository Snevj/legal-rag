"use client";

import { StatusBadge } from "@/components/status-badge";
import { Separator } from "@/components/ui/separator";
import type { ChatTurn } from "@/lib/types";

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-xs text-ivory">{children}</span>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1 mt-4 font-mono text-[11px] uppercase tracking-widest text-ash first:mt-0">
      {children}
    </p>
  );
}

export function TechnicalPanel({ turn }: { turn: ChatTurn | null }) {
  if (!turn) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="font-mono text-xs text-ash">
          {
            "// ask a question to see routing, guardrail, cost and latency telemetry here"
          }
        </p>
      </div>
    );
  }

  if (turn.pending) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="font-mono text-xs text-ash animate-pulse">
          {
            "// pipeline running — route → cache_lookup → retrieve → rerank → generate → guardrails → escalation"
          }
        </p>
      </div>
    );
  }

  if (turn.error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <StatusBadge tone="bad">error</StatusBadge>
        <p className="font-mono text-xs text-status-bad">{turn.error}</p>
      </div>
    );
  }

  const r = turn.response;
  if (!r) return null;

  const g = r.guardrails;

  return (
    <div className="h-full overflow-y-auto px-5 py-4">
      <SectionLabel>Routing</SectionLabel>
      <Row label="model_used">{r.model_used}</Row>
      <Row label="difficulty">
        <StatusBadge tone={r.difficulty === "hard" ? "warn" : "neutral"}>
          {r.difficulty}
        </StatusBadge>
      </Row>
      <Row label="cache_hit">
        <StatusBadge tone={r.cache_hit ? "good" : "neutral"}>
          {String(r.cache_hit)}
        </StatusBadge>
      </Row>
      <Row label="session_id">{r.session_id.slice(0, 12)}…</Row>

      <Separator className="my-3" />

      <SectionLabel>Cost &amp; latency</SectionLabel>
      <Row label="prompt_tokens">{r.prompt_tokens}</Row>
      <Row label="completion_tokens">{r.completion_tokens}</Row>
      <Row label="cost_usd">${r.cost_usd.toFixed(6)}</Row>
      <Row label="latency_ms">{r.latency_ms.toFixed(0)} ms</Row>

      <Separator className="my-3" />

      <SectionLabel>Guardrails</SectionLabel>
      <Row label="grounding_score">
        <StatusBadge
          tone={
            g.grounding_score >= 0.5
              ? "good"
              : g.grounding_score >= 0.15
                ? "warn"
                : "bad"
          }
        >
          {g.grounding_score.toFixed(2)}
        </StatusBadge>
      </Row>
      <Row label="ungrounded_citations">
        {g.ungrounded_citations.length ? (
          <StatusBadge tone="bad">
            {g.ungrounded_citations.length}
          </StatusBadge>
        ) : (
          <StatusBadge tone="good">0</StatusBadge>
        )}
      </Row>
      <Row label="injection_flagged">
        <StatusBadge tone={g.injection_flagged ? "bad" : "good"}>
          {String(g.injection_flagged)}
        </StatusBadge>
      </Row>
      <Row label="input_pii_detected">
        <StatusBadge tone={g.input_pii_detected ? "warn" : "good"}>
          {g.input_pii_types.join(", ") || "false"}
        </StatusBadge>
      </Row>
      <Row label="output_pii_detected">
        <StatusBadge tone={g.output_pii_detected ? "warn" : "good"}>
          {g.output_pii_types.join(", ") || "false"}
        </StatusBadge>
      </Row>
      <Row label="disclaimer_added">
        <StatusBadge tone={g.disclaimer_added ? "warn" : "neutral"}>
          {String(g.disclaimer_added)}
        </StatusBadge>
      </Row>

      <Separator className="my-3" />

      <SectionLabel>Escalation</SectionLabel>
      <Row label="escalated">
        <StatusBadge tone={r.escalated ? "bad" : "good"}>
          {String(r.escalated)}
        </StatusBadge>
      </Row>
      {r.escalation_reasons.length > 0 && (
        <ul className="mt-1 space-y-1 pl-1">
          {r.escalation_reasons.map((reason) => (
            <li
              key={reason}
              className="font-mono text-[11px] text-status-bad"
            >
              · {reason}
            </li>
          ))}
        </ul>
      )}

      <Separator className="my-3" />

      <SectionLabel>Retrieved sources ({r.sources.length})</SectionLabel>
      <div className="space-y-2">
        {r.sources.map((s) => (
          <div
            key={`${s.doc_id}-${s.chunk_index}`}
            className="rounded-lg border border-border bg-obsidian/60 p-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-ivory">
                {s.source_title}
              </span>
              <span className="font-mono text-[10px] text-ash">
                chunk {s.chunk_index} · score {s.score.toFixed(3)}
              </span>
            </div>
          </div>
        ))}
        {r.sources.length === 0 && (
          <p className="font-mono text-[11px] text-ash">
            (none — cache hit or no matching chunks)
          </p>
        )}
      </div>
    </div>
  );
}
