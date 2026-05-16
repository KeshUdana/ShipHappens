"use client";

import { Bell, Search, Menu } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface TopbarProps {
  title: string;
  subtitle?: string;
}

export function Topbar({ title, subtitle }: TopbarProps) {
  return (
    <header className="h-16 border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-40 flex items-center px-6 gap-4">
      {/* Mobile menu button */}
      <Button variant="ghost" size="icon" className="md:hidden w-8 h-8">
        <Menu className="w-4 h-4" />
      </Button>

      {/* Title */}
      <div className="flex-1 min-w-0">
        <h1 className="text-[15px] font-bold leading-tight truncate">{title}</h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground leading-tight mt-0.5">{subtitle}</p>
        )}
      </div>

      {/* Search */}
      <div className="relative hidden sm:block w-52">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
        <Input
          placeholder="Search papers…"
          className="pl-8 h-8 text-sm bg-muted border-0 focus-visible:ring-1"
        />
      </div>

      {/* Notifications */}
      <Button variant="ghost" size="icon" className="w-8 h-8 relative">
        <Bell className="w-4 h-4" />
        <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-red-500" />
      </Button>
    </header>
  );
}
