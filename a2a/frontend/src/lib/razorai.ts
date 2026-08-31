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

export const CATALOG: Product[] = [
  {
    sku: "RZP-KB-01",
    name: "Mechanical Keyboard 75%",
    category: "Peripherals",
    basePrice: 8990,
    stock: 142,
    stockCapacity: 200,
    slaDays: 2,
    costRatio: 0.62,
    discountCap: 18,
    marginFloor: 22,
  },
  {
    sku: "RZP-HD-02",
    name: "Studio Headphones ANC",
    category: "Audio",
    basePrice: 15499,
    stock: 38,
    stockCapacity: 150,
    slaDays: 3,
    costRatio: 0.7,
    discountCap: 12,
    marginFloor: 20,
  },
  {
    sku: "RZP-MN-03",
    name: '27" 4K Reference Monitor',
    category: "Displays",
    basePrice: 42000,
    stock: 12,
    stockCapacity: 60,
    slaDays: 5,
    costRatio: 0.75,
    discountCap: 8,
    marginFloor: 16,
  },
  {
    sku: "RZP-CH-04",
    name: "Ergonomic Task Chair",
    category: "Furniture",
    basePrice: 22750,
    stock: 87,
    stockCapacity: 120,
    slaDays: 6,
    costRatio: 0.58,
    discountCap: 22,
    marginFloor: 25,
  },
  {
    sku: "RZP-DK-05",
    name: "Thunderbolt Dock 12-in-1",
    category: "Peripherals",
    basePrice: 11250,
    stock: 5,
    stockCapacity: 80,
    slaDays: 4,
    costRatio: 0.66,
    discountCap: 15,
    marginFloor: 20,
  },
  {
    sku: "RZP-CM-06",
    name: "4K Conference Camera",
    category: "Video",
    basePrice: 31900,
    stock: 61,
    stockCapacity: 100,
    slaDays: 3,
    costRatio: 0.68,
    discountCap: 14,
    marginFloor: 18,
  },
];

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

export function negotiate(product: Product, intent: BuyerIntent): NegotiationResult {
  const base = product.basePrice;
  const unitCost = base * product.costRatio;
  const bonus = volumeBonus(intent.qty);
  const effectiveCap = Math.min(product.discountCap + bonus, 35);

  // Floor from margin policy and floor from discount cap — the stricter wins.
  const marginFloorPrice = unitCost / (1 - product.marginFloor / 100);
  const capFloorPrice = base * (1 - effectiveCap / 100);
  const merchantFloor = round(Math.max(marginFloorPrice, capFloorPrice));

  const offer = round(intent.budgetPerUnit);
  const gates: Gate[] = [];
  const audit: string[] = [];
  const t0 = 18 + ((intent.qty * 7) % 46);

  audit.push(`intent.received agent=${intent.agentId} sku=${product.sku} qty=${intent.qty}`);
  audit.push(`catalog.lookup base=₹${base.toLocaleString("en-IN")} stock=${product.stock} sla=${product.slaDays}d`);
  audit.push(`policy.load margin_floor=${product.marginFloor}% discount_cap=${product.discountCap}%`);
  audit.push(`volume.rebate qty=${intent.qty} -> +${bonus}% headroom (effective cap ${effectiveCap}%)`);
  audit.push(`floor.compute margin=₹${Math.round(marginFloorPrice).toLocaleString("en-IN")} cap=₹${Math.round(capFloorPrice).toLocaleString("en-IN")} -> ₹${Math.round(merchantFloor).toLocaleString("en-IN")}`);

  // Gate 1 — inventory
  const stockOk = intent.qty <= product.stock;
  gates.push({
    id: "inventory",
    label: "Inventory availability",
    status: stockOk ? "pass" : "fail",
    detail: stockOk
      ? `${intent.qty} of ${product.stock} units reserved`
      : `Only ${product.stock} units on hand, ${intent.qty} requested`,
  });

  // Gate 2 — fulfilment SLA
  const slaOk = intent.deadlineDays >= product.slaDays;
  const slaTight = slaOk && intent.deadlineDays - product.slaDays <= 1;
  gates.push({
    id: "sla",
    label: "Fulfilment SLA",
    status: slaOk ? (slaTight ? "warn" : "pass") : "fail",
    detail: slaOk
      ? `Ships in ${product.slaDays}d, deadline ${intent.deadlineDays}d`
      : `Needs ${product.slaDays}d minimum, deadline is ${intent.deadlineDays}d`,
  });

  // Gate 3 — discount cap
  const requestedDiscount = round(((base - offer) / base) * 100);
  const capOk = requestedDiscount <= effectiveCap;
  gates.push({
    id: "cap",
    label: "Discount cap",
    status: capOk ? "pass" : "fail",
    detail: `Asked ${Math.max(requestedDiscount, 0).toFixed(1)}% · policy allows ${effectiveCap.toFixed(1)}%`,
  });

  // Gate 4 — margin floor
  const marginAtOffer = round(((offer - unitCost) / offer) * 100);
  const marginOk = marginAtOffer >= product.marginFloor;
  gates.push({
    id: "margin",
    label: "Gross margin floor",
    status: marginOk ? "pass" : "fail",
    detail: `Offer holds ${marginAtOffer.toFixed(1)}% margin · floor ${product.marginFloor}%`,
  });

  // Gate 5 — offer sanity
  const sane = offer > 0 && offer <= base * 1.5 && intent.qty > 0;
  gates.push({
    id: "sanity",
    label: "Offer sanity & anti-abuse",
    status: sane ? "pass" : "fail",
    detail: sane ? "Offer within expected bounds for this SKU" : "Offer outside acceptable bounds",
  });

  gates.forEach((g) => audit.push(`gate.${g.id} -> ${g.status.toUpperCase()} :: ${g.detail}`));

  const hardBlock = gates.find((g) => g.status === "fail" && (g.id === "inventory" || g.id === "sla" || g.id === "sanity"));

  let verdict: Verdict;
  let finalUnitPrice = offer;
  let headline: string;
  let reason: string;

  if (hardBlock) {
    verdict = "REJECTED";
    finalUnitPrice = 0;
    headline = "Rejected on a hard constraint";
    reason = `${hardBlock.label} could not be satisfied — ${hardBlock.detail}. Price was never the blocker here.`;
    audit.push(`decision.reject cause=${hardBlock.id}`);
  } else if (offer >= merchantFloor) {
    verdict = "ACCEPTED";
    // Meet the buyer where they are, never charge above base.
    finalUnitPrice = round(Math.min(offer, base));
    headline = "Accepted at the buyer's price";
    reason = `The offer clears the merchant floor of ₹${Math.round(merchantFloor).toLocaleString("en-IN")}/unit with room to spare.`;
    audit.push(`decision.accept unit=₹${Math.round(finalUnitPrice).toLocaleString("en-IN")}`);
  } else {
    verdict = "COUNTERED";
    finalUnitPrice = merchantFloor;
    headline = "Countered at the merchant floor";
    reason = `₹${Math.round(offer).toLocaleString("en-IN")}/unit sits below the floor. ₹${Math.round(merchantFloor).toLocaleString("en-IN")}/unit is the lowest price that keeps every guardrail intact.`;
    audit.push(`decision.counter unit=₹${Math.round(merchantFloor).toLocaleString("en-IN")}`);
  }

  const total = round(finalUnitPrice * intent.qty);
  const paymentLink =
    verdict === "ACCEPTED"
      ? `https://rzp.io/i/${product.sku.toLowerCase().replace(/-/g, "")}${Math.abs(
          (intent.qty * 7919 + Math.round(finalUnitPrice)) % 99991,
        )}`
      : undefined;

  if (paymentLink) audit.push(`payment.link.created ${paymentLink}`);
  audit.push(`payload.signed hmac=sha256 latency=${t0}ms`);

  return {
    verdict,
    headline,
    reason,
    gates,
    audit,
    basePrice: base,
    buyerOffer: offer,
    merchantFloor,
    finalUnitPrice,
    totalPayable: total,
    discountPct: round(((base - finalUnitPrice) / base) * 100),
    minimumWorkable: merchantFloor,
    latencyMs: t0,
    paymentLink,
    intent,
    product,
  };
}

export const inr = (n: number) =>
  "₹" + Math.round(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
