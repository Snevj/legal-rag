"use client";

import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import type { ChatTurn } from "@/lib/types";

export function MessageBubble({
  turn,
  selected,
  onSelect,
}: {
  turn: ChatTurn;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-cobalt px-4 py-2.5 text-sm text-white">
          {turn.question}
        </div>
      </div>

      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "group flex justify-start text-left",
          "focus-visible:outline-none"
        )}
      >
        <div
          className={cn(
            "max-w-[85%] rounded-2xl rounded-tl-sm border px-4 py-3 text-sm transition-colors",
            selected
              ? "border-cobalt/50 bg-graphite"
              : "border-border bg-graphite/60 group-hover:border-slate-border/50"
          )}
        >
          {turn.pending && (
            <span className="font-mono text-xs text-ash">Thinking…</span>
          )}
          {turn.error && (
            <span className="text-status-bad">{turn.error}</span>
          )}
          {turn.response && (
            <>
              <p className="whitespace-pre-wrap text-ivory">
                {turn.response.answer}
              </p>
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                <StatusBadge tone="neutral">
                  {turn.response.model_used}
                </StatusBadge>
                {turn.response.cache_hit && (
                  <StatusBadge tone="good">cached</StatusBadge>
                )}
                {turn.response.escalated && (
                  <StatusBadge tone="bad">escalated</StatusBadge>
                )}
                <span className="ml-auto font-mono text-[10px] text-ash">
                  {selected ? "viewing details →" : "click for details"}
                </span>
              </div>
            </>
          )}
        </div>
      </button>
    </div>
  );
}
