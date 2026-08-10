import type {
  ApiErrorBody,
  ChatHistoryTurn,
  EscalationRecord,
  HealthResponse,
  IngestResponse,
  QueryResponse,
  UsageResponse,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { adminKey?: string }
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.adminKey) {
    headers.set("X-API-Key", init.adminKey);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as ApiErrorBody;
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON - fall back to statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export function getHealth() {
  return request<HealthResponse>("/health");
}

export function postQuery(payload: {
  question: string;
  session_id?: string;
  priority?: number;
  request_human_review?: boolean;
}) {
  return request<QueryResponse>("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function postIngest(file: File, sessionId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (sessionId) {
    formData.append("session_id", sessionId);
  }
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: formData,
  });
}

export function getHistory(sessionId: string) {
  return request<ChatHistoryTurn[]>(`/history?session_id=${encodeURIComponent(sessionId)}`);
}

export function getUsage(sessionId: string | undefined, adminKey?: string) {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  return request<UsageResponse>(`/usage${qs}`, { adminKey });
}

export function getEscalations(adminKey?: string) {
  return request<EscalationRecord[]>("/escalations", { adminKey });
}

export function resolveEscalation(
  id: string,
  notes: string,
  adminKey?: string
) {
  return request<EscalationRecord>(`/escalations/${id}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
    adminKey,
  });
}
