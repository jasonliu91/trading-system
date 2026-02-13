"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/mind", label: "Market Mind" },
  { href: "/decisions", label: "Decisions" },
  { href: "/performance", label: "Performance" }
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-bg/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3 md:px-8">
          <Link href="/" className="text-sm font-semibold tracking-[0.16em] text-text">
            ETH AI TRADING
          </Link>

          <nav className="flex items-center gap-2">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-lg px-3 py-1.5 text-xs uppercase tracking-[0.14em] transition ${
                    active ? "bg-accent/25 text-accent" : "text-muted hover:text-text"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {children}
    </div>
  );
}

