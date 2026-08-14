import { generateId } from "@/lib/utils";

const SESSION_KEY = "legal-rag:session_id";
const ADMIN_KEY_KEY = "legal-rag:admin_key";

function randomId(): string {
  return generateId().replace(/-/g, "");
}

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = randomId();
    window.localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function resetSessionId(): string {
  const id = randomId();
  if (typeof window !== "undefined") {
    window.localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(ADMIN_KEY_KEY) ?? "";
}

export function setAdminKey(key: string): void {
  if (typeof window === "undefined") return;
  if (key) {
    window.localStorage.setItem(ADMIN_KEY_KEY, key);
  } else {
    window.localStorage.removeItem(ADMIN_KEY_KEY);
  }
}
