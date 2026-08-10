"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Research" },
  { href: "/usage", label: "Usage" },
  { href: "/escalations", label: "Escalations" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-2 border-b border-border bg-onyx/90 px-3 backdrop-blur-md sm:px-6">
      <Link href="/" className="flex min-w-0 shrink-0 items-center gap-2">
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-cobalt font-mono text-[11px] font-semibold text-white">
          §
        </span>
        <span className="hidden truncate text-sm font-medium tracking-tight text-ivory sm:inline">
          Kanoon ke Haath
        </span>
      </Link>
      <nav className="flex items-center gap-0.5 sm:gap-1">
        {links.map((link) => {
          const active =
            link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-full px-2.5 py-1.5 text-xs whitespace-nowrap transition-colors sm:px-3 sm:text-sm",
                active
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
              )}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
