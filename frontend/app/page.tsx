"use client";

import { useEffect, useRef, useState } from "react";
import { NavBar } from "@/components/nav-bar";
import { Composer } from "@/components/chat/composer";
import { MessageBubble } from "@/components/chat/message-bubble";
import { TechnicalPanel } from "@/components/chat/technical-panel";
import { IngestDialog } from "@/components/chat/ingest-dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ApiError, postQuery } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import type { ChatTurn } from "@/lib/types";

export default function Home() {
  const [sessionId, setSessionId] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
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
    setSelectedId(id);

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

  const selectedTurn =
    turns.find((t) => t.id === selectedId) ?? turns.at(-1) ?? null;

  return (
    <div className="flex min-h-screen flex-col bg-onyx">
      <NavBar />
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* Chat column */}
        <div className="flex min-h-0 flex-1 flex-col">
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-4 py-6 sm:px-6"
          >
            {turns.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="mx-auto flex max-w-3xl flex-col gap-6">
                {turns.map((turn) => (
                  <MessageBubble
                    key={turn.id}
                    turn={turn}
                    selected={turn.id === selectedTurn?.id}
                    onSelect={() => setSelectedId(turn.id)}
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

        {/* Technical panel - desktop: fixed side column. mobile: tab below. */}
        <div className="hidden w-[380px] shrink-0 border-l border-border bg-graphite/40 lg:block">
          <PanelHeader />
          <div className="h-[calc(100vh-3.5rem-2.5rem)]">
            <TechnicalPanel turn={selectedTurn} />
          </div>
        </div>

        <div className="border-t border-border bg-graphite/40 lg:hidden">
          <Tabs defaultValue="technical" className="gap-0">
            <TabsList className="w-full rounded-none border-b border-border bg-transparent">
              <TabsTrigger value="technical" className="flex-1">
                Technical details
              </TabsTrigger>
            </TabsList>
            <TabsContent value="technical" className="h-80">
              <TechnicalPanel turn={selectedTurn} />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <IngestDialog open={ingestOpen} onOpenChange={setIngestOpen} />
    </div>
  );
}

function PanelHeader() {
  return (
    <div className="flex h-14 shrink-0 items-center border-b border-border px-5">
      <span className="font-mono text-xs uppercase tracking-widest text-ash">
        Technical detail
      </span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mx-auto flex max-w-lg flex-1 flex-col items-center justify-center gap-3 py-24 text-center">
      <h1 className="font-heading text-2xl font-semibold text-ivory">
        Ask about the ingested case law
      </h1>
      <p className="text-sm text-muted-foreground">
        Answers are retrieved and reranked from indexed opinions, then
        grounded and cited. Try: &quot;What did the Court hold in Gideon v.
        Wainwright about the right to counsel?&quot;
      </p>
    </div>
  );
}
