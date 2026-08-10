"use client";

import { useRef, useState } from "react";
import { CheckCircle2, Loader2, TriangleAlert, UploadCloud, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { postIngest } from "@/lib/api";

type FileStatus = "queued" | "uploading" | "done" | "error";

interface QueuedFile {
  id: string;
  file: File;
  status: FileStatus;
  numChunks?: number;
  error?: string;
}

function StatusIcon({ status }: { status: FileStatus }) {
  if (status === "uploading")
    return <Loader2 className="size-4 animate-spin text-ash" />;
  if (status === "done")
    return <CheckCircle2 className="size-4 text-status-good" />;
  if (status === "error")
    return <TriangleAlert className="size-4 text-status-bad" />;
  return <span className="size-4" />;
}

export function IngestDialog({
  open,
  onOpenChange,
  sessionId,
  onIngested,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sessionId?: string;
  onIngested?: (sourceTitle: string) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [uploading, setUploading] = useState(false);

  function addFiles(files: FileList | null) {
    if (!files) return;
    const next: QueuedFile[] = Array.from(files).map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: "queued",
    }));
    setQueue((prev) => [...prev, ...next]);
  }

  function removeFile(id: string) {
    setQueue((prev) => prev.filter((q) => q.id !== id));
  }

  async function handleUploadAll() {
    setUploading(true);
    for (const item of queue) {
      if (item.status === "done") continue;
      setQueue((prev) =>
        prev.map((q) => (q.id === item.id ? { ...q, status: "uploading" } : q))
      );
      try {
        const res = await postIngest(item.file, sessionId);
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? { ...q, status: "done", numChunks: res.num_chunks }
              : q
          )
        );
        onIngested?.(res.source_title);
      } catch (err) {
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? {
                  ...q,
                  status: "error",
                  error: err instanceof Error ? err.message : "Upload failed",
                }
              : q
          )
        );
      }
    }
    setUploading(false);
  }

  function reset() {
    setQueue([]);
    setUploading(false);
  }

  const hasPending = queue.some((q) => q.status !== "done");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload documents</DialogTitle>
          <DialogDescription>
            PDF or plain text, one or many at once. Each is chunked, embedded,
            and indexed into the vector store so questions can be answered
            against it.
          </DialogDescription>
        </DialogHeader>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-border/60 bg-obsidian/40 px-6 py-8 text-center transition-colors hover:border-cobalt/50"
        >
          <UploadCloud className="size-6 text-muted-foreground" />
          <span className="text-sm text-ivory">
            Click to choose files
          </span>
          <span className="text-xs text-muted-foreground">
            .pdf or .txt · multiple allowed
          </span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,text/plain,application/pdf"
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            e.target.value = "";
          }}
        />

        {queue.length > 0 && (
          <div className="max-h-56 space-y-1.5 overflow-y-auto">
            {queue.map((item) => (
              <div
                key={item.id}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-2.5 py-2 text-xs",
                  item.status === "error"
                    ? "border-status-bad/30 bg-status-bad-dim"
                    : item.status === "done"
                      ? "border-status-good/30 bg-status-good-dim"
                      : "border-border bg-obsidian/50"
                )}
              >
                <StatusIcon status={item.status} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-ivory">{item.file.name}</p>
                  {item.status === "done" && (
                    <p className="font-mono text-[10px] text-status-good">
                      {item.numChunks} chunks ingested
                    </p>
                  )}
                  {item.status === "error" && (
                    <p className="text-[10px] text-status-bad">{item.error}</p>
                  )}
                </div>
                {item.status !== "uploading" && item.status !== "done" && (
                  <button
                    type="button"
                    onClick={() => removeFile(item.id)}
                    className="shrink-0 text-ash hover:text-ivory"
                    aria-label={`Remove ${item.file.name}`}
                  >
                    <X className="size-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            onClick={handleUploadAll}
            disabled={queue.length === 0 || uploading || !hasPending}
          >
            {uploading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              `Ingest ${queue.filter((q) => q.status !== "done").length || ""}`.trim()
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
