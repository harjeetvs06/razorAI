import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { CATALOG, type Product } from "@/lib/razorai";

type PolicyPatch = { marginFloor: number; discountCap: number };

const PolicyContext = createContext<{
  products: Product[];
  update: (sku: string, patch: Partial<PolicyPatch>) => void;
  reset: () => void;
}>({ products: CATALOG, update: () => {}, reset: () => {} });

export function PolicyProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<Product[]>(CATALOG);

  const value = useMemo(
    () => ({
      products,
      update: (sku: string, patch: Partial<PolicyPatch>) =>
        setProducts((prev) => prev.map((p) => (p.sku === sku ? { ...p, ...patch } : p))),
      reset: () => setProducts(CATALOG),
    }),
    [products],
  );

  return <PolicyContext.Provider value={value}>{children}</PolicyContext.Provider>;
}

export const usePolicy = () => useContext(PolicyContext);
