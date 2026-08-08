import { cn } from "@/lib/utils";

type Tone = "good" | "warn" | "bad" | "neutral";

const toneClasses: Record<Tone, string> = {
  good: "bg-status-good-dim text-status-good border-status-good/30",
  warn: "bg-status-warn-dim text-status-warn border-status-warn/30",
  bad: "bg-status-bad-dim text-status-bad border-status-bad/30",
  neutral: "bg-obsidian text-ash border-slate-border/30",
};

export function StatusBadge({
  tone,
  children,
  className,
}: {
  tone: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[11px] leading-none tracking-tight",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
