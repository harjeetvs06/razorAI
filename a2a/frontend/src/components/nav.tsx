import { Link } from "@tanstack/react-router";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/theme-provider";

const links = [
  { to: "/", label: "Overview" },
  { to: "/catalog", label: "Catalog" },
  { to: "/negotiate", label: "Negotiate" },
  { to: "/dashboard", label: "Merchant" },
] as const;

export function Nav() {
  const { theme, toggle } = useTheme();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md transition-colors duration-300">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            R
          </span>
          <span className="font-display text-base font-semibold tracking-tight">RazorAI</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              activeOptions={{ exact: l.to === "/" }}
              className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors duration-200 hover:text-foreground"
              activeProps={{ className: "!text-foreground bg-secondary" }}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <button
          type="button"
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          className="grid size-9 place-items-center rounded-lg border border-border bg-surface transition-colors duration-300 hover:bg-secondary"
        >
          <span
            className="grid place-items-center transition-transform duration-300"
            style={{ transform: theme === "dark" ? "rotate(180deg)" : "rotate(0deg)" }}
          >
            {theme === "dark" ? (
              <Moon className="size-4 text-primary" />
            ) : (
              <Sun className="size-4 text-primary" />
            )}
          </span>
        </button>
      </div>

      <nav className="flex items-center gap-1 overflow-x-auto border-t border-border px-4 py-2 md:hidden">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            activeOptions={{ exact: l.to === "/" }}
            className="whitespace-nowrap rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors"
            activeProps={{ className: "!text-foreground bg-secondary" }}
          >
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
