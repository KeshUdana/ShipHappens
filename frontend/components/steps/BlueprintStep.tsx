"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { streamGeneratePaper } from "@/lib/api";
import { formatDuration } from "@/lib/utils";
import type { Blueprint, Paper } from "@/lib/types";

interface BlueprintStepProps {
  sessionId: string;
  blueprint: Blueprint;
  paperTitle: string;
  onNext: (paper: Paper) => void;
  onBack: () => void;
}

const TYPE_COLORS = [
  "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  "bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
];

export function BlueprintStep({ sessionId, blueprint, paperTitle, onNext, onBack }: BlueprintStepProps) {
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("");

  const sectionCount = blueprint.sections.length;

  const handleGenerate = async () => {
    setGenerating(true);
    setProgress(3);
    setStatusText("Contacting the generator…");
    try {
      const paper = await streamGeneratePaper(sessionId, blueprint, (event) => {
        switch (event.event) {
          case "start":
            setProgress(8);
            setStatusText(`Generating with ${event.model}…`);
            break;
          case "section":
            setStatusText(`Writing ${event.title}…`);
            break;
          case "chunk":
            // Sections drive the bar; chunks nudge it within the current section.
            setProgress((prev) =>
              Math.min(95, Math.max(prev + 1, 10 + (event.sections_seen / sectionCount) * 80))
            );
            break;
          case "warning":
            toast.warning(event.message);
            break;
          case "complete":
            setProgress(100);
            setStatusText("Paper ready!");
            break;
        }
      });
      toast.success("Paper generated!");
      onNext(paper);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Generation failed.");
      setGenerating(false);
      setProgress(0);
      setStatusText("");
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Blueprint Review</h2>
          <p className="text-muted-foreground text-sm mt-1">
            AI extracted the following structure from your uploaded papers. Review before generating.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onBack} className="shrink-0" disabled={generating}>
          ← Back
        </Button>
      </div>

      {/* Paper meta */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Paper</p>
              <p className="font-semibold truncate">{paperTitle || blueprint.subject || "Untitled Paper"}</p>
            </div>
            <Separator orientation="vertical" className="h-8" />
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Duration</p>
              <p className="font-semibold">{formatDuration(blueprint.duration_minutes)}</p>
            </div>
            <Separator orientation="vertical" className="h-8" />
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Total Marks</p>
              <p className="font-semibold">{blueprint.total_marks}</p>
            </div>
            <Separator orientation="vertical" className="h-8" />
            <div className="flex gap-2 flex-wrap">
              <Badge variant="secondary">{blueprint.board}</Badge>
              <Badge variant="secondary">{blueprint.level}</Badge>
              <Badge variant="secondary">{blueprint.subject}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tone notes */}
      <div className="flex gap-3 p-4 rounded-lg bg-muted/60 border">
        <BookOpen className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
        <p className="text-sm text-muted-foreground leading-relaxed">{blueprint.tone_notes}</p>
      </div>

      {/* Cover-page instructions */}
      {blueprint.instructions_pattern.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Cover-Page Instructions
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-4 space-y-1.5">
            {blueprint.instructions_pattern.map((inst, i) => (
              <div key={i} className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                <p className="text-xs text-muted-foreground">{inst}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Sections */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Sections ({sectionCount})
        </h3>
        {blueprint.sections.map((section) => (
          <Card key={section.id} className="overflow-hidden">
            <CardHeader className="pb-3 pt-4 px-5">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-base">{section.title}</CardTitle>
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-muted text-muted-foreground shrink-0">
                  {section.marks} marks
                </span>
              </div>
            </CardHeader>
            <CardContent className="px-5 pb-4 space-y-3">
              <div className="flex gap-1.5 flex-wrap">
                {section.question_types.map((t, i) => (
                  <span
                    key={t}
                    className={`text-xs font-semibold px-2.5 py-1 rounded-full ${TYPE_COLORS[i % TYPE_COLORS.length]}`}
                  >
                    {t}
                  </span>
                ))}
              </div>
              <div className="space-y-1">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground">{section.instructions}</p>
                </div>
                <div className="flex items-start gap-2">
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground italic">{section.typical_prompt_style}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Mark distribution */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Mark Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pb-4">
          {blueprint.sections.map((section) => {
            const pct = blueprint.total_marks > 0
              ? Math.round((section.marks / blueprint.total_marks) * 100)
              : 0;
            return (
              <div key={section.id} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium">{section.title}</span>
                  <span className="text-muted-foreground">{section.marks} marks · {pct}%</span>
                </div>
                <Progress value={pct} className="h-1.5" />
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Generation progress */}
      {generating && (
        <div className="space-y-2 p-4 rounded-lg border bg-muted/40">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <p className="text-sm font-medium">{statusText}</p>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      )}

      <Button
        className="w-full h-11 text-sm font-semibold"
        onClick={handleGenerate}
        disabled={generating}
      >
        {generating ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Generating Paper…
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 mr-2" />
            Generate New Paper
          </>
        )}
      </Button>

      <div className="flex items-center gap-2 justify-center pb-2">
        <RefreshCw className="w-3.5 h-3.5 text-muted-foreground" />
        <p className="text-xs text-muted-foreground">
          You can regenerate individual questions after generation.
        </p>
      </div>
    </div>
  );
}
