export type Product = {
  sku: string;
  name: string;
  category: string;
  basePrice: number;
  stock: number;
  stockCapacity: number;
  slaDays: number;
  /** Percent of base price that is unit cost — sets the true margin floor. */
  costRatio: number;
  /** Max discount the merchant policy will ever allow, in percent. */
  discountCap: number;
  /** Minimum gross margin percent the merchant must retain. */
  marginFloor: number;
};

export async function fetchCatalog(): Promise<Product[]> {
  const res = await fetch("http://localhost:8001/api/v1/negotiate/catalog");
  if (!res.ok) throw new Error(`Catalog fetch failed: ${res.status}`);
  const raw: {
    sku: string;
    name: string;
    base_price: number;
    stock: number;
    category: string;
    shipping_sla_days: number;
    image_key: string;
  }[] = await res.json();

  // Map backend field names -> frontend Product shape.
  // Backend doesn't expose costRatio/discountCap/marginFloor (merchant-private policy),
  // so we use safe placeholder values for display only — the REAL numbers are
  // enforced server-side and returned per-negotiation as `effective_floor`.
  return raw.map((item) => ({
    sku: item.sku,
    name: item.name,
    category: item.category,
    basePrice: item.base_price,
    stock: item.stock,
    stockCapacity: item.stock,
    slaDays: item.shipping_sla_days,
    costRatio: 0,
    discountCap: 0,
    marginFloor: 0,
  }));
}

export type BuyerIntent = {
  sku: string;
  qty: number;
  budgetPerUnit: number;
  deadlineDays: number;
  agentId: string;
};

export type GateStatus = "pass" | "fail" | "warn";

export type Gate = {
  id: string;
  label: string;
  status: GateStatus;
  detail: string;
};

export type Verdict = "ACCEPTED" | "COUNTERED" | "REJECTED";

export type NegotiationResult = {
  verdict: Verdict;
  headline: string;
  reason: string;
  gates: Gate[];
  audit: string[];
  basePrice: number;
  buyerOffer: number;
  merchantFloor: number;
  finalUnitPrice: number;
  totalPayable: number;
  discountPct: number;
  minimumWorkable: number;
  latencyMs: number;
  paymentLink?: string;
  intent: BuyerIntent;
  product: Product;
};

const round = (n: number) => Math.round(n * 100) / 100;

/** Volume rebate: bigger orders unlock a little more room, capped. */
export function volumeBonus(qty: number) {
  if (qty >= 100) return 6;
  if (qty >= 50) return 4;
  if (qty >= 20) return 2.5;
  if (qty >= 5) return 1;
  return 0;
}

export async function negotiate(product: Product, intent: BuyerIntent): Promise<NegotiationResult> {
  const t0 = performance.now();

  // Call the multi-round A2A endpoint
  const res = await fetch("http://localhost:8001/api/v1/negotiate/auto", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sku: product.sku,
      quantity: intent.qty,
      budget_total: intent.budgetPerUnit * intent.qty,
      delivery_deadline_days: intent.deadlineDays,
      buyer_agent_id: intent.agentId,
    }),
  });

  if (!res.ok) {
    throw new Error(`Negotiation failed: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();
  const latencyMs = Math.round(performance.now() - t0);

  // Map the multi-round response back to NegotiationResult shape for rendering
  const finalAgreement = data.final_agreement || data.transcript[data.transcript.length - 2]; // last merchant response
  
  const verdict: Verdict = data.outcome === "DEAL" ? "ACCEPTED" : "REJECTED";
  
  const transcript = data.transcript.map((t: any, i: number) => 
    t.actor === "merchant" 
      ? `Round ${t.round}: Merchant ${t.response.status} at ₹${t.response.unit_price}/unit`
      : `Round ${t.round}: Buyer ${t.move} — ${t.reason}`
  );

  return {
    verdict,
    headline: data.outcome === "DEAL" ? "Deal Reached!" : "No Agreement",
    reason: data.reason || finalAgreement?.explanation || "",
    gates: (finalAgreement?.gates_checked || []).map((g: string, i: number) => ({
      id: `gate-${i}`,
      label: g.replace(/^[✓✗]\s*/, "").split(":")[0] ?? "",
      status: g.startsWith("✓") ? "pass" : g.startsWith("✗") ? "fail" : "warn",
      detail: g.replace(/^[✓✗]\s*/, ""),
    })),
    audit: transcript,
    basePrice: finalAgreement?.base_price || product.basePrice,
    buyerOffer: intent.budgetPerUnit,
    merchantFloor: finalAgreement?.effective_floor || 0,
    finalUnitPrice: finalAgreement?.unit_price || 0,
    totalPayable: finalAgreement?.total_price || 0,
    discountPct: finalAgreement?.discount_pct || 0,
    minimumWorkable: 0,
    latencyMs,
    paymentLink: finalAgreement?.payment_link || "",
    intent,
    product,
  };
}
export const inr = (n: number) =>
  "₹" + Math.round(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
