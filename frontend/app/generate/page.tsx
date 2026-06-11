"use client";

import { useState } from "react";
import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StepIndicator } from "@/components/StepIndicator";
import { UploadStep } from "@/components/steps/UploadStep";
import { BlueprintStep } from "@/components/steps/BlueprintStep";
import { EditableStep } from "@/components/steps/EditableStep";
import { ExportStep } from "@/components/steps/ExportStep";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import type { Blueprint, Paper } from "@/lib/types";

export interface PaperMeta {
  title: string;
  board: string;
  level: string;
}

export default function GeneratePage() {
  const [step, setStep] = useState(1);
  const [meta, setMeta] = useState<PaperMeta>({ title: "", board: "", level: "" });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [paper, setPaper] = useState<Paper | null>(null);

  const handleUploadNext = (data: { sessionId: string; blueprint: Blueprint; meta: PaperMeta }) => {
    setSessionId(data.sessionId);
    setBlueprint(data.blueprint);
    setMeta(data.meta);
    setStep(2);
  };

  const handleBlueprintNext = (generated: Paper) => {
    setPaper(generated);
    setStep(3);
  };

  const handleStartOver = () => {
    setStep(1);
    setMeta({ title: "", board: "", level: "" });
    setSessionId(null);
    setBlueprint(null);
    setPaper(null);
  };

  return (
    <DashboardLayout
      title="Generate Paper"
      subtitle="AI-powered exam paper generator"
    >
      <div className="max-w-4xl space-y-6">
        {/* Back to dashboard */}
        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground h-8 text-xs">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Dashboard
            </Button>
          </Link>
        </div>

        {/* Step indicator */}
        <div className="bg-card border border-border rounded-xl px-6 py-5">
          <StepIndicator currentStep={step} />
        </div>

        {/* Step content */}
        <div>
          {step === 1 && <UploadStep onNext={handleUploadNext} />}
          {step === 2 && sessionId && blueprint && (
            <BlueprintStep
              sessionId={sessionId}
              blueprint={blueprint}
              paperTitle={meta.title}
              onNext={handleBlueprintNext}
              onBack={() => setStep(1)}
            />
          )}
          {step === 3 && sessionId && blueprint && paper && (
            <EditableStep
              sessionId={sessionId}
              blueprint={blueprint}
              paper={paper}
              onPaperChange={setPaper}
              onNext={() => setStep(4)}
              onBack={() => setStep(2)}
            />
          )}
          {step === 4 && sessionId && paper && (
            <ExportStep
              sessionId={sessionId}
              paper={paper}
              board={meta.board}
              level={meta.level}
              onBack={() => setStep(3)}
              onStartOver={handleStartOver}
            />
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
