"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertTriangle,
  FileText,
  KeyRound,
  Loader2,
  Printer,
  RotateCcw,
  ShieldCheck,
  LayoutDashboard,
} from "lucide-react";
import { toast } from "sonner";
import { checkDuplicates, generateAnswerKey } from "@/lib/api";
import { formatDuration } from "@/lib/utils";
import type { AnswerKey, DedupResponse, Paper } from "@/lib/types";

interface ExportStepProps {
  sessionId: string;
  paper: Paper;
  board: string;
  level: string;
  onBack: () => void;
  onStartOver: () => void;
}

const SEVERITY_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  low: "bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
};

export function ExportStep({ sessionId, paper, board, level, onBack, onStartOver }: ExportStepProps) {
  const [printing, setPrinting] = useState(false);
  const [answerKey, setAnswerKey] = useState<AnswerKey | null>(null);
  const [generatingKey, setGeneratingKey] = useState(false);
  const [dedup, setDedup] = useState<DedupResponse | null>(null);
  const [checkingDedup, setCheckingDedup] = useState(false);

  const handlePrint = () => {
    setPrinting(true);
    toast.info("Use “Save as PDF” in the print dialog to download.");
    setTimeout(() => {
      window.print();
      setPrinting(false);
    }, 300);
  };

  const handleAnswerKey = async () => {
    setGeneratingKey(true);
    try {
      const key = await generateAnswerKey(sessionId, paper);
      setAnswerKey(key);
      toast.success("Answer key generated.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Answer key generation failed.");
    } finally {
      setGeneratingKey(false);
    }
  };

  const handleDedup = async () => {
    setCheckingDedup(true);
    try {
      const result = await checkDuplicates(sessionId, paper);
      setDedup(result);
      if (result.warnings.length === 0) {
        toast.success("No overlap with the source papers found.");
      } else {
        toast.warning(`${result.warnings.length} question(s) overlap with source papers.`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Originality check failed.");
    } finally {
      setCheckingDedup(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">PDF Export</h2>
          <p className="text-muted-foreground text-sm mt-1">
            Preview your generated paper below and download or print.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onBack} className="shrink-0">
          ← Back
        </Button>
      </div>

      {/* Action bar */}
      <div className="flex flex-wrap gap-2 p-4 rounded-xl border bg-muted/40 print:hidden">
        <Button className="flex-1 sm:flex-none h-9 text-sm" onClick={handlePrint} disabled={printing}>
          {printing ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Printer className="w-4 h-4 mr-2" />
          )}
          Print / Save PDF
        </Button>
        <Button
          variant="outline"
          className="flex-1 sm:flex-none h-9 text-sm"
          onClick={handleAnswerKey}
          disabled={generatingKey}
        >
          {generatingKey ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <KeyRound className="w-4 h-4 mr-2" />
          )}
          {answerKey ? "Regenerate Answer Key" : "Generate Answer Key"}
        </Button>
        <Button
          variant="outline"
          className="flex-1 sm:flex-none h-9 text-sm"
          onClick={handleDedup}
          disabled={checkingDedup}
        >
          {checkingDedup ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <ShieldCheck className="w-4 h-4 mr-2" />
          )}
          Check Originality
        </Button>
        <div className="flex-1 sm:flex-none sm:ml-auto flex gap-2">
          <Link href="/">
            <Button variant="outline" className="h-9 text-sm gap-1.5">
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </Button>
          </Link>
          <Button variant="ghost" className="h-9 text-sm text-muted-foreground" onClick={onStartOver}>
            <RotateCcw className="w-4 h-4 mr-2" />
            New Paper
          </Button>
        </div>
      </div>

      {/* Dedup warnings */}
      {dedup && dedup.warnings.length > 0 && (
        <Card className="border-amber-300/60 print:hidden">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Originality warnings ({dedup.warnings.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pb-4">
            {dedup.warnings.map((w) => (
              <div key={w.question_id} className="flex items-start gap-3 text-xs">
                <span className={`px-2 py-0.5 rounded-full font-semibold shrink-0 ${SEVERITY_STYLES[w.severity] ?? SEVERITY_STYLES.low}`}>
                  {w.severity} · {(w.similarity * 100).toFixed(0)}%
                </span>
                <p className="text-muted-foreground">
                  <span className="font-semibold text-foreground">{w.question_id}</span> resembles:
                  {" "}“{w.matched_source_snippet}”
                </p>
              </div>
            ))}
            <p className="text-[11px] text-muted-foreground pt-1">
              Regenerate flagged questions in the previous step to improve originality.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Paper preview */}
      <div
        id="paper-preview"
        className="border rounded-xl bg-white dark:bg-card shadow-sm overflow-hidden"
      >
        {/* Paper header */}
        <div className="border-b p-8 pb-6 space-y-3 bg-white dark:bg-card print:p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              {board && <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">{board}</p>}
              <h1 className="text-2xl font-bold text-foreground">{paper.title}</h1>
              {level && <Badge variant="secondary" className="text-xs">{level}</Badge>}
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <Separator />
          <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
            <span><span className="font-medium text-foreground">Duration:</span> {formatDuration(paper.duration_minutes)}</span>
            <span><span className="font-medium text-foreground">Total Marks:</span> {paper.total_marks}</span>
          </div>
          {paper.instructions.length > 0 && (
            <ul className="text-xs text-muted-foreground italic border-t pt-3 space-y-0.5 list-disc list-inside">
              {paper.instructions.map((inst, i) => (
                <li key={i}>{inst}</li>
              ))}
            </ul>
          )}
        </div>

        {/* Sections */}
        <div className="p-8 pt-6 space-y-8 print:p-6">
          {paper.sections.map((section) => (
            <div key={section.id} className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-base font-bold">{section.title} ({section.marks} marks)</h2>
                <p className="text-xs text-muted-foreground italic">{section.instructions}</p>
              </div>
              <Separator />
              <div className="space-y-5">
                {section.questions.map((q) => (
                  <div key={q.id} className="space-y-2">
                    {q.context_passage && (
                      <p className="ml-8 text-sm italic text-muted-foreground border rounded p-3 whitespace-pre-line">
                        {q.context_passage}
                      </p>
                    )}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <span className="font-bold text-sm shrink-0 w-6">{q.number}.</span>
                        <p className="text-sm leading-relaxed whitespace-pre-line">{q.prompt}</p>
                      </div>
                      <Badge variant="outline" className="text-xs shrink-0 self-start">{q.marks}m</Badge>
                    </div>
                    {q.sub_parts.length > 0 && (
                      <div className="ml-9 space-y-3 mt-2">
                        {q.sub_parts.map((sp) => (
                          <div key={sp.label} className="flex items-start gap-3">
                            <span className="text-sm font-semibold shrink-0 w-7">{sp.label}</span>
                            <div className="flex-1 space-y-1">
                              <p className="text-sm leading-relaxed whitespace-pre-line">{sp.prompt}</p>
                              <div className="h-8 border-b border-dashed border-border/60" />
                            </div>
                            <Badge variant="outline" className="text-xs shrink-0">{sp.marks}m</Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="text-center text-xs text-muted-foreground pt-4 border-t">
            — END OF PAPER —
          </div>
        </div>
      </div>

      {/* Answer key */}
      {answerKey && (
        <div className="border rounded-xl bg-white dark:bg-card shadow-sm overflow-hidden">
          <div className="border-b p-6 space-y-1">
            <div className="flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-muted-foreground" />
              <h2 className="text-lg font-bold">Answer Key & Marking Scheme</h2>
            </div>
            <p className="text-xs text-muted-foreground">
              {answerKey.paper_title} · {answerKey.total_marks} marks
            </p>
          </div>
          <div className="p-6 space-y-6">
            {answerKey.sections.map((section) => (
              <div key={section.section_id} className="space-y-3">
                <h3 className="text-sm font-bold uppercase tracking-wide">{section.section_title}</h3>
                <div className="space-y-4">
                  {section.answers.map((ans) => (
                    <div key={ans.question_id} className="rounded-lg border p-4 space-y-2">
                      <p className="text-xs font-semibold text-muted-foreground uppercase">{ans.question_id}</p>
                      <p className="text-sm leading-relaxed whitespace-pre-line">{ans.model_answer}</p>
                      {ans.sub_part_answers.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          {ans.sub_part_answers.map((spa) => (
                            <div key={spa.label} className="flex items-start gap-2 text-sm">
                              <span className="font-semibold shrink-0">{spa.label}</span>
                              <p className="flex-1 whitespace-pre-line">{spa.model_answer}</p>
                              <span className="text-xs text-muted-foreground shrink-0">[{spa.marks}]</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {ans.marking_criteria.length > 0 && (
                        <div className="pt-1">
                          <p className="text-xs font-semibold text-muted-foreground mb-1">Marking criteria</p>
                          <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                            {ans.marking_criteria.map((c, i) => (
                              <li key={i}>{c}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {ans.common_mistakes.length > 0 && (
                        <div className="pt-1">
                          <p className="text-xs font-semibold text-amber-600 dark:text-amber-400 mb-1">Common mistakes</p>
                          <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                            {ans.common_mistakes.map((m, i) => (
                              <li key={i}>{m}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Card className="bg-muted/30 print:hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Export notes</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground space-y-1 pb-4">
          <p>• Download uses browser print-to-PDF for clean A4 formatting.</p>
          <p>• The answer key is generated from your edited paper, not the original draft.</p>
          <p>• “Check Originality” compares every question against the uploaded source PDFs.</p>
        </CardContent>
      </Card>
    </div>
  );
}
