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

interface UploadData {
  files: { name: string; size: number; id: string }[];
  title: string;
  board: string;
  level: string;
}

export default function GeneratePage() {
  const [step, setStep] = useState(1);
  const [uploadData, setUploadData] = useState<UploadData>({
    files: [],
    title: "",
    board: "",
    level: "",
  });

  const handleUploadNext = (data: UploadData) => {
    setUploadData(data);
    setStep(2);
  };

  const handleStartOver = () => {
    setStep(1);
    setUploadData({ files: [], title: "", board: "", level: "" });
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
          {step === 2 && (
            <BlueprintStep
              paperTitle={uploadData.title}
              board={uploadData.board}
              level={uploadData.level}
              onNext={() => setStep(3)}
              onBack={() => setStep(1)}
            />
          )}
          {step === 3 && (
            <EditableStep
              onNext={() => setStep(4)}
              onBack={() => setStep(2)}
            />
          )}
          {step === 4 && (
            <ExportStep
              paperTitle={uploadData.title}
              board={uploadData.board}
              level={uploadData.level}
              onBack={() => setStep(3)}
              onStartOver={handleStartOver}
            />
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
