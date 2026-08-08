"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, AlertTriangle, Check } from "lucide-react";
import { NavBar } from "@/components/nav-bar";
import { AdminKeyBar } from "@/components/admin-key-bar";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, getEscalations, resolveEscalation } from "@/lib/api";
import type { EscalationRecord } from "@/lib/types";

function EscalationCard({
  record,
  adminKey,
  onResolved,
}: {
  record: EscalationRecord;
  adminKey: string;
  onResolved: (updated: EscalationRecord) => void;
}) {
  const [notes, setNotes] = useState("");
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleResolve() {
    setResolving(true);
    setError(null);
    try {
      const updated = await resolveEscalation(record.id, notes, adminKey || undefined);
      onResolved(updated);
    } catch (err) {
      setError(err instanceof ApiError ? `${err.status} ${err.message}` : "Failed to resolve");
    } finally {
      setResolving(false);
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1.5">
            {record.reasons.map((reason) => (
              <StatusBadge key={reason} tone="bad">
                {reason}
              </StatusBadge>
            ))}
          </div>
          <span className="font-mono text-[11px] text-ash">
            {new Date(record.created_at * 1000).toLocaleString()}
          </span>
        </div>

        <div>
          <p className="text-[11px] uppercase tracking-widest text-ash">
            Question
          </p>
          <p className="text-sm text-ivory">{record.question}</p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-widest text-ash">
            Answer
          </p>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">
            {record.answer}
          </p>
        </div>
        <p className="font-mono text-[11px] text-ash">
          session {record.session_id.slice(0, 16)}…
        </p>

        <div className="flex items-end gap-2 pt-1">
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Resolution notes (optional)"
            rows={1}
            className="min-h-9 flex-1 resize-none"
          />
          <Button onClick={handleResolve} disabled={resolving}>
            <Check className="size-4" />
            Resolve
          </Button>
        </div>
        {error && <p className="text-sm text-status-bad">{error}</p>}
      </CardContent>
    </Card>
  );
}

export default function EscalationsPage() {
  const [adminKey, setAdminKeyState] = useState("");
  const [records, setRecords] = useState<EscalationRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (key: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getEscalations(key || undefined);
      setRecords(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status} ${err.message}`
          : "Failed to load escalations"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(adminKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminKey]);

  return (
    <div className="flex min-h-screen flex-col bg-onyx">
      <NavBar />
      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ivory">
              Human-review escalations
            </h1>
            <p className="text-sm text-muted-foreground">
              Answers flagged by a guardrail — PII, prompt injection,
              ungrounded citation, or low grounding score.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <AdminKeyBar onChange={setAdminKeyState} />
            <Button
              variant="outline"
              size="icon"
              onClick={() => load(adminKey)}
              disabled={loading}
              aria-label="Refresh"
            >
              <RefreshCw className={loading ? "size-4 animate-spin" : "size-4"} />
            </Button>
          </div>
        </div>

        {error && (
          <Card className="mb-4 border-status-bad/30 bg-status-bad-dim">
            <CardContent className="flex items-center gap-2 py-4 text-sm text-status-bad">
              <AlertTriangle className="size-4 shrink-0" />
              {error}
            </CardContent>
          </Card>
        )}

        {!error && !loading && records.length === 0 && (
          <p className="py-12 text-center text-sm text-muted-foreground">
            No pending escalations.
          </p>
        )}

        <div className="space-y-3">
          {records.map((record) => (
            <EscalationCard
              key={record.id}
              record={record}
              adminKey={adminKey}
              onResolved={(updated) =>
                setRecords((prev) => prev.filter((r) => r.id !== updated.id))
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
}
