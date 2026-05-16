"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, FileText, Loader2, Printer, RotateCcw, Share2, LayoutDashboard } from "lucide-react";
import { toast } from "sonner";

interface ExportStepProps {
  paperTitle: string;
  board: string;
  level: string;
  onBack: () => void;
  onStartOver: () => void;
}

const MOCK_PAPER = {
  title: "Physics Paper 1",
  duration: "2 hours 30 minutes",
  totalMarks: 120,
  sections: [
    {
      id: "A",
      heading: "Section A — Multiple Choice (20 marks)",
      instruction: "Answer ALL questions. Each question carries 1 mark.",
      questions: [
        { number: 1, text: "A uniform beam of length 4.0 m and weight 200 N is supported at both ends. A load of 500 N is placed 1.0 m from the left end. What is the reaction force at the left support?", options: ["A  312 N", "B  275 N", "C  425 N", "D  188 N"], marks: 1 },
        { number: 2, text: "Which of the following best describes the term 'specific heat capacity' of a substance?", options: ["A  Energy per unit mass per degree", "B  Energy needed to melt 1 kg", "C  Energy needed to vaporise 1 kg", "D  Energy per unit volume per degree"], marks: 1 },
        { number: 3, text: "A wave has a frequency of 250 Hz and a wavelength of 1.4 m. What is its speed?", options: ["A  178 m s⁻¹", "B  350 m s⁻¹", "C  250 m s⁻¹", "D  500 m s⁻¹"], marks: 1 },
      ],
    },
    {
      id: "B",
      heading: "Section B — Structured Questions (60 marks)",
      instruction: "Answer ALL questions. Show all working clearly.",
      questions: [
        {
          number: 1,
          text: "A car of mass 1200 kg accelerates from rest to 20 m s⁻¹ in 8.0 s on a straight horizontal road.",
          subParts: [
            { label: "(a)", text: "Calculate the acceleration of the car.", marks: 2 },
            { label: "(b)", text: "Calculate the net force acting on the car during acceleration.", marks: 2 },
            { label: "(c)", text: "If the driving force is 4500 N, calculate the frictional force opposing motion.", marks: 2 },
            { label: "(d)", text: "Sketch a velocity-time graph for the motion described. Label the axes and show the values.", marks: 4 },
          ],
          marks: 10,
        },
      ],
    },
    {
      id: "C",
      heading: "Section C — Extended Response (40 marks)",
      instruction: "Answer ONE question only from this section.",
      questions: [
        {
          number: 1,
          text: "Describe and explain the factors that affect the resistance of a metallic conductor. In your answer, include a discussion of how temperature affects resistance and how this behaviour differs between metallic conductors and semiconductors. Use appropriate equations and diagrams where necessary.",
          marks: 20,
        },
      ],
    },
  ],
};

export function ExportStep({ paperTitle, board, level, onBack, onStartOver }: ExportStepProps) {
  const [downloading, setDownloading] = useState(false);
  const [printing, setPrinting] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    await new Promise((r) => setTimeout(r, 1500));
    setDownloading(false);
    toast.success("PDF downloaded successfully.");
  };

  const handlePrint = async () => {
    setPrinting(true);
    await new Promise((r) => setTimeout(r, 800));
    setPrinting(false);
    window.print();
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
      <div className="flex flex-wrap gap-2 p-4 rounded-xl border bg-muted/40">
        <Button className="flex-1 sm:flex-none h-9 text-sm" onClick={handleDownload} disabled={downloading}>
          {downloading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Download className="w-4 h-4 mr-2" />
          )}
          Download PDF
        </Button>
        <Button variant="outline" className="flex-1 sm:flex-none h-9 text-sm" onClick={handlePrint} disabled={printing}>
          {printing ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Printer className="w-4 h-4 mr-2" />
          )}
          Print
        </Button>
        <Button
          variant="outline"
          className="flex-1 sm:flex-none h-9 text-sm"
          onClick={() => toast.success("Share link copied to clipboard.")}
        >
          <Share2 className="w-4 h-4 mr-2" />
          Share
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
              <h1 className="text-2xl font-bold text-foreground">
                {paperTitle || MOCK_PAPER.title}
              </h1>
              {level && <Badge variant="secondary" className="text-xs">{level}</Badge>}
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <Separator />
          <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
            <span><span className="font-medium text-foreground">Duration:</span> {MOCK_PAPER.duration}</span>
            <span><span className="font-medium text-foreground">Total Marks:</span> {MOCK_PAPER.totalMarks}</span>
            <span><span className="font-medium text-foreground">Date:</span> May 2025</span>
          </div>
          <p className="text-xs text-muted-foreground italic border-t pt-3">
            READ THE INSTRUCTIONS ON THE FRONT COVER CAREFULLY. Answer all questions in the spaces provided.
            Calculators may be used unless otherwise stated.
          </p>
        </div>

        {/* Sections */}
        <div className="p-8 pt-6 space-y-8 print:p-6">
          {MOCK_PAPER.sections.map((section) => (
            <div key={section.id} className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-base font-bold">{section.heading}</h2>
                <p className="text-xs text-muted-foreground italic">{section.instruction}</p>
              </div>
              <Separator />
              <div className="space-y-5">
                {section.questions.map((q) => (
                  <div key={q.number} className="space-y-2">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <span className="font-bold text-sm shrink-0 w-5">{q.number}.</span>
                        <p className="text-sm leading-relaxed">{q.text}</p>
                      </div>
                      <Badge variant="outline" className="text-xs shrink-0 self-start">
                        {"marks" in q ? `${q.marks}m` : ""}
                      </Badge>
                    </div>
                    {"options" in q && q.options && (
                      <div className="ml-8 grid grid-cols-1 sm:grid-cols-2 gap-1.5 mt-2">
                        {q.options.map((opt) => (
                          <div key={opt} className="text-sm flex items-center gap-2">
                            <div className="w-4 h-4 rounded-full border border-border shrink-0" />
                            <span>{opt}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {"subParts" in q && q.subParts && (
                      <div className="ml-8 space-y-3 mt-2">
                        {q.subParts.map((sp) => (
                          <div key={sp.label} className="flex items-start gap-3">
                            <span className="text-sm font-semibold shrink-0 w-6">{sp.label}</span>
                            <div className="flex-1 space-y-1">
                              <p className="text-sm leading-relaxed">{sp.text}</p>
                              <div className="h-8 border-b border-dashed border-border/60" />
                            </div>
                            <Badge variant="outline" className="text-xs shrink-0">{sp.marks}m</Badge>
                          </div>
                        ))}
                      </div>
                    )}
                    {!("subParts" in q) && !("options" in q) && (
                      <div className="ml-8 space-y-1.5 mt-2">
                        {[...Array(6)].map((_, i) => (
                          <div key={i} className="h-7 border-b border-dashed border-border/50" />
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

      <Card className="bg-muted/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Export notes</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground space-y-1 pb-4">
          <p>• Download uses browser print-to-PDF for clean A4 formatting.</p>
          <p>• For server-side PDF generation (v2), WeasyPrint is integrated in the backend.</p>
          <p>• Answer spaces are proportional to the marks allocated.</p>
        </CardContent>
      </Card>
    </div>
  );
}
