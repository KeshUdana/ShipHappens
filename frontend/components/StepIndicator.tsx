"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

const steps = [
  { id: 1, label: "Upload" },
  { id: 2, label: "Blueprint Review" },
  { id: 3, label: "Editable Paper" },
  { id: 4, label: "PDF Export" },
];

interface StepIndicatorProps {
  currentStep: number;
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-center w-full">
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <div className="flex flex-col items-center gap-1.5">
            <div
              className={cn(
                "w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-all duration-300",
                currentStep > step.id
                  ? "bg-primary border-primary text-primary-foreground"
                  : currentStep === step.id
                  ? "bg-primary border-primary text-primary-foreground shadow-md shadow-primary/30 scale-110"
                  : "bg-muted border-border text-muted-foreground"
              )}
            >
              {currentStep > step.id ? (
                <Check className="w-4 h-4" />
              ) : (
                step.id
              )}
            </div>
            <span
              className={cn(
                "text-xs font-medium whitespace-nowrap transition-colors duration-300",
                currentStep >= step.id
                  ? "text-foreground"
                  : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={cn(
                "h-0.5 w-16 sm:w-24 mx-2 mb-5 transition-all duration-500",
                currentStep > step.id ? "bg-primary" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}
