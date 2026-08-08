"use client";

import { TerminalSquare } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { TechnicalPanel } from "@/components/chat/technical-panel";
import type { ChatTurn } from "@/lib/types";

export function TechnicalDrawer({
  open,
  onOpenChange,
  turn,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  turn: ChatTurn | null;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full border-border bg-graphite p-0 sm:max-w-md">
        <SheetHeader className="border-b border-border">
          <SheetTitle className="flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-ash">
            <TerminalSquare className="size-3.5 text-cobalt" />
            Technical detail
          </SheetTitle>
          <SheetDescription className="sr-only">
            Routing, cost, latency and guardrail telemetry for the selected
            answer.
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1">
          <TechnicalPanel turn={turn} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
