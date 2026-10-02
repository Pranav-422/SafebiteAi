"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { getProducts, analyzeProduct, Product, AgeGroup } from "@/lib/api";

const CATEGORIES = ["All", "beverage", "snack", "candy", "meal", "breakfast", "dairy"];
const AGE_GROUPS: { value: AgeGroup; icon: string; label: string; sub: string }[] = [
  { value: "child", icon: "child_care", label: "Child", sub: "Ages 0-12" },
  { value: "teen", icon: "school", label: "Teen", sub: "Ages 13-19" },
  { value: "adult", icon: "person", label: "Adult", sub: "Ages 20+" },
  { value: "senior", icon: "elderly", label: "Senior", sub: "Ages 60+" },
];

export default function ProductsPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [cat, setCat] = useState("All");
  const [ageGroup, setAgeGroup] = useState<AgeGroup>("adult");
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProducts(cat === "All" ? undefined : cat)
      .then((p) => { setProducts(p); setError(null); })
      .catch((e: Error) => setError(e.message));
  }, [cat]);

  const selectedProduct = useMemo(
    () => products.find((p) => p.id === selected) ?? null,
    [products, selected]
  );

  async function handleAnalyze() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeProduct(selected, ageGroup);
      sessionStorage.setItem("safebite_result", JSON.stringify(result));
      router.push("/report");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-forest-gradient fade-in">
      <Navbar />
      <main className="pt-24 pb-24 px-6 max-w-screen-2xl mx-auto">
        <header className="mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-container/40 text-forest text-xs font-bold uppercase tracking-[0.15em] mb-3">
            <span className="material-symbols-outlined text-sm">storefront</span>
            Product Catalog
          </div>
          <h1 className="font-headline text-4xl text-on-surface mb-2">Product Catalog</h1>
          <p className="text-on-surface-variant font-body">Pick a product, choose age group, and generate a safety report.</p>
          {error && (
            <p role="alert" className="mt-4 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm font-body">{error}</p>
          )}
        </header>

        <section className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* Categories sidebar */}
          <aside className="xl:col-span-2 space-y-4">
            <div className="xl:sticky xl:top-24 forest-card p-4">
              <h2 className="font-headline text-lg mb-3 text-on-surface">Categories</h2>
              <div className="flex flex-col gap-2">
                {CATEGORIES.map((c) => (
                  <button
                    key={c}
                    onClick={() => setCat(c)}
                    className={`px-4 py-2.5 rounded-xl text-left font-semibold text-sm transition-all duration-200 ${
                      cat === c
                        ? "bg-forest text-white shadow-forest"
                        : "bg-ivory-warm/50 text-on-surface-variant hover:bg-ivory-warm hover:text-on-surface"
                    }`}
                  >
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </aside>

          {/* Product grid */}
          <div className="xl:col-span-7">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {products.map((p) => (
                <div
                  key={p.id}
                  onClick={() => setSelected(p.id)}
                  className={`group forest-card overflow-hidden flex flex-col cursor-pointer ${
                    selected === p.id ? "ring-2 ring-forest shadow-forest-lg" : ""
                  }`}
                >
                  <div className="aspect-square bg-ivory-warm flex items-center justify-center relative">
                    {p.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={p.image_url} alt={p.name} className="w-full h-full object-cover" />
                    ) : (
                      <span className="material-symbols-outlined text-6xl text-outline-variant/40">inventory_2</span>
                    )}
                    {selected === p.id && (
                      <div className="absolute top-3 right-3 w-8 h-8 rounded-full bg-forest flex items-center justify-center shadow-forest">
                        <span className="material-symbols-outlined text-sm text-white" style={{ fontVariationSettings: "'FILL' 1" }}>
                          check
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="p-4 flex-1 flex flex-col">
                    <h4 className="font-body font-bold text-sm text-on-surface">{p.name}</h4>
                    <p className="text-xs text-on-surface-variant mt-1">{p.brand}</p>
                    <span className="mt-2 text-[10px] bg-ivory-warm px-2.5 py-0.5 rounded-full text-on-surface-variant capitalize w-fit border border-outline-variant/30">
                      {p.category}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analyze sidebar */}
          <aside className="xl:col-span-3">
            <div className="xl:sticky xl:top-24 forest-card p-5">
              <h3 className="font-headline text-lg mb-1 text-on-surface">Analyze Selection</h3>
              <p className="text-xs text-on-surface-variant mb-4 font-body">
                {selectedProduct ? `Selected: ${selectedProduct.name}` : "Select any product card to continue"}
              </p>

              <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2">Age Group</p>
              <div className="grid grid-cols-2 gap-2 mb-5">
                {AGE_GROUPS.map((a) => (
                  <button
                    key={a.value}
                    onClick={() => setAgeGroup(a.value)}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all duration-200 ${
                      ageGroup === a.value
                        ? "border-forest bg-primary-container/30 shadow-forest"
                        : "border-outline-variant/40 hover:border-forest/40 bg-white"
                    }`}
                  >
                    <span className="material-symbols-outlined text-xl text-forest" style={{ fontVariationSettings: "'FILL' 1" }}>{a.icon}</span>
                    <div className={`text-xs font-bold mt-1 ${ageGroup === a.value ? "text-forest" : "text-on-surface"}`}>{a.label}</div>
                    <div className={`text-[10px] text-center ${ageGroup === a.value ? "text-forest/70" : "text-on-surface-variant"}`}>{a.sub}</div>
                  </button>
                ))}
              </div>

              <button
                onClick={handleAnalyze}
                disabled={!selected || loading}
                className="w-full py-4 rounded-xl gradient-bg text-on-primary font-bold shadow-forest hover:shadow-forest-lg transition-all duration-300 active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="material-symbols-outlined">biotech</span>
                {loading ? "Analyzing..." : "Analyze Safety"}
              </button>
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
}
