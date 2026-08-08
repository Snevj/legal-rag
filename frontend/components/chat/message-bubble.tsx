"use client";

import { FileText, TerminalSquare, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import type { ChatTurn } from "@/lib/types";

function AssistantAvatar() {
  return (
    <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-obsidian font-mono text-[11px] text-ash">
      §
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-1.5 animate-bounce rounded-full bg-ash"
          style={{ animationDelay: `${i * 120}ms` }}
        />
      ))}
    </div>
  );
}

export function MessageBubble({
  turn,
  onOpenDetails,
}: {
  turn: ChatTurn;
  onOpenDetails: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-1 duration-300">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-3xl rounded-tr-md bg-cobalt px-4 py-2.5 text-sm text-white shadow-[0_1px_0_rgba(255,255,255,0.08)_inset]">
          {turn.question}
        </div>
      </div>

      <div className="flex items-start gap-2.5">
        <AssistantAvatar />
        <div className="min-w-0 max-w-[85%] flex-1">
          <div
            className={cn(
              "rounded-3xl rounded-tl-md border px-4 py-3 text-sm",
              turn.error
                ? "border-status-bad/30 bg-status-bad-dim"
                : "border-border bg-graphite"
            )}
          >
            {turn.pending && <TypingDots />}

            {turn.error && (
              <div className="flex items-start gap-2 text-status-bad">
                <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                <span>{turn.error}</span>
              </div>
            )}

            {turn.response && (
              <>
                <p className="whitespace-pre-wrap leading-relaxed text-ivory">
                  {turn.response.answer}
                </p>

                {turn.response.sources.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {[
                      ...new Map(
                        turn.response.sources.map((s) => [s.source_title, s])
                      ).values(),
                    ].map((s) => (
                      <span
                        key={s.doc_id}
                        className="inline-flex items-center gap-1 rounded-full border border-border bg-obsidian/70 px-2 py-0.5 text-[11px] text-ash"
                      >
                        <FileText className="size-3" />
                        {s.source_title}
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          {turn.response && (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5 px-1">
              <StatusBadge tone="neutral">
                {turn.response.model_used}
              </StatusBadge>
              {turn.response.cache_hit && (
                <StatusBadge tone="good">cached</StatusBadge>
              )}
              {turn.response.escalated && (
                <StatusBadge tone="bad">escalated</StatusBadge>
              )}
              <Button
                variant="ghost"
                size="xs"
                onClick={onOpenDetails}
                className="ml-auto gap-1 text-ash hover:text-ivory"
              >
                <TerminalSquare className="size-3" />
                Details
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
