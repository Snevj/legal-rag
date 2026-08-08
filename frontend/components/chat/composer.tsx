"use client";

import { useRef, useState } from "react";
import { ArrowUp, Paperclip, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export function Composer({
  onSubmit,
  onIngestClick,
  disabled,
}: {
  onSubmit: (question: string) => void;
  onIngestClick: () => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
    requestAnimationFrame(() => textareaRef.current?.focus());
  }

  return (
    <div className="border-t border-border bg-onyx px-4 py-4 sm:px-6">
      <div
        className={cn(
          "flex items-end gap-2 rounded-3xl border border-border bg-graphite p-2 pl-4 transition-colors focus-within:border-cobalt/50"
        )}
      >
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="mb-0.5 shrink-0 text-muted-foreground hover:text-foreground"
          onClick={onIngestClick}
          aria-label="Upload document"
        >
          <Paperclip className="size-4" />
        </Button>
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask a question about the ingested case law…"
          rows={1}
          className="max-h-40 min-h-9 flex-1 resize-none border-0 bg-transparent px-1 py-1.5 shadow-none focus-visible:ring-0"
        />
        <Button
          type="button"
          size="icon"
          className="mb-0.5 shrink-0 rounded-full"
          disabled={disabled || !value.trim()}
          onClick={submit}
          aria-label="Send"
        >
          {disabled ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <ArrowUp className="size-4" />
          )}
        </Button>
      </div>
      <p className="mt-2 text-center text-[11px] text-muted-foreground">
        Legal research assistance only — not legal advice. Verify citations
        against primary sources.
      </p>
    </div>
  );
}
