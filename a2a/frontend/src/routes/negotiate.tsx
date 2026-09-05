import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Copy, Handshake, Send, TriangleAlert, X } from "lucide-react";
import { usePolicy } from "@/components/policy-provider";
import { GateList } from "@/components/gate-list";
import { Terminal } from "@/components/terminal";
import { TugOfWar } from "@/components/tug-of-war";
import { inr, negotiate, volumeBonus, type NegotiationResult } from "@/lib/razorai";

export const Route = createFileRoute("/negotiate")({
  validateSearch: (s: Record<string, unknown>) => ({
    sku: typeof s["sku"] === "string" ? s["sku"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Negotiation builder — compose a buyer intent | RazorAI" },
      {
        name: "description",
        content:
          "Compose a buyer-agent intent, watch the request travel to the merchant engine, and read the verdict with every guardrail gate explained.",
      },
      { property: "og:title", content: "Negotiation builder | RazorAI" },
      {
        property: "og:description",
        content: "Compose an intent and watch the merchant engine decide, gate by gate.",
      },
    ],
  }),
  component: NegotiatePage,
});

type Phase = "idle" | "sending" | "result" | "error";

function NegotiatePage() {


  const { sku } = Route.useSearch();
  const { products ,loading,error} = usePolicy();

  if (loading) return <main className="mx-auto max-w-6xl px-4 py-14 text-center text-sm text-muted-foreground">Loading catalog…</main>;
  if (error || products.length === 0) return <main className="mx-auto max-w-6xl px-4 py-14 text-center text-sm text-destructive">Couldn't load catalog. Is the backend running on :8001?</main>;


  const [errorMessage, setErrorMessage] = useState<string>("");
  const [selected, setSelected] = useState(sku ?? products[0]!.sku);
  const product = products.find((p) => p.sku === selected) ?? products[0]!;

  const [qty, setQty] = useState(40);
  const [budget, setBudget] = useState(() => Math.round(products[0]!.basePrice * 0.85));
  const [deadline, setDeadline] = useState(7);
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<NegotiationResult | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setBudget(Math.round(product.basePrice * 0.85));
    setPhase("idle");
    setResult(null);
  }, [product.sku, product.basePrice]);

  const intent = useMemo(
    () => ({ sku: product.sku, qty, budgetPerUnit: budget, deadlineDays: deadline, agentId: "buyer-agent://acme.procurement" }),
    [product.sku, qty, budget, deadline],
  );


  const requestJson = JSON.stringify(
    {
      protocol: "a2a/negotiate.v1",
      agent: intent.agentId,
      intent: {
        sku: intent.sku,
        qty: intent.qty,
        budget_per_unit: intent.budgetPerUnit,
        total_budget: intent.budgetPerUnit * intent.qty,
        deadline_days: intent.deadlineDays,
      },
      constraints: { currency: "INR", settlement: "razorpay_payment_link" },
      meta: { volume_rebate_pct: volumeBonus(intent.qty) },
    },
    null,
    2,
  );

  async function send() {
    setPhase("sending");
    setResult(null);
    setErrorMessage("");
    try {
      const computed = await negotiate(product, intent);
      setResult(computed);
      setPhase("result");
      window.setTimeout(
        () => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
        60,
      );
    } catch (err) {
      console.error("Negotiation failed:", err);
      setErrorMessage(err instanceof Error ? err.message : "Negotiation failed. Is the backend running?");
      setPhase("error");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <header className="animate-rise">
        <h1 className="text-3xl font-semibold">Negotiation builder</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Left: what your buyer agent wants. Right: the exact payload it will speak. Nothing is
          translated behind your back.
        </p>
      </header>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        {/* Buyer inputs */}
        <section className="surface-card animate-rise p-6">
          <h2 className="font-display text-sm font-semibold">Buyer agent</h2>

          <label className="mt-6 block text-xs font-medium text-muted-foreground">SKU</label>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            className="mt-2 w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition-colors duration-200 focus:border-primary"
          >
            {products.map((p) => (
              <option key={p.sku} value={p.sku}>
                {p.name} — {inr(p.basePrice)}
              </option>
            ))}
          </select>

          <Field label="Quantity" hint={`${product.stock} in stock · rebate +${volumeBonus(qty)}%`}>
            <input
              type="range"
              min={1}
              max={product.stockCapacity}
              value={qty}
              onChange={(e) => setQty(Number(e.target.value))}
              className="w-full accent-[var(--color-primary)]"
            />
            <output className="font-mono text-sm font-semibold">{qty} units</output>
          </Field>

          <Field label="Budget per unit" hint={`List ${inr(product.basePrice)}`}>
            <input
              type="range"
              min={Math.round(product.basePrice * 0.5)}
              max={product.basePrice}
              step={10}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="w-full accent-[var(--color-primary)]"
            />
            <output className="font-mono text-sm font-semibold text-primary">{inr(budget)}</output>
          </Field>

          <Field label="Deadline" hint={`Merchant SLA ${product.slaDays}d`}>
            <input
              type="range"
              min={1}
              max={21}
              value={deadline}
              onChange={(e) => setDeadline(Number(e.target.value))}
              className="w-full accent-[var(--color-primary)]"
            />
            <output className="font-mono text-sm font-semibold">{deadline} days</output>
          </Field>

          <div className="mt-6 rounded-lg bg-secondary px-4 py-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Total budget</span>
              <span className="font-mono font-semibold">{inr(budget * qty)}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={send}
            disabled={phase === "sending"}
            className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-all duration-200 hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0"
          >
            <Send className="size-4" />
            {phase === "sending" ? "Negotiating…" : "Send intent to merchant engine"}
          </button>

          {/* request travelling animation */}
          <div className="relative mt-5 h-8">
            <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border" />
            <div className="absolute inset-y-0 left-0 flex items-center bg-surface pr-2 text-[11px] text-muted-foreground">
              buyer
            </div>
            <div className="absolute inset-y-0 right-0 flex items-center bg-surface pl-2 text-[11px] text-muted-foreground">
              merchant
            </div>
            {phase === "sending" ? (
              <span
                className="absolute top-1/2 size-2.5 -translate-y-1/2 rounded-full bg-primary"
                style={{ animation: "ra-travel 1100ms ease-in-out forwards" }}
              />
            ) : null}
          </div>
        </section>

        {/* Live payload */}
        <section className="animate-rise" style={{ animationDelay: "80ms" }}>
          <Terminal lines={requestJson.split("\n")} title="POST /a2a/negotiate" speed={0} />
          <p className="mt-3 text-xs text-muted-foreground">
            This payload updates as you move a slider — it is exactly what gets signed and sent.
          </p>
        </section>
      </div>

     <div ref={resultRef} className="scroll-mt-24">
    {phase === "sending" ? <SendingState /> : null}
    {phase === "result" && result ? <ResultView result={result} /> : null}
    {phase === "error" ? (
      <div className="surface-card mt-6 p-10 text-center border border-red-500/30">
        <p className="text-sm font-medium text-red-500">Negotiation failed</p>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          {errorMessage}
        </p>
        <button
          onClick={() => setPhase("idle")}
          className="mt-4 text-sm underline underline-offset-4"
        >
          Try again
        </button>
      </div>
    ) : null}
    {phase === "idle" ? (
      <div className="surface-card mt-6 p-10 text-center">
        <Handshake className="mx-auto size-6 text-muted-foreground" />
        <p className="mt-4 text-sm font-medium">No session yet</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">
          Set the terms your agent is authorised to accept, then send. You'll see the decision
          form gate by gate rather than pop out of a spinner.
        </p>
      </div>
    ) : null}
  </div>
    </main>
  );
}
  function Field({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="mt-6">
      <div className="flex items-baseline justify-between">
        <label className="text-xs font-medium text-muted-foreground">{label}</label>
        <span className="text-[11px] text-muted-foreground">{hint}</span>
      </div>
      <div className="mt-2 flex items-center gap-4">{children}</div>
    </div>
  );
}

const STEPS = [
  "Reserving inventory",
  "Checking fulfilment SLA",
  "Applying discount cap",
  "Testing margin floor",
  "Signing decision payload",
];

function SendingState() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = STEPS.map((_, i) => window.setTimeout(() => setStep(i + 1), 180 * (i + 1)));
    return () => t.forEach(window.clearTimeout);
  }, []);

  return (
    <section className="surface-card mt-6 p-6">
      <h2 className="font-display text-sm font-semibold">Merchant engine is deciding</h2>
      <ul className="mt-4 space-y-3">
        {STEPS.map((s, i) => (
          <li
            key={s}
            className="flex items-center gap-3 text-sm transition-all duration-300"
            style={{ opacity: i < step ? 1 : 0.3, transform: i < step ? "none" : "translateY(4px)" }}
          >
            <span
              className="grid size-5 place-items-center rounded-md"
              style={{
                backgroundColor: "color-mix(in oklab, var(--color-primary) 18%, transparent)",
                color: "var(--color-primary)",
              }}
            >
              {i < step ? <Check className="size-3.5" /> : null}
            </span>
            {s}
          </li>
        ))}
      </ul>
    </section>
  );
}

const VERDICT_STYLE = {
  ACCEPTED: { color: "var(--color-success)", Icon: Check, label: "Accepted" },
  COUNTERED: { color: "var(--color-warning)", Icon: TriangleAlert, label: "Countered" },
  REJECTED: { color: "var(--color-destructive)", Icon: X, label: "Rejected" },
} as const;

function ResultView({ result }: { result: NegotiationResult }) {
  const v = VERDICT_STYLE[result.verdict];
  const [copied, setCopied] = useState(false);

  return (
    <div className="mt-6 space-y-6">
      <section
        className="surface-card animate-pop p-8"
        style={{ borderColor: `color-mix(in oklab, ${v.color} 40%, transparent)` }}
      >
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-start gap-4">
            <span
              className="grid size-12 shrink-0 place-items-center rounded-xl"
              style={{ backgroundColor: `color-mix(in oklab, ${v.color} 16%, transparent)`, color: v.color }}
            >
              <v.Icon className="size-6" />
            </span>
            <div>
              <p className="font-display text-3xl font-semibold" style={{ color: v.color }}>
                {v.label}
              </p>
              <p className="mt-1 text-sm font-medium">{result.headline}</p>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
                {result.reason}
              </p>
            </div>
          </div>

          {result.verdict !== "REJECTED" ? (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Settled unit price</p>
              <p className="font-mono text-3xl font-semibold">{inr(result.finalUnitPrice)}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {result.discountPct.toFixed(1)}% off list · {result.intent.qty} units ·{" "}
                <span className="font-mono text-foreground">{inr(result.totalPayable)}</span>
              </p>
            </div>
          ) : (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Minimum that would work</p>
              <p className="font-mono text-2xl font-semibold">{inr(result.minimumWorkable)}</p>
            </div>
          )}
        </div>

        <p className="mt-6 font-mono text-xs text-muted-foreground">
          decided in {result.latencyMs}ms · {result.gates.length} gates · agent {result.intent.agentId}
        </p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <TugOfWar
          base={result.basePrice}
          offer={result.buyerOffer}
          floor={result.merchantFloor}
          {...(result.verdict !== "REJECTED" ? { settled: result.finalUnitPrice } : {})}
        />
        <GateList gates={result.gates} />
      </div>

      {result.paymentLink ? (
        <section className="surface-card animate-rise p-6">
          <h3 className="font-display text-sm font-semibold">Payment link</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Issued for {result.intent.qty} × {result.product.name} at {inr(result.finalUnitPrice)}/unit.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <code className="min-w-0 flex-1 truncate rounded-lg bg-secondary px-4 py-2.5 font-mono text-sm">
              {result.paymentLink}
            </code>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard?.writeText(result.paymentLink!);
                setCopied(true);
                window.setTimeout(() => setCopied(false), 1600);
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium transition-colors duration-200 hover:bg-secondary"
            >
              <Copy className="size-4" /> {copied ? "Copied" : "Copy"}
            </button>
            <a
              href={result.paymentLink}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-transform duration-200 hover:-translate-y-0.5"
            >
              Pay {inr(result.totalPayable)}
            </a>
          </div>
        </section>
      ) : null}

      <AuditTrail lines={result.audit} />
    </div>
  );
}

function AuditTrail({ lines }: { lines: string[] }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="surface-card overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-6 py-4 text-left transition-colors duration-200 hover:bg-secondary/60"
      >
        <div>
          <h3 className="font-display text-sm font-semibold">Full audit trail</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{lines.length} steps, replayed in order</p>
        </div>
        <ChevronDown
          className="size-4 text-muted-foreground transition-transform duration-300"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </button>
      {open ? (
        <div className="border-t border-border p-4">
          <Terminal lines={lines} speed={120} />
        </div>
      ) : null}
    </section>
  );
}
