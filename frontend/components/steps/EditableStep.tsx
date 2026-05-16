"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  FileDown,
  Loader2,
  Pencil,
  RefreshCw,
  Check,
  X,
} from "lucide-react";
import { toast } from "sonner";

interface SubPart {
  label: string;
  text: string;
  marks: number;
}

interface Question {
  id: string;
  number: string;
  text: string;
  marks: number;
  options?: string[];
  subParts?: SubPart[];
  answerLines?: number;
}

interface Section {
  id: string;
  title: string;
  instruction: string;
  type: "MCQ" | "Structured" | "Essay";
  questions: Question[];
}

const INITIAL_SECTIONS: Section[] = [
  {
    id: "A",
    title: "SECTION A",
    instruction:
      "Answer ALL questions in this section. Each question carries 1 mark. Choose the best answer from the options given.",
    type: "MCQ",
    questions: [
      {
        id: "a1",
        number: "1",
        text: "A uniform beam of length 4.0 m and weight 200 N is supported at both ends. A load of 500 N is placed 1.0 m from the left end. What is the reaction force at the left support?",
        marks: 1,
        options: ["A   312 N", "B   275 N", "C   425 N", "D   188 N"],
      },
      {
        id: "a2",
        number: "2",
        text: "Which of the following best describes the term 'specific heat capacity' of a substance?",
        marks: 1,
        options: [
          "A   Energy required per unit mass per unit temperature rise",
          "B   Energy required to melt 1 kg of the substance",
          "C   Energy required to vaporise 1 kg of the substance",
          "D   Energy stored per unit volume per unit temperature rise",
        ],
      },
      {
        id: "a3",
        number: "3",
        text: "A wave has a frequency of 250 Hz and a wavelength of 1.4 m. What is its speed?",
        marks: 1,
        options: ["A   178 m s⁻¹", "B   350 m s⁻¹", "C   250 m s⁻¹", "D   500 m s⁻¹"],
      },
      {
        id: "a4",
        number: "4",
        text: "The cross-sectional area of a wire is halved and its length is doubled. By what factor does the resistance change?",
        marks: 1,
        options: ["A   ×2", "B   ×4", "C   ×0.5", "D   ×1"],
      },
      {
        id: "a5",
        number: "5",
        text: "An object is projected horizontally from a cliff of height 80 m. Taking g = 10 m s⁻², what is the time taken to reach the ground?",
        marks: 1,
        options: ["A   2.8 s", "B   4.0 s", "C   8.0 s", "D   1.6 s"],
      },
    ],
  },
  {
    id: "B",
    title: "SECTION B",
    instruction:
      "Answer ALL questions in this section. Show all working clearly. Marks are awarded for method as well as correct answers.",
    type: "Structured",
    questions: [
      {
        id: "b1",
        number: "1",
        text: "A car of mass 1200 kg accelerates from rest to 20 m s⁻¹ in 8.0 s on a straight horizontal road.",
        marks: 10,
        subParts: [
          { label: "(a)", text: "Calculate the acceleration of the car.", marks: 2 },
          { label: "(b)", text: "Calculate the net force acting on the car during acceleration.", marks: 2 },
          {
            label: "(c)",
            text: "If the driving force is 4500 N, calculate the frictional force opposing motion.",
            marks: 2,
          },
          {
            label: "(d)",
            text: "Sketch a velocity-time graph for the motion described. Label both axes clearly and mark the values.",
            marks: 4,
          },
        ],
      },
      {
        id: "b2",
        number: "2",
        text: "A spring of spring constant 250 N m⁻¹ is compressed by 8.0 cm from its natural length.",
        marks: 10,
        subParts: [
          { label: "(a)", text: "Calculate the elastic potential energy stored in the spring.", marks: 3 },
          {
            label: "(b)",
            text: "When released, the spring launches a ball of mass 50 g vertically upward. Calculate the maximum height reached, assuming all elastic potential energy converts to gravitational potential energy. (g = 10 m s⁻²)",
            marks: 4,
          },
          {
            label: "(c)",
            text: "State one assumption made in (b) and explain how removing this assumption would affect your answer.",
            marks: 3,
          },
        ],
      },
    ],
  },
  {
    id: "C",
    title: "SECTION C",
    instruction:
      "Answer ONE question only from this section. Your answer should be in continuous prose and include equations and diagrams where appropriate.",
    type: "Essay",
    questions: [
      {
        id: "c1",
        number: "1",
        text: "Describe and explain the factors that affect the resistance of a metallic conductor. In your answer, include a discussion of how temperature affects resistance and how this behaviour differs between metallic conductors and semiconductors. Use appropriate equations and diagrams where necessary.",
        marks: 20,
        answerLines: 20,
      },
      {
        id: "c2",
        number: "2",
        text: "Explain the concept of simple harmonic motion (SHM). Derive the expressions for displacement, velocity and acceleration of a body undergoing SHM from first principles. Illustrate your answer with a practical example and discuss the effect of damping on SHM.",
        marks: 20,
        answerLines: 20,
      },
    ],
  },
];

const ANSWER_LINES_FOR_MARKS = (marks: number, type: string) => {
  if (type === "Essay") return 18;
  if (marks >= 4) return 6;
  if (marks >= 3) return 4;
  if (marks >= 2) return 3;
  return 2;
};

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
      <span className="text-[11px] font-semibold text-gray-700 leading-none">[{marks}]</span>
    </div>
  );
}

function EditToolbar({
  editing,
  regenerating,
  saved,
  onEdit,
  onRegenerate,
}: {
  editing: boolean;
  regenerating: boolean;
  saved: boolean;
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
        {saved ? (
          <Check className="w-3 h-3 text-green-500" />
        ) : editing ? (
          <X className="w-3 h-3" />
        ) : (
          <Pencil className="w-3 h-3" />
        )}
        {editing ? "Cancel" : "Edit"}
      </button>
      <button
        onClick={onRegenerate}
        disabled={regenerating}
        className="flex items-center gap-1 px-2 py-1 rounded bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 shadow-sm text-[11px] font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
      >
        {regenerating ? (
          <Loader2 className="w-3 h-3 animate-spin" />
        ) : (
          <RefreshCw className="w-3 h-3" />
        )}
        {regenerating ? "Regenerating…" : "Regenerate"}
      </button>
    </div>
  );
}

function MCQQuestion({ question }: { question: Question }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(question.text);
  const [options, setOptions] = useState(question.options ?? []);
  const [regenerating, setRegenerating] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleRegenerate = async () => {
    setRegenerating(true);
    await new Promise((r) => setTimeout(r, 1500));
    setRegenerating(false);
    toast.success(`Question ${question.number} regenerated.`);
  };

  const handleSave = () => {
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    toast.success("Changes saved.");
  };

  return (
    <div className="relative group">
      <EditToolbar
        editing={editing}
        regenerating={regenerating}
        saved={saved}
        onEdit={() => setEditing((v) => !v)}
        onRegenerate={handleRegenerate}
      />
      <div
        className={cn(
          "rounded-sm transition-colors",
          editing ? "bg-amber-50/60 dark:bg-amber-950/20 ring-1 ring-amber-300/60 p-2 -mx-2" : "hover:bg-gray-50/60 dark:hover:bg-zinc-800/40"
        )}
      >
        <div className="flex items-start gap-3">
          <span className="font-bold text-[13px] shrink-0 w-5 pt-0.5">{question.number}</span>
          <div className="flex-1 space-y-2.5">
            {editing ? (
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="text-[13px] min-h-[60px] resize-none font-[family-name:var(--font-figtree)]"
                autoFocus
              />
            ) : (
              <p className="text-[13px] leading-relaxed">{text}</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
              {options.map((opt, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full border border-gray-500 shrink-0 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full" />
                  </div>
                  {editing ? (
                    <input
                      value={opt}
                      onChange={(e) =>
                        setOptions((prev) =>
                          prev.map((o, idx) => (idx === i ? e.target.value : o))
                        )
                      }
                      className="text-[13px] flex-1 border-b border-gray-300 bg-transparent outline-none py-0.5 font-[family-name:var(--font-figtree)]"
                    />
                  ) : (
                    <span className="text-[13px]">{opt}</span>
                  )}
                </div>
              ))}
            </div>
            {editing && (
              <div className="flex gap-2 justify-end pt-1">
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setEditing(false)}>Cancel</Button>
                <Button size="sm" className="h-7 text-xs" onClick={handleSave}>Save</Button>
              </div>
            )}
          </div>
          <MarksBox marks={question.marks} />
        </div>
      </div>
    </div>
  );
}

function StructuredQuestion({ question }: { question: Question }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(question.text);
  const [subParts, setSubParts] = useState<SubPart[]>(question.subParts ?? []);
  const [regenerating, setRegenerating] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleRegenerate = async () => {
    setRegenerating(true);
    await new Promise((r) => setTimeout(r, 1500));
    setRegenerating(false);
    toast.success(`Question ${question.number} regenerated.`);
  };

  const handleSave = () => {
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    toast.success("Changes saved.");
  };

  return (
    <div className="relative group">
      <EditToolbar
        editing={editing}
        regenerating={regenerating}
        saved={saved}
        onEdit={() => setEditing((v) => !v)}
        onRegenerate={handleRegenerate}
      />
      <div
        className={cn(
          "rounded-sm transition-colors",
          editing ? "bg-amber-50/60 dark:bg-amber-950/20 ring-1 ring-amber-300/60 p-2 -mx-2" : ""
        )}
      >
        {/* Question stem */}
        <div className="flex items-start gap-3 mb-3">
          <span className="font-bold text-[13px] shrink-0 w-5 pt-0.5">{question.number}</span>
          <div className="flex-1">
            {editing ? (
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="text-[13px] min-h-[56px] resize-none font-[family-name:var(--font-figtree)]"
                autoFocus
              />
            ) : (
              <p className="text-[13px] leading-relaxed">{text}</p>
            )}
          </div>
          <span className="text-[12px] font-semibold text-gray-500 shrink-0 pt-0.5">[{question.marks}]</span>
        </div>

        {/* Sub-parts */}
        {subParts.length > 0 && (
          <div className="ml-8 space-y-4">
            {subParts.map((sp, i) => (
              <div key={sp.label}>
                <div className="flex items-start gap-3">
                  <span className="text-[13px] font-medium shrink-0 w-7 pt-0.5">{sp.label}</span>
                  <div className="flex-1">
                    {editing ? (
                      <Textarea
                        value={sp.text}
                        onChange={(e) =>
                          setSubParts((prev) =>
                            prev.map((p, idx) => (idx === i ? { ...p, text: e.target.value } : p))
                          )
                        }
                        className="text-[13px] min-h-[48px] resize-none font-[family-name:var(--font-figtree)]"
                      />
                    ) : (
                      <p className="text-[13px] leading-relaxed">{sp.text}</p>
                    )}
                    <AnswerLines count={ANSWER_LINES_FOR_MARKS(sp.marks, "Structured")} />
                  </div>
                  <MarksBox marks={sp.marks} />
                </div>
              </div>
            ))}
          </div>
        )}

        {editing && (
          <div className="flex gap-2 justify-end pt-2 ml-8">
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" className="h-7 text-xs" onClick={handleSave}>Save</Button>
          </div>
        )}
      </div>
    </div>
  );
}

function EssayQuestion({ question }: { question: Question }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(question.text);
  const [regenerating, setRegenerating] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleRegenerate = async () => {
    setRegenerating(true);
    await new Promise((r) => setTimeout(r, 1500));
    setRegenerating(false);
    toast.success(`Question ${question.number} regenerated.`);
  };

  const handleSave = () => {
    setEditing(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    toast.success("Changes saved.");
  };

  return (
    <div className="relative group">
      <EditToolbar
        editing={editing}
        regenerating={regenerating}
        saved={saved}
        onEdit={() => setEditing((v) => !v)}
        onRegenerate={handleRegenerate}
      />
      <div
        className={cn(
          "rounded-sm transition-colors",
          editing ? "bg-amber-50/60 dark:bg-amber-950/20 ring-1 ring-amber-300/60 p-2 -mx-2" : ""
        )}
      >
        <div className="flex items-start gap-3 mb-2">
          <span className="font-bold text-[13px] shrink-0 w-5 pt-0.5">{question.number}</span>
          <div className="flex-1">
            {editing ? (
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="text-[13px] min-h-[80px] resize-none font-[family-name:var(--font-figtree)]"
                autoFocus
              />
            ) : (
              <p className="text-[13px] leading-relaxed">{text}</p>
            )}
          </div>
          <MarksBox marks={question.marks} />
        </div>
        <div className="ml-8">
          <AnswerLines count={question.answerLines ?? ANSWER_LINES_FOR_MARKS(question.marks, "Essay")} />
        </div>
        {editing && (
          <div className="flex gap-2 justify-end pt-2 ml-8">
            <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" className="h-7 text-xs" onClick={handleSave}>Save</Button>
          </div>
        )}
      </div>
    </div>
  );
}

interface EditableStepProps {
  onNext: () => void;
  onBack: () => void;
}

export function EditableStep({ onNext, onBack }: EditableStepProps) {
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);

  const handleRegenerateSection = async (sectionId: string) => {
    setRegeneratingSection(sectionId);
    await new Promise((r) => setTimeout(r, 2000));
    setRegeneratingSection(null);
    toast.success(`Section ${sectionId} regenerated.`);
  };

  const totalMarks = INITIAL_SECTIONS.reduce(
    (acc, s) => acc + s.questions.reduce((a, q) => a + q.marks, 0),
    0
  );

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
              <p className="text-[11px] font-semibold tracking-[0.15em] uppercase text-gray-500">Cambridge International AS & A Level</p>
              <h1 className="text-[22px] font-black tracking-tight text-gray-900 dark:text-white">PHYSICS</h1>
              <p className="text-[13px] text-gray-600 dark:text-gray-400 font-medium">Paper 1 · May/June 2025</p>
            </div>
            <div className="text-right space-y-1 shrink-0">
              <div className="border border-gray-400 px-3 py-1.5 text-center">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Total Marks</p>
                <p className="text-lg font-black text-gray-900 dark:text-white">{totalMarks}</p>
              </div>
              <p className="text-[11px] text-gray-500">2 hours 30 minutes</p>
            </div>
          </div>

          <Separator className="my-4 bg-gray-300 dark:bg-zinc-700" />

          <div className="space-y-1 text-[12px] text-gray-600 dark:text-gray-400">
            <p className="font-semibold text-gray-800 dark:text-gray-200">INSTRUCTIONS TO CANDIDATES</p>
            <ul className="list-disc list-inside space-y-0.5 ml-1">
              <li>Answer <span className="font-semibold">all</span> questions in Section A and Section B.</li>
              <li>Answer <span className="font-semibold">one</span> question from Section C.</li>
              <li>All working must be shown. Marks may be given for a correct method even if the answer is wrong.</li>
              <li>Calculators may be used.</li>
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
          {INITIAL_SECTIONS.map((section) => (
            <div key={section.id}>
              {/* Section heading */}
              <div className="flex items-center justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="text-[14px] font-black tracking-widest text-gray-900 dark:text-white">
                      {section.title}
                    </h2>
                    <div className="flex-1 h-px bg-gray-400 dark:bg-zinc-600" />
                    <span className="text-[12px] font-semibold text-gray-500 shrink-0">
                      {section.questions.reduce((a, q) => a + q.marks, 0)} marks
                    </span>
                  </div>
                  <p className="text-[12px] text-gray-500 dark:text-gray-400 italic">
                    {section.instruction}
                  </p>
                </div>
                <button
                  disabled={regeneratingSection === section.id}
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

              <div className="space-y-6">
                {section.questions.map((q) => {
                  if (section.type === "MCQ") return <MCQQuestion key={q.id} question={q} />;
                  if (section.type === "Structured") return <StructuredQuestion key={q.id} question={q} />;
                  return <EssayQuestion key={q.id} question={q} />;
                })}
              </div>

              {section.id !== "C" && (
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

      <Button
        className="w-full h-11 text-sm font-semibold"
        onClick={onNext}
      >
        <FileDown className="w-4 h-4 mr-2" />
        Proceed to PDF Export
      </Button>
    </div>
  );
}
