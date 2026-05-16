"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  FileText,
  Users,
  BookOpen,
  Settings,
  Sparkles,
  GraduationCap,
  ChevronRight,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/papers", icon: FileText, label: "Papers" },
  { href: "/students", icon: Users, label: "Students" },
  { href: "/courses", icon: BookOpen, label: "Courses" },
];

const BOTTOM_ITEMS = [
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-60 shrink-0 hidden md:flex flex-col h-screen sticky top-0 border-r border-border bg-card">
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-border shrink-0">
        <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-sm">
          <Sparkles className="w-4 h-4 text-primary-foreground" />
        </div>
        <div>
          <p className="font-black text-[15px] tracking-tight leading-none">SmartPaper</p>
          <p className="text-[10px] text-muted-foreground mt-0.5 font-medium">LMS Platform</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-2">
          Main Menu
        </p>
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
              isActive(href)
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <Icon className={cn("w-4 h-4 shrink-0", isActive(href) ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground")} />
            {label}
            {isActive(href) && <ChevronRight className="w-3.5 h-3.5 ml-auto opacity-70" />}
          </Link>
        ))}

        <div className="pt-4">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest px-3 mb-2">
            Account
          </p>
          {BOTTOM_ITEMS.map(({ href, icon: Icon, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                isActive(href)
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className={cn("w-4 h-4 shrink-0", isActive(href) ? "text-primary-foreground" : "text-muted-foreground group-hover:text-foreground")} />
              {label}
            </Link>
          ))}
        </div>
      </nav>

      {/* User card */}
      <div className="px-3 pb-4">
        <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/60 border border-border">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0">
            <GraduationCap className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold truncate leading-none">Mr. Chalaka</p>
            <p className="text-xs text-muted-foreground mt-0.5">Teacher · Physics</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
