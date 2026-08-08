"use client";

import { useRef, useState } from "react";
import { Loader2, UploadCloud } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { postIngest } from "@/lib/api";
import type { IngestResponse } from "@/lib/types";

export function IngestDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IngestResponse | null>(null);

  async function handleUpload() {
    if (!file) return;
    setStatus("loading");
    setError(null);
    try {
      const res = await postIngest(file);
      setResult(res);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  function reset() {
    setFile(null);
    setResult(null);
    setError(null);
    setStatus("idle");
  }

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
          <DialogTitle>Upload a document</DialogTitle>
          <DialogDescription>
            PDF or plain text. It&apos;s chunked, embedded, and indexed into
            the vector store so questions can be answered against it.
          </DialogDescription>
        </DialogHeader>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-border/60 bg-obsidian/40 px-6 py-8 text-center transition-colors hover:border-cobalt/50"
        >
          <UploadCloud className="size-6 text-muted-foreground" />
          <span className="text-sm text-ivory">
            {file ? file.name : "Click to choose a file"}
          </span>
          <span className="text-xs text-muted-foreground">.pdf or .txt</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,text/plain,application/pdf"
          className="hidden"
          onChange={(e) => {
            setResult(null);
            setError(null);
            setFile(e.target.files?.[0] ?? null);
          }}
        />

        {error && <p className="text-sm text-status-bad">{error}</p>}
        {result && (
          <div className="rounded-lg border border-status-good/30 bg-status-good-dim px-3 py-2 font-mono text-xs text-status-good">
            Ingested &quot;{result.source_title}&quot; — {result.num_chunks}{" "}
            chunks (doc_id {result.doc_id.slice(0, 8)}…)
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || status === "loading"}
          >
            {status === "loading" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              "Ingest"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
