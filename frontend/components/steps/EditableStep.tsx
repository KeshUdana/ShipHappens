"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { cn, formatDuration } from "@/lib/utils";
import {
  FileDown,
  Loader2,
  Pencil,
  RefreshCw,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { regenerateQuestion, regenerateSection } from "@/lib/api";
import type { Blueprint, Paper, Question, SectionPaper, SubPart } from "@/lib/types";

interface EditableStepProps {
  sessionId: string;
  blueprint: Blueprint;
  paper: Paper;
  onPaperChange: (paper: Paper) => void;
  onNext: () => void;
  onBack: () => void;
}

function replaceQuestion(paper: Paper, sectionId: string, fresh: Question): Paper {
  return {
    ...paper,
    sections: paper.sections.map((s) =>
      s.id !== sectionId
        ? s
        : { ...s, questions: s.questions.map((q) => (q.id === fresh.id ? fresh : q)) }
    ),
  };
}

function replaceSection(paper: Paper, fresh: SectionPaper): Paper {
  return {
    ...paper,
    sections: paper.sections.map((s) => (s.id === fresh.id ? fresh : s)),
  };
}

function isMcqLike(type: string) {
  const t = type.toLowerCase();
  return t.includes("mcq") || t.includes("multiple");
}

function answerLinesForMarks(marks: number, type: string) {
  const t = type.toLowerCase();
  if (t.includes("essay") || t.includes("extended")) return 14;
  if (marks >= 6) return 8;
  if (marks >= 4) return 6;
  if (marks >= 3) return 4;
  if (marks >= 2) return 3;
  return 2;
}

function AnswerLines({ count }: { count: number }) {
  return (
    <div className="mt-3 space-y-[10px]">
      {[...Array(count)].map((_, i) => (
        <div key={i} className="border-b border-gray-300 h-[1px] w-full" />
      ))}
    </div>
  );
}

function MarksBox({ marks }: { marks: number }) {
  return (
    <div className="shrink-0 border border-gray-400 px-1.5 py-0.5 min-w-[32px] text-center">
      <span className="text-[11px] font-semibold text-gray-700 dark:text-gray-300 leading-none">[{marks}]</span>
    </div>
  );
}

function EditToolbar({
  editing,
  regenerating,
  onEdit,
  onRegenerate,
}: {
  editing: boolean;
  regenerating: boolean;
  onEdit: () => void;
  onRegenerate: () => void;
}) {
  return (
    <div className="absolute -top-3 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-150 z-10">
      <button
        onClick={onEdit}
        disabled={regenerating}
        className="flex items-center gap-1 px-2 py-1 rounded bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 shadow-sm text-[11px] font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
      >
        {editing ? <X className="w-3 h-3" /> : <Pencil className="w-3 h-3" />}
        {editing ? "Cancel" : "Edit"}
      </button>
      <button
        onClick={onRegenerate}
        disabled={regenerating || editing}
        className="flex items-center gap-1 px-2 py-1 rounded bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 shadow-sm text-[11px] font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
      >
        {regenerating ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
        {regenerating ? "Regenerating…" : "Regenerate"}
      </button>
    </div>
  );
}

function QuestionBlock({
  question,
  onSave,
  onRegenerate,
  regenerating,
}: {
  question: Question;
  onSave: (q: Question) => void;
  onRegenerate: () => void;
  regenerating: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draftPrompt, setDraftPrompt] = useState(question.prompt);
  const [draftSubParts, setDraftSubParts] = useState<SubPart[]>(question.sub_parts);

  const startEdit = () => {
    setDraftPrompt(question.prompt);
    setDraftSubParts(question.sub_parts);
    setEditing(true);
  };

  const handleSave = () => {
    onSave({ ...question, prompt: draftPrompt, sub_parts: draftSubParts });
    setEditing(false);
    toast.success("Changes saved.");
  };

  const mcq = isMcqLike(question.type);

  return (
    <div className="relative group">
      <EditToolbar
        editing={editing}
        regenerating={regenerating}
        onEdit={() => (editing ? setEditing(false) : startEdit())}
        onRegenerate={onRegenerate}
      />
      <div
        className={cn(
          "rounded-sm transition-colors",
          editing
            ? "bg-amber-50/60 dark:bg-amber-950/20 ring-1 ring-amber-300/60 p-2 -mx-2"
            : "hover:bg-gray-50/60 dark:hover:bg-zinc-800/40",
          regenerating && "opacity-50"
        )}
      >
        {question.context_passage && (
          <div className="ml-8 mb-3 p-3 rounded border border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800/60">
            <p className="text-[12px] leading-relaxed italic text-gray-600 dark:text-gray-400 whitespace-pre-line">
              {question.context_passage}
            </p>
          </div>
        )}

        {/* Question stem */}
        <div className="flex items-start gap-3">
          <span className="font-bold text-[13px] shrink-0 w-7 pt-0.5">{question.number}</span>
          <div className="flex-1">
            {editing ? (
              <Textarea
                value={draftPrompt}
                onChange={(e) => setDraftPrompt(e.target.value)}
                className="text-[13px] min-h-[60px] resize-none font-[family-name:var(--font-figtree)]"
                autoFocus
              />
            ) : (
              <p className="text-[13px] leading-relaxed whitespace-pre-line">{question.prompt}</p>
            )}
            {!mcq && question.sub_parts.length === 0 && !editing && (
              <AnswerLines count={answerLinesForMarks(question.marks, question.type)} />
            )}
          </div>
          <MarksBox marks={question.marks} />
        </div>

        {/* Sub-parts */}
        {(editing ? draftSubParts : question.sub_parts).length > 0 && (
          <div className="ml-10 mt-3 space-y-4">
            {(editing ? draftSubParts : question.sub_parts).map((sp, i) => (
              <div key={sp.label} className="flex items-start gap-3">
                <span className="text-[13px] font-medium shrink-0 w-7 pt-0.5">{sp.label}</span>
                <div className="flex-1">
                  {editing ? (
                    <Textarea
                      value={sp.prompt}
                      onChange={(e) =>
                        setDraftSubParts((prev) =>
                          prev.map((p, idx) => (idx === i ? { ...p, prompt: e.target.value } : p))
                        )
                      }
                      className="text-[13px] min-h-[48px] resize-none font-[family-name:var(--font-figtree)]"
                    />
                  ) : (
                    <>
                      <p className="text-[13px] leading-relaxed whitespace-pre-line">{sp.prompt}</p>
                      <AnswerLines count={answerLinesForMarks(sp.marks, question.type)} />
                    </>
                  )}
                </div>
                <MarksBox marks={sp.marks} />
              </div>
            ))}
          </div>
        )}

        {editing && (
          <div className="flex gap-2 justify-end pt-2 ml-8">
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button size="sm" className="h-7 text-xs" onClick={handleSave}>
              Save
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export function EditableStep({
  sessionId,
  blueprint,
  paper,
  onPaperChange,
  onNext,
  onBack,
}: EditableStepProps) {
  const [regeneratingQuestion, setRegeneratingQuestion] = useState<string | null>(null);
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);

  const handleRegenerateQuestion = async (sectionId: string, questionId: string, number: string) => {
    setRegeneratingQuestion(questionId);
    try {
      const fresh = await regenerateQuestion(sessionId, {
        paper,
        blueprint,
        question_id: questionId,
      });
      onPaperChange(replaceQuestion(paper, sectionId, fresh));
      toast.success(`Question ${number} regenerated.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Regeneration failed.");
    } finally {
      setRegeneratingQuestion(null);
    }
  };

  const handleRegenerateSection = async (sectionId: string) => {
    setRegeneratingSection(sectionId);
    try {
      const fresh = await regenerateSection(sessionId, {
        paper,
        blueprint,
        section_id: sectionId,
      });
      onPaperChange(replaceSection(paper, fresh));
      toast.success(`${fresh.title} regenerated.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Section regeneration failed.");
    } finally {
      setRegeneratingSection(null);
    }
  };

  const handleSaveQuestion = (sectionId: string) => (q: Question) => {
    onPaperChange(replaceQuestion(paper, sectionId, q));
  };

  return (
    <div className="max-w-4xl mx-auto w-full space-y-4">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Editable Paper</h2>
          <p className="text-muted-foreground text-xs mt-0.5">
            Hover any question to edit or regenerate it.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onBack} className="shrink-0 text-sm">
          ← Back
        </Button>
      </div>

      {/* Paper sheet */}
      <div className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-lg shadow-md overflow-hidden">

        {/* Paper header */}
        <div className="border-b border-gray-300 dark:border-zinc-700 px-10 py-6">
          <div className="flex items-start justify-between gap-6">
            <div className="space-y-0.5">
              <p className="text-[11px] font-semibold tracking-[0.15em] uppercase text-gray-500">
                {blueprint.board} · {blueprint.level}
              </p>
              <h1 className="text-[22px] font-black tracking-tight text-gray-900 dark:text-white uppercase">
                {paper.title}
              </h1>
              <p className="text-[13px] text-gray-600 dark:text-gray-400 font-medium">{blueprint.subject}</p>
            </div>
            <div className="text-right space-y-1 shrink-0">
              <div className="border border-gray-400 px-3 py-1.5 text-center">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Total Marks</p>
                <p className="text-lg font-black text-gray-900 dark:text-white">{paper.total_marks}</p>
              </div>
              <p className="text-[11px] text-gray-500">{formatDuration(paper.duration_minutes)}</p>
            </div>
          </div>

          <Separator className="my-4 bg-gray-300 dark:bg-zinc-700" />

          <div className="space-y-1 text-[12px] text-gray-600 dark:text-gray-400">
            <p className="font-semibold text-gray-800 dark:text-gray-200">INSTRUCTIONS TO CANDIDATES</p>
            <ul className="list-disc list-inside space-y-0.5 ml-1">
              {paper.instructions.map((inst, i) => (
                <li key={i}>{inst}</li>
              ))}
            </ul>
          </div>

          <div className="mt-3 flex gap-8 text-[11px] text-gray-500">
            <span>Candidate Name: <span className="inline-block w-40 border-b border-gray-400 ml-1" /></span>
            <span>Centre No.: <span className="inline-block w-24 border-b border-gray-400 ml-1" /></span>
            <span>Candidate No.: <span className="inline-block w-16 border-b border-gray-400 ml-1" /></span>
          </div>
        </div>

        {/* Sections */}
        <div className="px-10 py-6 space-y-10">
          {paper.sections.map((section, sectionIndex) => (
            <div key={section.id}>
              {/* Section heading */}
              <div className="flex items-center justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="text-[14px] font-black tracking-widest text-gray-900 dark:text-white uppercase">
                      {section.title}
                    </h2>
                    <div className="flex-1 h-px bg-gray-400 dark:bg-zinc-600" />
                    <span className="text-[12px] font-semibold text-gray-500 shrink-0">
                      {section.marks} marks
                    </span>
                  </div>
                  <p className="text-[12px] text-gray-500 dark:text-gray-400 italic">
                    {section.instructions}
                  </p>
                </div>
                <button
                  disabled={regeneratingSection !== null}
                  onClick={() => handleRegenerateSection(section.id)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-[11px] font-medium text-gray-500 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors shrink-0 disabled:opacity-50"
                >
                  {regeneratingSection === section.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3 h-3" />
                  )}
                  Regenerate section
                </button>
              </div>

              <div className={cn("space-y-6", regeneratingSection === section.id && "opacity-50")}>
                {section.questions.map((q) => (
                  <QuestionBlock
                    key={q.id}
                    question={q}
                    regenerating={regeneratingQuestion === q.id}
                    onSave={handleSaveQuestion(section.id)}
                    onRegenerate={() => handleRegenerateQuestion(section.id, q.id, q.number)}
                  />
                ))}
              </div>

              {sectionIndex !== paper.sections.length - 1 && (
                <div className="mt-6 text-right text-[11px] text-gray-400 italic">
                  [Turn over]
                </div>
              )}
            </div>
          ))}

          <div className="text-center text-[12px] text-gray-400 font-medium tracking-widest pt-4 border-t border-gray-200 dark:border-zinc-700">
            END OF PAPER
          </div>
        </div>
      </div>

      <Button className="w-full h-11 text-sm font-semibold" onClick={onNext}>
        <FileDown className="w-4 h-4 mr-2" />
        Proceed to PDF Export
      </Button>
    </div>
  );
}
