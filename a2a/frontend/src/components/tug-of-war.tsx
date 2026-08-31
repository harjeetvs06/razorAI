import { inr } from "@/lib/razorai";

/**
 * Price tug-of-war: buyer pulls from the left (low), merchant floor holds
 * from the right. The overlap or gap between the two markers is the story.
 */
export function TugOfWar({
  base,
  offer,
  floor,
  settled,
}: {
  base: number;
  offer: number;
  floor: number;
  settled?: number;
}) {
  const lo = Math.min(offer, floor) * 0.88;
  const hi = base * 1.04;
  const pos = (v: number) => Math.max(2, Math.min(98, ((v - lo) / (hi - lo)) * 100));

  const offerPos = pos(offer);
  const floorPos = pos(floor);
  const gapOk = offer >= floor;

  return (
    <div className="surface-card p-6">
      <div className="mb-8 flex items-center justify-between">
        <h3 className="font-display text-sm font-semibold">Price tug-of-war</h3>
        <span
          className="rounded-md px-2 py-1 text-xs font-medium"
          style={{
            backgroundColor: gapOk
              ? "color-mix(in oklab, var(--color-success) 16%, transparent)"
              : "color-mix(in oklab, var(--color-warning) 18%, transparent)",
            color: gapOk ? "var(--color-success)" : "var(--color-warning)",
          }}
        >
          {gapOk ? "Zone of agreement" : `Gap ${inr(floor - offer)}/unit`}
        </span>
      </div>

      <div className="relative h-3 rounded-md bg-secondary">
        {/* buyer pull */}
        <div
          className="absolute inset-y-0 left-0 rounded-l-md bg-primary/35 transition-all duration-700"
          style={{ width: `${offerPos}%` }}
        />
        {/* merchant hold */}
        <div
          className="absolute inset-y-0 right-0 rounded-r-md transition-all duration-700"
          style={{
            width: `${100 - floorPos}%`,
            backgroundColor: "color-mix(in oklab, var(--color-foreground) 18%, transparent)",
          }}
        />
        {settled ? (
          <div
            className="absolute -top-1 size-5 -translate-x-1/2 rounded-md border-2 border-background bg-primary transition-all duration-700 animate-pulse-ring"
            style={{ left: `${pos(settled)}%` }}
          />
        ) : null}

        <Marker pct={offerPos} label="Buyer offer" value={inr(offer)} tone="primary" side="down" />
        <Marker pct={floorPos} label="Merchant floor" value={inr(floor)} tone="fg" side="up" />
      </div>

      <div className="mt-10 flex items-center justify-between text-xs text-muted-foreground">
        <span>{inr(lo)}</span>
        <span>List {inr(base)}</span>
      </div>
    </div>
  );
}

function Marker({
  pct,
  label,
  value,
  tone,
  side,
}: {
  pct: number;
  label: string;
  value: string;
  tone: "primary" | "fg";
  side: "up" | "down";
}) {
  const color = tone === "primary" ? "var(--color-primary)" : "var(--color-foreground)";
  return (
    <div
      className="absolute -translate-x-1/2 transition-all duration-700"
      style={{ left: `${pct}%`, top: side === "up" ? "100%" : "auto", bottom: side === "down" ? "100%" : "auto" }}
    >
      <div className={side === "down" ? "mb-2 text-center" : "mt-2 text-center"}>
        <div className="whitespace-nowrap text-[11px] uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="whitespace-nowrap font-mono text-sm font-semibold" style={{ color }}>
          {value}
        </div>
      </div>
      <div className="mx-auto h-3 w-0.5" style={{ backgroundColor: color }} />
    </div>
  );
}
