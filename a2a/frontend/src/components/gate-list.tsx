import { useEffect, useState } from "react";
import { Check, ChevronDown, TriangleAlert, X } from "lucide-react";
import type { Gate } from "@/lib/razorai";

const ICON = {
  pass: Check,
  fail: X,
  warn: TriangleAlert,
} as const;

const TONE = {
  pass: "var(--color-success)",
  fail: "var(--color-destructive)",
  warn: "var(--color-warning)",
} as const;

/** Sequential reveal: one gate every `stagger` ms, so waiting = watching. */
export function GateList({
  gates,
  stagger = 150,
  collapsible = true,
}: {
  gates: Gate[];
  stagger?: number;
  collapsible?: boolean;
}) {
  const [shown, setShown] = useState(0);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    setShown(0);
    const timers = gates.map((_, i) => window.setTimeout(() => setShown(i + 1), stagger * (i + 1)));
    return () => timers.forEach(window.clearTimeout);
  }, [gates, stagger]);

  const done = shown >= gates.length;

  return (
    <section className="surface-card overflow-hidden">
      <button
        type="button"
        onClick={() => collapsible && setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left transition-colors duration-200 hover:bg-secondary/60"
      >
        <div>
          <h3 className="font-display text-sm font-semibold">Guardrail gates</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {done ? `${gates.length} of ${gates.length} evaluated` : `Evaluating ${shown}/${gates.length}…`}
          </p>
        </div>
        {collapsible ? (
          <ChevronDown
            className="size-4 shrink-0 text-muted-foreground transition-transform duration-300"
            style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
          />
        ) : null}
      </button>

      {open ? (
        <ul className="border-t border-border px-6 py-2">
          {gates.map((g, i) => {
            const visible = i < shown;
            const Icon = ICON[g.status];
            return (
              <li
                key={g.id}
                className="flex items-start gap-3 border-b border-border py-3 last:border-b-0 transition-all duration-300"
                style={{
                  opacity: visible ? 1 : 0,
                  transform: visible ? "translateY(0)" : "translateY(6px)",
                }}
              >
                <span
                  className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-md"
                  style={{
                    backgroundColor: `color-mix(in oklab, ${TONE[g.status]} 18%, transparent)`,
                    color: TONE[g.status],
                  }}
                >
                  {visible ? <Icon className="size-3.5" /> : null}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{g.label}</p>
                  <p className="mt-0.5 font-mono text-xs text-muted-foreground">{g.detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
