import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Gauge, ScrollText, ShieldCheck } from "lucide-react";
import { Terminal } from "@/components/terminal";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RazorAI — Agents that negotiate your checkout price" },
      {
        name: "description",
        content:
          "Watch an AI buyer agent and a merchant engine settle on a price in milliseconds, with every guardrail and reason shown in the open.",
      },
      { property: "og:title", content: "RazorAI — Agents that negotiate your checkout price" },
      {
        property: "og:description",
        content: "Bounded, explainable agent-to-agent price negotiation for Razorpay merchants.",
      },
    ],
  }),
  component: Landing,
});

const DEMO = [
  "buyer.agent › intent { sku: RZP-KB-01, qty: 40, budget: ₹7,600 }",
  "merchant.engine › catalog.lookup base=₹8,990 stock=142 sla=2d",
  "merchant.engine › gate.inventory PASS  40/142 reserved",
  "merchant.engine › gate.sla PASS  ships in 2d",
  "merchant.engine › gate.cap PASS  asked 15.5% · allowed 21.0%",
  "merchant.engine › gate.margin FAIL  holds 26.6% · floor 22.0% ok",
  "merchant.engine › counter ₹7,146/unit — lowest price with guardrails intact",
  "buyer.agent › accept · payment link issued · payload signed",
];

const STATS = [
  { icon: Gauge, value: "38ms", label: "Median negotiation latency" },
  { icon: ShieldCheck, value: "5", label: "Guardrail gates per decision" },
  { icon: ScrollText, value: "100%", label: "Decisions with a full audit trail" },
];

function Landing() {
  return (
    <main>
      <section className="relative overflow-hidden">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-60" aria-hidden />
        <div className="relative mx-auto grid max-w-6xl gap-16 px-4 py-20 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:py-28">
          <div className="animate-rise">
            <span className="inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-muted-foreground">
              <span className="size-1.5 rounded-full bg-primary animate-pulse-ring" />
              Agent-to-Agent protocol · Razorpay
            </span>

            <h1 className="mt-6 text-4xl font-semibold leading-[1.05] sm:text-6xl">
              Checkout stops being a
              <span className="text-primary"> yes/no button</span>. It becomes a conversation.
            </h1>

            <p className="mt-6 max-w-xl text-base leading-relaxed text-muted-foreground">
              A buyer agent states qty, budget and deadline. The RazorAI merchant engine answers
              with a price it can actually defend — bounded by margin floors, discount caps and
              inventory, with every gate shown in the open.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/negotiate"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-transform duration-200 hover:-translate-y-0.5"
              >
                Run a negotiation <ArrowRight className="size-4" />
              </Link>
              <Link
                to="/catalog"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-5 py-3 text-sm font-medium transition-colors duration-200 hover:bg-secondary"
              >
                Browse catalog
              </Link>
            </div>
          </div>

          <div className="animate-rise" style={{ animationDelay: "120ms" }}>
            <Terminal lines={DEMO} title="live-negotiation.log" speed={700} loop />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="grid gap-4 sm:grid-cols-3">
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className="surface-card animate-rise p-6"
              style={{ animationDelay: `${160 + i * 80}ms` }}
            >
              <s.icon className="size-5 text-primary" />
              <p className="mt-4 font-display text-3xl font-semibold">{s.value}</p>
              <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <h2 className="text-2xl font-semibold">How a decision is made</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Nothing is hidden behind a spinner. The same five gates run on every request, in the same
          order, and the reasoning is attached to the result — accepted or not.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            {
              t: "Bounded, never blind",
              d: "The engine can only move inside a merchant-defined band: margin floor, discount cap, and a volume rebate that widens the band for large orders.",
            },
            {
              t: "A rejection is an instruction",
              d: "Every no comes with the exact number that would have been a yes, so the buyer agent can re-offer in one round instead of five.",
            },
            {
              t: "Signed, auditable payload",
              d: "Verdict, gate results and the final price are emitted as one signed payload — replayable line by line in the audit trail.",
            },
          ].map((c) => (
            <div key={c.t} className="surface-card p-6">
              <h3 className="text-sm font-semibold">{c.t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{c.d}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
