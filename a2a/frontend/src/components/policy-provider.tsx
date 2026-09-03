import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchCatalog, type Product } from "@/lib/razorai";

type PolicyPatch = { marginFloor: number; discountCap: number };

const PolicyContext = createContext<{
  products: Product[];
  loading: boolean;
  error: string | null;
  update: (sku: string, patch: Partial<PolicyPatch>) => void;
  reset: () => void;
}>({ products: [], loading: true, error: null, update: () => {}, reset: () => {} });

export function PolicyProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [original, setOriginal] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchCatalog()
      .then((items) => {
        if (cancelled) return;
        setProducts(items);
        setOriginal(items);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Failed to load catalog:", err);
        setError(err instanceof Error ? err.message : "Failed to load catalog. Is the backend running?");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      products,
      loading,
      error,
      update: (sku: string, patch: Partial<PolicyPatch>) =>
        setProducts((prev) => prev.map((p) => (p.sku === sku ? { ...p, ...patch } : p))),
      reset: () => setProducts(original),
    }),
    [products, loading, error, original],
  );

  return <PolicyContext.Provider value={value}>{children}</PolicyContext.Provider>;
}

export const usePolicy = () => useContext(PolicyContext);