"use client";

import { useEffect, useRef, useState } from "react";
import { Scale } from "lucide-react";
import { NavBar } from "@/components/nav-bar";
import { Composer } from "@/components/chat/composer";
import { MessageBubble } from "@/components/chat/message-bubble";
import { TechnicalDrawer } from "@/components/chat/technical-drawer";
import { IngestDialog } from "@/components/chat/ingest-dialog";
import { Button } from "@/components/ui/button";
import { ApiError, postQuery } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import type { ChatTurn } from "@/lib/types";

const SUGGESTIONS = [
  "What did the Court hold in Gideon v. Wainwright about the right to counsel?",
  "Summarize the holding in Brown v. Board of Education.",
  "What was at issue in Marbury v. Madison?",
];

export default function Home() {
  const [sessionId, setSessionId] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [detailsId, setDetailsId] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [ingestOpen, setIngestOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Session id lives in localStorage, unavailable during SSR - this
    // one-time client read can't be a lazy useState initializer without
    // causing a hydration mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessionId(getOrCreateSessionId());
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns]);

  const pending = turns.some((t) => t.pending);

  async function handleSubmit(question: string) {
    const id = crypto.randomUUID();
    const turn: ChatTurn = {
      id,
      question,
      response: null,
      error: null,
      pending: true,
      askedAt: Date.now(),
    };
    setTurns((prev) => [...prev, turn]);
    setDetailsId(id);

    try {
      const response = await postQuery({
        question,
        session_id: sessionId || undefined,
      });
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, response, pending: false } : t))
      );
    } catch (err) {
      const message =
        err instanceof ApiError
          ? `${err.status} ${err.message}`
          : err instanceof Error
            ? err.message
            : "Request failed";
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id ? { ...t, error: message, pending: false } : t
        )
      );
    }
  }

  const detailsTurn = turns.find((t) => t.id === detailsId) ?? null;

  return (
    <div className="relative flex min-h-screen flex-col bg-onyx">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-[480px] bg-[radial-gradient(ellipse_60%_50%_at_50%_-10%,rgba(82,102,235,0.16),transparent)]"
      />
      <NavBar />

      <div className="flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
          {turns.length === 0 ? (
            <EmptyState onPick={handleSubmit} />
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-6">
              {turns.map((turn) => (
                <MessageBubble
                  key={turn.id}
                  turn={turn}
                  onOpenDetails={() => {
                    setDetailsId(turn.id);
                    setDetailsOpen(true);
                  }}
                />
              ))}
            </div>
          )}
        </div>
        <div className="mx-auto w-full max-w-3xl">
          <Composer
            onSubmit={handleSubmit}
            onIngestClick={() => setIngestOpen(true)}
            disabled={pending}
          />
        </div>
      </div>

      <TechnicalDrawer
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        turn={detailsTurn}
      />
      <IngestDialog open={ingestOpen} onOpenChange={setIngestOpen} />
    </div>
  );
}

function EmptyState({
  onPick,
}: {
  onPick: (question: string) => void;
}) {
  return (
    <div className="mx-auto flex max-w-lg flex-1 flex-col items-center justify-center gap-5 py-20 text-center">
      <div className="flex size-12 items-center justify-center rounded-full border border-border bg-graphite">
        <Scale className="size-5 text-cobalt" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-ivory">
          Ask about the ingested case law
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Answers are retrieved and reranked from indexed opinions, then
          grounded and cited against the source text.
        </p>
      </div>
      <div className="flex w-full flex-col gap-2">
        {SUGGESTIONS.map((s) => (
          <Button
            key={s}
            variant="outline"
            onClick={() => onPick(s)}
            className="h-auto justify-start whitespace-normal rounded-2xl px-4 py-2.5 text-left text-sm font-normal text-muted-foreground hover:border-cobalt/40 hover:text-ivory"
          >
            {s}
          </Button>
        ))}
      </div>
    </div>
  );
}
