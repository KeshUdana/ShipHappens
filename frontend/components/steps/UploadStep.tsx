"use client";

import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  Upload,
  FileText,
  X,
  ChevronDown,
  Loader2,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

interface UploadedFile {
  name: string;
  size: number;
  id: string;
}

interface UploadStepProps {
  onNext: (data: {
    files: UploadedFile[];
    title: string;
    board: string;
    level: string;
  }) => void;
}

const BOARDS = ["Cambridge (CAIE)", "Edexcel", "AQA", "OCR", "IB Diploma", "Local (Sri Lanka)"];
const LEVELS = ["O/L (Ordinary Level)", "A/L (Advanced Level)", "IGCSE", "AS Level", "A2 Level", "Grade 9–11"];

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadStep({ onNext }: UploadStepProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const [title, setTitle] = useState("");
  const [board, setBoard] = useState("");
  const [level, setLevel] = useState("");
  const [analyzing, setAnalyzing] = useState(false);

  const handleFiles = useCallback((incoming: FileList | null) => {
    if (!incoming) return;
    const valid = Array.from(incoming).filter((f) => f.type === "application/pdf");
    if (valid.length !== incoming.length) {
      toast.error("Only PDF files are accepted.");
    }
    setFiles((prev) => {
      const combined = [
        ...prev,
        ...valid.map((f) => ({ name: f.name, size: f.size, id: crypto.randomUUID() })),
      ];
      if (combined.length > 5) {
        toast.warning("Maximum 5 files allowed. Extra files were ignored.");
        return combined.slice(0, 5);
      }
      return combined;
    });
  }, []);

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleAnalyze = async () => {
    if (files.length < 1) {
      toast.error("Please upload at least one PDF.");
      return;
    }
    setAnalyzing(true);
    await new Promise((r) => setTimeout(r, 2200));
    setAnalyzing(false);
    onNext({ files, title, board, level });
  };

  return (
    <div className="max-w-2xl mx-auto w-full space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-2xl font-bold tracking-tight">Upload Past Papers</h2>
        <p className="text-muted-foreground text-sm">
          Upload 1–5 past exam PDFs. Our AI will extract the structure and generate a new paper.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-input")?.click()}
        className={cn(
          "relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all duration-200 group",
          dragging
            ? "border-primary bg-primary/5 scale-[1.01]"
            : "border-border hover:border-primary/60 hover:bg-muted/40"
        )}
      >
        <input
          id="file-input"
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="flex flex-col items-center gap-3 pointer-events-none">
          <div className={cn(
            "w-14 h-14 rounded-full flex items-center justify-center transition-colors",
            dragging ? "bg-primary/10" : "bg-muted group-hover:bg-primary/10"
          )}>
            <Upload className={cn("w-6 h-6 transition-colors", dragging ? "text-primary" : "text-muted-foreground group-hover:text-primary")} />
          </div>
          <div>
            <p className="font-semibold text-sm">
              {dragging ? "Drop your PDFs here" : "Drag & drop PDFs here"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">or click to browse · max 5 files</p>
          </div>
        </div>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted-foreground">{files.length}/5 files</p>
            <Button variant="ghost" size="sm" className="text-xs text-muted-foreground h-auto py-0.5" onClick={() => setFiles([])}>
              Clear all
            </Button>
          </div>
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg border bg-card"
              >
                <div className="w-8 h-8 rounded-md bg-red-50 dark:bg-red-950 flex items-center justify-center shrink-0">
                  <FileText className="w-4 h-4 text-red-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="w-7 h-7 shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={() => removeFile(file.id)}
                >
                  <X className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Optional metadata */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Paper Details <span className="font-normal text-muted-foreground text-sm">(optional)</span></CardTitle>
          <CardDescription>Provide context to help the AI generate a more accurate paper.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="title">Paper Title</Label>
            <Input
              id="title"
              placeholder="e.g. Physics Paper 1 2025"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Exam Board</Label>
              <DropdownMenu>
                <DropdownMenuTrigger className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring">
                  <span className={board ? "text-foreground" : "text-muted-foreground"}>{board || "Select board"}</span>
                  <ChevronDown className="w-4 h-4 opacity-50" />
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-48">
                  {BOARDS.map((b) => (
                    <DropdownMenuItem key={b} onClick={() => setBoard(b)}>{b}</DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div className="space-y-1.5">
              <Label>Level</Label>
              <DropdownMenu>
                <DropdownMenuTrigger className="flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring">
                  <span className={level ? "text-foreground" : "text-muted-foreground"}>{level || "Select level"}</span>
                  <ChevronDown className="w-4 h-4 opacity-50" />
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-48">
                  {LEVELS.map((l) => (
                    <DropdownMenuItem key={l} onClick={() => setLevel(l)}>{l}</DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          {(board || level) && (
            <div className="flex gap-2 flex-wrap">
              {board && <Badge variant="secondary">{board}</Badge>}
              {level && <Badge variant="secondary">{level}</Badge>}
            </div>
          )}
        </CardContent>
      </Card>

      <Button
        className="w-full h-11 text-sm font-semibold"
        onClick={handleAnalyze}
        disabled={files.length === 0 || analyzing}
      >
        {analyzing ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Analyzing papers…
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 mr-2" />
            Analyze & Generate Blueprint
          </>
        )}
      </Button>
    </div>
  );
}
