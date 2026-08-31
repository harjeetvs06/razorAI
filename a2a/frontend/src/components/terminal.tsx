import { useEffect, useState } from "react";

/** Terminal panel that types out lines one at a time. */
export function Terminal({
  lines,
  title = "audit-trail",
  speed = 220,
  loop = false,
  className = "",
}: {
  lines: string[];
  title?: string;
  speed?: number;
  loop?: boolean;
  className?: string;
}) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(0);
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      if (i > lines.length) {
        if (loop) {
          i = 0;
          setCount(0);
          return;
        }
        window.clearInterval(id);
        return;
      }
      setCount(i);
    }, speed);
    return () => window.clearInterval(id);
  }, [lines, speed, loop]);

  return (
    <div
      className={`overflow-hidden rounded-xl border border-border ${className}`}
      style={{ backgroundColor: "var(--color-terminal)", color: "var(--color-terminal-foreground)" }}
    >
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5">
        <span className="size-2.5 rounded-full bg-destructive/70" />
        <span className="size-2.5 rounded-full bg-warning/70" />
        <span className="size-2.5 rounded-full bg-success/70" />
        <span className="ml-2 font-mono text-xs text-white/50">{title}</span>
      </div>
      <div className="min-h-40 space-y-1 overflow-x-auto p-4 font-mono text-xs leading-relaxed">
        {lines.slice(0, count).map((l, i) => (
          <div key={`${i}-${l}`} className="animate-rise whitespace-pre">
            <span className="mr-2 select-none text-primary">›</span>
            <span className={i === count - 1 ? "caret" : ""}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
