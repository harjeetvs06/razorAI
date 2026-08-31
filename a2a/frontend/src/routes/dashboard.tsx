import { createFileRoute } from "@tanstack/react-router";
import { RotateCcw } from "lucide-react";
import { usePolicy } from "@/components/policy-provider";
import { inr } from "@/lib/razorai";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Merchant dashboard — tune your negotiation bounds | RazorAI" },
      {
        name: "description",
        content:
          "Set margin floors and discount caps per SKU and see how the negotiation state machine moves from incoming intent to signed payload.",
      },
      { property: "og:title", content: "Merchant dashboard | RazorAI" },
      {
        property: "og:description",
        content: "Tune margin floors and discount caps per SKU, live.",
      },
    ],
  }),
  component: Dashboard,
});

const MACHINE = [
  { id: "INCOMING_INTENT", d: "Signed buyer payload received" },
  { id: "EVALUATE", d: "Catalog, stock and SLA resolved" },
  { id: "GUARDRAILS", d: "Five gates run in fixed order" },
  { id: "ACCEPT / COUNTER", d: "Price settled inside the band" },
  { id: "PAYMENT LINK", d: "Razorpay link issued on accept" },
  { id: "PAYLOAD", d: "Verdict + reasoning signed and returned" },
];

function Dashboard() {
  const { products, update, reset } = usePolicy();

  return (
    <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <header className="animate-rise flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Merchant dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            These two numbers per SKU are the entire authority you hand to the engine. Change them
            and the next negotiation obeys immediately.
          </p>
        </div>
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium transition-colors duration-200 hover:bg-secondary"
        >
          <RotateCcw className="size-4" /> Reset policy
        </button>
      </header>

      <section className="mt-10">
        <h2 className="font-display text-sm font-semibold">Negotiation state machine</h2>
        <ol className="mt-4 grid gap-3 md:grid-cols-6">
          {MACHINE.map((s, i) => (
            <li
              key={s.id}
              className="surface-card animate-rise relative p-4"
              style={{ animationDelay: `${i * 70}ms` }}
            >
              <span className="font-mono text-[11px] text-primary">0{i + 1}</span>
              <p className="mt-1 font-display text-xs font-semibold leading-snug">{s.id}</p>
              <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">{s.d}</p>
              {i < MACHINE.length - 1 ? (
                <span className="absolute right-[-10px] top-1/2 hidden h-px w-4 -translate-y-1/2 bg-border md:block" />
              ) : null}
            </li>
          ))}
        </ol>
      </section>

      <section className="surface-card mt-10 overflow-hidden">
        <div className="border-b border-border px-6 py-4">
          <h2 className="font-display text-sm font-semibold">SKU policy</h2>
        </div>
        <div className="divide-y divide-border">
          {products.map((p) => {
            const unitCost = p.basePrice * p.costRatio;
            const marginFloorPrice = unitCost / (1 - p.marginFloor / 100);
            const capFloorPrice = p.basePrice * (1 - p.discountCap / 100);
            const floor = Math.max(marginFloorPrice, capFloorPrice);
            const binding = marginFloorPrice >= capFloorPrice ? "margin floor" : "discount cap";

            return (
              <div key={p.sku} className="grid gap-6 px-6 py-5 lg:grid-cols-[1.2fr_1fr_1fr_auto] lg:items-center">
                <div>
                  <p className="text-sm font-medium">{p.name}</p>
                  <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                    {p.sku} · list {inr(p.basePrice)} · cost {inr(unitCost)}
                  </p>
                </div>

                <Slider
                  label="Margin floor"
                  value={p.marginFloor}
                  min={5}
                  max={45}
                  onChange={(v) => update(p.sku, { marginFloor: v })}
                />
                <Slider
                  label="Discount cap"
                  value={p.discountCap}
                  min={0}
                  max={35}
                  onChange={(v) => update(p.sku, { discountCap: v })}
                />

                <div className="lg:text-right">
                  <p className="text-[11px] text-muted-foreground">Effective floor</p>
                  <p className="font-mono text-lg font-semibold text-primary">{inr(floor)}</p>
                  <p className="text-[11px] text-muted-foreground">bound by {binding}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="font-mono text-xs font-semibold">{value}%</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-[var(--color-primary)]"
      />
    </div>
  );
}
