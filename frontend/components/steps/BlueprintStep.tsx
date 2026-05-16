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

interface BlueprintStepProps {
  paperTitle: string;
  board: string;
  level: string;
  onNext: () => void;
  onBack: () => void;
}

const MOCK_BLUEPRINT = {
  sections: [
    {
      id: "A",
      title: "Section A – Multiple Choice",
      questionType: "MCQ",
      questionCount: 20,
      marksPerQuestion: 1,
      totalMarks: 20,
      instructions: "Answer ALL questions. Each question carries 1 mark. No negative marking.",
      styleNotes: "Single best answer from 4 options (A–D). Topics cover units 1–4.",
    },
    {
      id: "B",
      title: "Section B – Structured Questions",
      questionType: "Structured",
      questionCount: 6,
      marksPerQuestion: 10,
      totalMarks: 60,
      instructions: "Answer ALL questions. Show all working clearly.",
      styleNotes: "Multi-part questions with sub-parts (a), (b), (c). Diagrams expected where relevant.",
    },
    {
      id: "C",
      title: "Section C – Essay / Extended Response",
      questionType: "Essay",
      questionCount: 2,
      marksPerQuestion: 20,
      totalMarks: 40,
      instructions: "Answer ONE question only from this section.",
      styleNotes: "Extended prose answers. Mark scheme follows AO1/AO2/AO3 criteria.",
    },
  ],
  totalMarks: 120,
  duration: "2 hours 30 minutes",
  rubric: "This paper consists of three sections. Read all instructions carefully before starting.",
  topicDistribution: [
    { topic: "Mechanics", percentage: 28 },
    { topic: "Waves & Optics", percentage: 22 },
    { topic: "Electricity", percentage: 20 },
    { topic: "Thermodynamics", percentage: 18 },
    { topic: "Modern Physics", percentage: 12 },
  ],
};

const QUESTION_TYPE_COLORS: Record<string, string> = {
  MCQ: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  Structured: "bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  Essay: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
};

export function BlueprintStep({ paperTitle, board, level, onNext, onBack }: BlueprintStepProps) {
  const [generating, setGenerating] = useState(false);

  const handleGenerate = async () => {
    setGenerating(true);
    toast.promise(
      new Promise((r) => setTimeout(r, 2500)),
      {
        loading: "Generating new paper…",
        success: "Paper generated!",
        error: "Something went wrong.",
      }
    );
    await new Promise((r) => setTimeout(r, 2500));
    setGenerating(false);
    onNext();
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
        <Button variant="ghost" size="sm" onClick={onBack} className="shrink-0">
          ← Back
        </Button>
      </div>

      {/* Paper meta */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Paper</p>
              <p className="font-semibold truncate">{paperTitle || "Untitled Paper"}</p>
            </div>
            <Separator orientation="vertical" className="h-8" />
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Duration</p>
              <p className="font-semibold">{MOCK_BLUEPRINT.duration}</p>
            </div>
            <Separator orientation="vertical" className="h-8" />
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">Total Marks</p>
              <p className="font-semibold">{MOCK_BLUEPRINT.totalMarks}</p>
            </div>
            {board && (
              <>
                <Separator orientation="vertical" className="h-8" />
                <div className="flex gap-2 flex-wrap">
                  <Badge variant="secondary">{board}</Badge>
                  {level && <Badge variant="secondary">{level}</Badge>}
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Rubric */}
      <div className="flex gap-3 p-4 rounded-lg bg-muted/60 border">
        <BookOpen className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
        <p className="text-sm text-muted-foreground leading-relaxed">{MOCK_BLUEPRINT.rubric}</p>
      </div>

      {/* Sections */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
          Sections ({MOCK_BLUEPRINT.sections.length})
        </h3>
        {MOCK_BLUEPRINT.sections.map((section) => (
          <Card key={section.id} className="overflow-hidden">
            <CardHeader className="pb-3 pt-4 px-5">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-base">{section.title}</CardTitle>
                <span
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                    QUESTION_TYPE_COLORS[section.questionType]
                  }`}
                >
                  {section.questionType}
                </span>
              </div>
            </CardHeader>
            <CardContent className="px-5 pb-4 space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-2.5 rounded-lg bg-muted/60">
                  <p className="text-xs text-muted-foreground">Questions</p>
                  <p className="text-xl font-bold mt-0.5">{section.questionCount}</p>
                </div>
                <div className="text-center p-2.5 rounded-lg bg-muted/60">
                  <p className="text-xs text-muted-foreground">Marks/Q</p>
                  <p className="text-xl font-bold mt-0.5">{section.marksPerQuestion}</p>
                </div>
                <div className="text-center p-2.5 rounded-lg bg-muted/60">
                  <p className="text-xs text-muted-foreground">Total</p>
                  <p className="text-xl font-bold mt-0.5">{section.totalMarks}</p>
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground">{section.instructions}</p>
                </div>
                <div className="flex items-start gap-2">
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground italic">{section.styleNotes}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Topic distribution */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            Topic Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pb-4">
          {MOCK_BLUEPRINT.topicDistribution.map((t) => (
            <div key={t.topic} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="font-medium">{t.topic}</span>
                <span className="text-muted-foreground">{t.percentage}%</span>
              </div>
              <Progress value={t.percentage} className="h-1.5" />
            </div>
          ))}
        </CardContent>
      </Card>

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
