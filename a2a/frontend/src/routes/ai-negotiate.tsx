import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, Send } from "lucide-react";

export const Route = createFileRoute("/ai-negotiate")({
  component: AINegotiatePage,
});

function AINegotiatePage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  async function send() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("http://localhost:8001/api/v1/negotiate/from-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Request failed");
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-14 sm:px-6">
      <header className="animate-rise">
        <h1 className="flex items-center gap-2 text-3xl font-semibold">
          <Sparkles className="size-7 text-primary" />
          AI Buyer Agent
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Describe what you need in plain language. An AI parses your intent, then negotiates
          with the merchant engine on your behalf.
        </p>
      </header>

      <div className="surface-card mt-8 p-6">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder='e.g. "I need 20 water bottles, budget around ₹18,500, need it in 5 days"'
          rows={3}
          className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm outline-none focus:border-primary"
        />
        <button
          onClick={send}
          disabled={loading || !message.trim()}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground disabled:opacity-60"
        >
          <Send className="size-4" />
          {loading ? "Negotiating…" : "Send to AI Buyer Agent"}
        </button>
      </div>

      {error ? (
        <div className="surface-card mt-6 p-6 text-sm text-destructive">{error}</div>
      ) : null}

      {result ? (
        <div className="mt-6 space-y-4">
          <div className="surface-card p-6">
            <h3 className="text-sm font-semibold text-muted-foreground">AI understood your request as:</h3>
            <pre className="mt-2 overflow-x-auto rounded-lg bg-secondary p-4 text-xs">
              {JSON.stringify(result.ai_parsed_intent, null, 2)}
            </pre>
          </div>

          <div
            className={`surface-card p-6 ${result.outcome === "DEAL" ? "border-green-500/40" : "border-red-500/40"}`}
          >
            <h2 className="text-xl font-semibold" style={{ color: result.outcome === "DEAL" ? "var(--color-success)" : "var(--color-destructive)" }}>
              {result.outcome === "DEAL" ? "Deal Reached!" : "No Agreement"}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">{result.reason || ""}</p>
            <p className="mt-2 text-xs text-muted-foreground">{result.total_rounds} round(s) negotiated</p>

            {result.outcome === "DEAL" && result.final_agreement?.payment_link ? (
              <a
                href={result.final_agreement.payment_link}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground"
              >
                Pay ₹{result.final_agreement.total_price}
              </a>
            ) : null}
          </div>

          <div className="surface-card p-6">
            <h3 className="text-sm font-semibold">Negotiation transcript</h3>
            <div className="mt-3 space-y-2 font-mono text-xs">
              {result.transcript.map((t: any, i: number) => (
                <div key={i} className="rounded bg-secondary p-2">
                  {t.actor === "merchant"
                    ? `Round ${t.round} · Merchant: ${t.response.status} at ₹${t.response.unit_price}/unit`
                    : `Round ${t.round} · Buyer: ${t.move} — ${t.reason}`}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}