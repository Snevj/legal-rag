"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { NavBar } from "@/components/nav-bar";
import { AdminKeyBar } from "@/components/admin-key-bar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, getUsage } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";
import type { UsageResponse } from "@/lib/types";

function BudgetBar({ used, limit }: { used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const tone = pct >= 90 ? "bg-status-bad" : pct >= 60 ? "bg-status-warn" : "bg-cobalt";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-obsidian">
      <div
        className={`h-full ${tone} transition-all`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div>
      <p className="font-mono text-[11px] uppercase tracking-widest text-ash">
        {label}
      </p>
      <p className="mt-1 font-mono text-2xl text-ivory">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

export default function UsagePage() {
  const [adminKey, setAdminKeyState] = useState("");
  const [data, setData] = useState<UsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (key: string) => {
    setLoading(true);
    setError(null);
    try {
      const sessionId = getOrCreateSessionId();
      const res = await getUsage(sessionId, key || undefined);
      setData(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status} ${err.message}`
          : "Failed to load usage"
      );
      setData(null);
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
              Cost &amp; budget usage
            </h1>
            <p className="text-sm text-muted-foreground">
              Cumulative token and cost tracking for today, global and
              per-session.
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

        {data && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Global budget</CardTitle>
                <CardDescription>
                  Shared across every session, protects the Groq key ·{" "}
                  {data.date}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Stat
                  label="tokens used"
                  value={data.global_tokens_used.toLocaleString()}
                  sub={`of ${data.global_token_budget.toLocaleString()} budget`}
                />
                <BudgetBar
                  used={data.global_tokens_used}
                  limit={data.global_token_budget}
                />
                <Stat
                  label="cost_usd"
                  value={`$${data.global_cost_usd.toFixed(6)}`}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>This session</CardTitle>
                <CardDescription>
                  Session ID: {getOrCreateSessionId().slice(0, 16)}…
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.session_token_budget != null ? (
                  <>
                    <Stat
                      label="tokens used"
                      value={(data.session_tokens_used ?? 0).toLocaleString()}
                      sub={`of ${data.session_token_budget.toLocaleString()} budget`}
                    />
                    <BudgetBar
                      used={data.session_tokens_used ?? 0}
                      limit={data.session_token_budget}
                    />
                    <Stat
                      label="cost_usd"
                      value={`$${(data.session_cost_usd ?? 0).toFixed(6)}`}
                    />
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No session data yet — ask a question first.
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
