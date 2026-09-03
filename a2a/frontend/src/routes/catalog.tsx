import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Truck } from "lucide-react";
import { usePolicy } from "@/components/policy-provider";
import { inr } from "@/lib/razorai";

export const Route = createFileRoute("/catalog")({
  head: () => ({
    meta: [
      { title: "Catalog — negotiable SKUs | RazorAI" },
      {
        name: "description",
        content:
          "Every SKU in the RazorAI catalog is negotiable within merchant-set bounds. Stock levels, shipping SLA and list price at a glance.",
      },
      { property: "og:title", content: "Catalog — negotiable SKUs | RazorAI" },
      {
        property: "og:description",
        content: "Browse negotiable SKUs with live stock, SLA and list price.",
      },
    ],
  }),
  component: Catalog,
});

function Catalog() {
  const { products, loading, error } = usePolicy();

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6 text-center">
        <p className="text-sm text-muted-foreground">Loading catalog…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6 text-center">
        <p className="text-sm text-destructive">Couldn't load catalog: {error}</p>
        <p className="mt-2 text-xs text-muted-foreground">Is the backend running on http://localhost:8001?</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <header className="animate-rise">
        <h1 className="text-3xl font-semibold">Catalog</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Every SKU carries its own negotiation band. Hover a card to open a session with the
          merchant engine.
        </p>
      </header>

      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((p, i) => {
          const stockPct = Math.round((p.stock / p.stockCapacity) * 100);
          const low = p.stock <= 15;
          return (
            <Link
              key={p.sku}
              to="/negotiate"
              search={{ sku: p.sku }}
              className="surface-card group animate-rise flex flex-col p-6 hover:-translate-y-1"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="rounded-md bg-secondary px-2 py-1 text-[11px] font-medium text-muted-foreground">
                  {p.category}
                </span>
                <span className="font-mono text-[11px] text-muted-foreground">{p.sku}</span>
              </div>

              <h2 className="mt-4 font-display text-lg font-semibold leading-snug">{p.name}</h2>

              <p className="mt-3 font-mono text-2xl font-semibold text-primary">{inr(p.basePrice)}</p>
              <p className="text-xs text-muted-foreground">list price · per unit</p>

              <div className="mt-5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Stock</span>
                  <span
                    className="font-mono"
                    style={{ color: low ? "var(--color-warning)" : "var(--color-foreground)" }}
                  >
                    {p.stock} / {p.stockCapacity}
                  </span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-md bg-secondary">
                  <div
                    className="h-full rounded-md transition-all duration-700"
                    style={{
                      width: `${stockPct}%`,
                      backgroundColor: low ? "var(--color-warning)" : "var(--color-primary)",
                    }}
                  />
                </div>
              </div>

              <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                <Truck className="size-3.5" />
                Ships in {p.slaDays} day{p.slaDays > 1 ? "s" : ""}
              </div>

              <div className="mt-5 flex items-center gap-1.5 text-sm font-medium text-primary opacity-0 transition-all duration-200 group-hover:opacity-100 group-focus-visible:opacity-100">
                Negotiate <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-1" />
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
