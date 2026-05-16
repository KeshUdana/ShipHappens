"use client";

import Link from "next/link";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  FileText,
  Sparkles,
  Users,
  TrendingUp,
  Clock,
  Download,
  Eye,
  Copy,
  MoreHorizontal,
  BookOpen,
  Star,
  Calendar,
  ArrowUpRight,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const STATS = [
  {
    label: "Papers Generated",
    value: "24",
    delta: "+3 this week",
    positive: true,
    icon: FileText,
    color: "text-violet-600 dark:text-violet-400",
    bg: "bg-violet-50 dark:bg-violet-950",
  },
  {
    label: "Active Students",
    value: "186",
    delta: "+12 this month",
    positive: true,
    icon: Users,
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-950",
  },
  {
    label: "Subjects Covered",
    value: "6",
    delta: "Physics · Chem · Bio…",
    positive: null,
    icon: BookOpen,
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-50 dark:bg-emerald-950",
  },
  {
    label: "Avg. Paper Score",
    value: "74%",
    delta: "+2.1% vs last month",
    positive: true,
    icon: TrendingUp,
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-950",
  },
];

interface Paper {
  id: string;
  title: string;
  subject: string;
  board: string;
  level: string;
  marks: number;
  questions: number;
  createdAt: string;
  status: "draft" | "published" | "archived";
  uses: number;
}

const PAST_PAPERS: Paper[] = [
  { id: "1", title: "Physics Paper 1 — Mechanics", subject: "Physics", board: "Cambridge (CAIE)", level: "A/L", marks: 120, questions: 28, createdAt: "2025-05-14", status: "published", uses: 34 },
  { id: "2", title: "Chemistry Paper 2 — Organic", subject: "Chemistry", board: "Edexcel", level: "A/L", marks: 80, questions: 16, createdAt: "2025-05-10", status: "published", uses: 27 },
  { id: "3", title: "Biology Mock Exam — Full Paper", subject: "Biology", board: "Cambridge (CAIE)", level: "O/L", marks: 100, questions: 40, createdAt: "2025-05-06", status: "draft", uses: 0 },
  { id: "4", title: "Physics Paper 2 — Electricity & Waves", subject: "Physics", board: "Cambridge (CAIE)", level: "A/L", marks: 120, questions: 30, createdAt: "2025-04-28", status: "published", uses: 52 },
  { id: "5", title: "Mathematics — Pure 1 Revision", subject: "Mathematics", board: "Cambridge (CAIE)", level: "A/L", marks: 75, questions: 12, createdAt: "2025-04-20", status: "archived", uses: 18 },
  { id: "6", title: "Combined Science — Term Test", subject: "Science", board: "Local (Sri Lanka)", level: "O/L", marks: 100, questions: 50, createdAt: "2025-04-12", status: "published", uses: 61 },
];

const SUBJECT_COLORS: Record<string, string> = {
  Physics:     "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
  Chemistry:   "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
  Biology:     "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  Mathematics: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Science:     "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
};

const STATUS_STYLES: Record<string, string> = {
  published: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  draft:     "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  archived:  "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
};

const RECENT_ACTIVITY = [
  { action: "Generated", paper: "Physics Paper 1 — Mechanics", time: "2 hours ago", icon: Zap, color: "text-violet-500" },
  { action: "Downloaded", paper: "Chemistry Paper 2 — Organic", time: "Yesterday", icon: Download, color: "text-blue-500" },
  { action: "Generated", paper: "Biology Mock Exam — Full Paper", time: "3 days ago", icon: Zap, color: "text-violet-500" },
  { action: "Downloaded", paper: "Physics Paper 2 — Electricity", time: "1 week ago", icon: Download, color: "text-blue-500" },
];

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export default function DashboardPage() {
  return (
    <DashboardLayout
      title="Dashboard"
      subtitle="Welcome back, Mr. Chalaka"
    >
      <div className="space-y-6 max-w-7xl">

        {/* Generate CTA banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 dark:from-zinc-900 dark:via-zinc-800 dark:to-zinc-900 p-6 shadow-lg">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-violet-600/20 via-transparent to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-indigo-600/15 via-transparent to-transparent pointer-events-none" />
          <div className="relative flex flex-col sm:flex-row items-start sm:items-center gap-5 justify-between">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-violet-400" />
                <span className="text-xs font-semibold text-violet-400 uppercase tracking-widest">AI-Powered</span>
              </div>
              <h2 className="text-xl font-black text-white">Generate a New Exam Paper</h2>
              <p className="text-sm text-gray-400 max-w-md">
                Upload past papers and let SmartPaper extract the structure, generate questions, and export a print-ready PDF in minutes.
              </p>
            </div>
            <Link href="/generate" className="shrink-0">
              <Button size="lg" className="bg-white text-gray-900 hover:bg-gray-100 font-bold shadow-md gap-2 h-11">
                <Sparkles className="w-4 h-4" />
                Generate Paper
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STATS.map((stat) => (
            <Card key={stat.label} className="border-border shadow-none">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center shrink-0", stat.bg)}>
                    <stat.icon className={cn("w-4 h-4", stat.color)} />
                  </div>
                  {stat.positive !== null && (
                    <div className={cn("flex items-center gap-0.5 text-[11px] font-semibold", stat.positive ? "text-emerald-600" : "text-red-500")}>
                      <ArrowUpRight className="w-3 h-3" />
                    </div>
                  )}
                </div>
                <div className="mt-3">
                  <p className="text-2xl font-black">{stat.value}</p>
                  <p className="text-xs font-medium text-muted-foreground mt-0.5">{stat.label}</p>
                  <p className={cn("text-[11px] mt-1", stat.positive === true ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
                    {stat.delta}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main content: papers + activity */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* Past papers table */}
          <div className="xl:col-span-2 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-[15px] font-bold">Recent Papers</h2>
                <p className="text-xs text-muted-foreground">Your last generated exam papers</p>
              </div>
              <Link href="/papers">
                <Button variant="ghost" size="sm" className="text-xs h-8 gap-1.5 text-muted-foreground">
                  View all <ArrowUpRight className="w-3 h-3" />
                </Button>
              </Link>
            </div>

            <Card className="border-border shadow-none overflow-hidden">
              <div className="divide-y divide-border">
                {PAST_PAPERS.map((paper) => (
                  <div key={paper.id} className="group flex items-center gap-4 px-5 py-4 hover:bg-muted/40 transition-colors">
                    {/* Icon */}
                    <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center shrink-0", SUBJECT_COLORS[paper.subject] ?? "bg-gray-100 text-gray-600")}>
                      <FileText className="w-4 h-4" />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-semibold truncate">{paper.title}</p>
                        <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full", STATUS_STYLES[paper.status])}>
                          {paper.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-muted-foreground flex-wrap">
                        <span>{paper.board}</span>
                        <span className="w-1 h-1 rounded-full bg-border" />
                        <span>{paper.level}</span>
                        <span className="w-1 h-1 rounded-full bg-border" />
                        <span>{paper.marks} marks · {paper.questions} questions</span>
                        <span className="w-1 h-1 rounded-full bg-border" />
                        <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(paper.createdAt)}</span>
                        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{paper.uses} uses</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <Button variant="ghost" size="icon" className="w-7 h-7">
                        <Eye className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="w-7 h-7">
                        <Download className="w-3.5 h-3.5" />
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger className="flex items-center justify-center w-7 h-7 rounded-md hover:bg-muted transition-colors">
                          <MoreHorizontal className="w-3.5 h-3.5" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem><Eye className="w-3.5 h-3.5 mr-2" />Preview</DropdownMenuItem>
                          <DropdownMenuItem><Copy className="w-3.5 h-3.5 mr-2" />Duplicate</DropdownMenuItem>
                          <DropdownMenuItem><Download className="w-3.5 h-3.5 mr-2" />Download PDF</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Right column */}
          <div className="space-y-5">

            {/* Quick actions */}
            <div className="space-y-3">
              <h2 className="text-[15px] font-bold">Quick Actions</h2>
              <div className="grid grid-cols-1 gap-2">
                <Link href="/generate">
                  <button className="w-full flex items-center gap-3 p-3.5 rounded-xl border border-border bg-card hover:bg-muted/50 transition-colors text-left group">
                    <div className="w-9 h-9 rounded-lg bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center shrink-0">
                      <Sparkles className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">Generate Paper</p>
                      <p className="text-[11px] text-muted-foreground">Upload PDFs and generate</p>
                    </div>
                    <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                </Link>
                <button className="w-full flex items-center gap-3 p-3.5 rounded-xl border border-border bg-card hover:bg-muted/50 transition-colors text-left group">
                  <div className="w-9 h-9 rounded-lg bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center shrink-0">
                    <Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">Add Students</p>
                    <p className="text-[11px] text-muted-foreground">Invite via email or link</p>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
                <button className="w-full flex items-center gap-3 p-3.5 rounded-xl border border-border bg-card hover:bg-muted/50 transition-colors text-left group">
                  <div className="w-9 h-9 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center shrink-0">
                    <Star className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">Mark Scheme</p>
                    <p className="text-[11px] text-muted-foreground">Generate answers & rubric</p>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              </div>
            </div>

            <Separator />

            {/* Recent activity */}
            <div className="space-y-3">
              <h2 className="text-[15px] font-bold">Recent Activity</h2>
              <div className="space-y-0">
                {RECENT_ACTIVITY.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 py-3 border-b border-border last:border-0">
                    <div className={cn("w-7 h-7 rounded-full bg-muted flex items-center justify-center shrink-0 mt-0.5")}>
                      <item.icon className={cn("w-3.5 h-3.5", item.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-medium leading-snug">
                        <span className="text-muted-foreground">{item.action}: </span>
                        {item.paper}
                      </p>
                      <div className="flex items-center gap-1 mt-0.5 text-[11px] text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {item.time}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
