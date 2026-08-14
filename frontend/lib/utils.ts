import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** crypto.randomUUID() only exists in secure contexts (HTTPS/localhost) -
 * this app is also served over plain HTTP, where it's undefined and throws.
 * Falls back to a non-cryptographic id, which is fine here since these are
 * just React keys / client-side identifiers, never security tokens. */
export function generateId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}
