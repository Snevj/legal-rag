"use client";

import { useEffect, useState } from "react";
import { KeyRound } from "lucide-react";
import { Input } from "@/components/ui/input";
import { getAdminKey, setAdminKey } from "@/lib/session";

export function AdminKeyBar({
  onChange,
}: {
  onChange: (key: string) => void;
}) {
  const [key, setKey] = useState("");

  useEffect(() => {
    const stored = getAdminKey();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setKey(stored);
    onChange(stored);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-graphite px-3 py-1.5">
      <KeyRound className="size-3.5 text-muted-foreground" />
      <Input
        value={key}
        onChange={(e) => {
          const next = e.target.value;
          setKey(next);
          setAdminKey(next);
          onChange(next);
        }}
        placeholder="ADMIN_API_KEY (optional, if configured on backend)"
        className="h-6 border-0 bg-transparent p-0 text-xs shadow-none focus-visible:ring-0"
      />
    </div>
  );
}
