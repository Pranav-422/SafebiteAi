"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { analyzeText, AgeGroup } from "@/lib/api";

const AGE_GROUPS: { value: AgeGroup; label: string; icon: string; sub: string }[] = [
  { value: "child",  label: "Child",  icon: "child_care", sub: "Under 12" },
  { value: "teen",   label: "Teen",   icon: "school",     sub: "12 – 17"  },
  { value: "adult",  label: "Adult",  icon: "person",     sub: "18 – 59"  },
  { value: "senior", label: "Senior", icon: "elderly",    sub: "60 +"     },
];

type Restriction =
  | "diabetic"
  | "hypertension"
  | "vegan"
  | "vegetarian"
  | "nut_allergy"
  | "lactose_intolerant"
  | "gluten_intolerant";

const RESTRICTIONS: { key: Restriction; label: string; icon: string; color: string }[] = [
  { key: "diabetic",           label: "Diabetic",          icon: "glucose",          color: "text-amber-600"   },
  { key: "hypertension",       label: "Hypertension",      icon: "favorite",         color: "text-red-500"     },
  { key: "vegan",              label: "Vegan",             icon: "eco",              color: "text-emerald-600" },
  { key: "vegetarian",         label: "Vegetarian",        icon: "grass",            color: "text-green-500"   },
  { key: "nut_allergy",        label: "Nut Allergy",       icon: "dangerous",        color: "text-orange-500"  },
  { key: "lactose_intolerant", label: "Lactose Intolerant",icon: "no_drinks",        color: "text-sky-600"     },
  { key: "gluten_intolerant",  label: "Gluten Intolerant", icon: "do_not_disturb_on",color: "text-rose-500"    },
];

const EXAMPLE_TEXT =
  "Water, Sugar, Enriched Flour (Wheat Flour, Niacin, Reduced Iron, Thiamine Mononitrate, Riboflavin, Folic Acid), Palm Oil, Cocoa Powder, Salt, Soy Lecithin, Artificial Flavors, Sodium Benzoate.";

export default function AnalyzePage() {
  const router = useRouter();

  const [text, setText]               = useState("");
  const [ageGroup, setAgeGroup]       = useState<AgeGroup>("adult");
  const [active, setActive]           = useState<Set<Restriction>>(new Set());
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState<string | null>(null);

  const toggleRestriction = (key: Restriction) => {
    setActive(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const handleSubmit = async () => {
    const trimmed = text.trim();
    if (!trimmed) { setError("Please paste or type the ingredient list first."); return; }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeText(trimmed, ageGroup, undefined, Array.from(active));
      sessionStorage.setItem("safebite_result", JSON.stringify(result));
      router.push("/report");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-forest-gradient fade-in">
      <Navbar />

      <main className="pt-28 pb-24 px-6 max-w-2xl mx-auto">
        {/* Header */}
        <header className="text-center mb-12 space-y-3">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-container/40 text-forest text-xs font-bold uppercase tracking-[0.15em] mb-2">
            <span className="material-symbols-outlined text-sm">edit_note</span>
            Manual Entry
          </div>
          <h1 className="font-headline text-4xl md:text-5xl text-on-surface">
            Enter <span className="text-forest italic">Ingredients</span>
          </h1>
          <p className="text-on-surface-variant text-base max-w-sm mx-auto font-body">
            Paste or type the ingredient list directly from any food package.
          </p>
        </header>

        {/* Textarea */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="font-body font-bold text-on-surface text-base flex items-center gap-2">
              <span className="material-symbols-outlined text-forest text-lg">list_alt</span>
              Ingredient List
            </label>
            <button
              onClick={() => { setText(EXAMPLE_TEXT); setError(null); }}
              className="text-xs text-forest font-bold hover:underline flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-sm">auto_fix_high</span>
              Use Example
            </button>
          </div>
          <div className="relative">
            <textarea
              value={text}
              onChange={e => { setText(e.target.value); setError(null); }}
              placeholder={`e.g. ${EXAMPLE_TEXT}`}
              rows={6}
              className="w-full resize-none rounded-xl border-2 border-outline-variant/40 bg-white px-5 py-4 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-forest focus:ring-1 focus:ring-forest/20 transition-all custom-shadow font-body leading-relaxed"
            />
            {text && (
              <button
                onClick={() => setText("")}
                className="absolute top-3 right-3 w-7 h-7 rounded-full bg-ivory-warm flex items-center justify-center text-on-surface-variant hover:bg-error-container hover:text-on-error-container transition-colors"
              >
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            )}
          </div>
          <p className="text-xs text-on-surface-variant pl-1 font-body">
            {text.trim().split(/[,\n]+/).filter(Boolean).length} items detected
          </p>
        </section>

        {/* Age Group */}
        <section className="mt-10 space-y-3">
          <h2 className="font-body font-bold text-on-surface text-base flex items-center gap-2">
            <span className="material-symbols-outlined text-forest text-lg">person</span>
            Who is eating this?
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {AGE_GROUPS.map(({ value, label, icon, sub }) => {
              const selected = ageGroup === value;
              return (
                <button
                  key={value}
                  onClick={() => setAgeGroup(value)}
                  className={`flex flex-col items-center gap-1.5 py-4 px-2 rounded-xl border-2 transition-all duration-200 font-body font-bold text-sm
                    ${selected
                      ? "border-forest bg-forest text-white shadow-forest"
                      : "border-outline-variant/40 bg-white text-on-surface hover:border-forest/40"
                    }`}
                >
                  <span className={`material-symbols-outlined text-2xl ${selected ? "text-white" : "text-forest"}`} style={{ fontVariationSettings: "'FILL' 1" }}>
                    {icon}
                  </span>
                  <span>{label}</span>
                  <span className={`text-[10px] font-medium ${selected ? "text-white/70" : "text-on-surface-variant"}`}>{sub}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Health Restrictions */}
        <section className="mt-10 space-y-3">
          <h2 className="font-body font-bold text-on-surface text-base flex items-center gap-2">
            <span className="material-symbols-outlined text-forest text-lg">health_and_safety</span>
            Health Restrictions
            <span className="text-xs font-medium text-on-surface-variant">(optional)</span>
          </h2>
          <div className="flex flex-wrap gap-2.5">
            {RESTRICTIONS.map(({ key, label, icon, color }) => {
              const on = active.has(key);
              return (
                <button
                  key={key}
                  onClick={() => toggleRestriction(key)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full border-2 text-sm font-bold transition-all duration-200
                    ${on
                      ? "border-forest bg-forest text-white shadow-forest"
                      : "border-outline-variant/40 bg-white text-on-surface hover:border-forest/40"
                    }`}
                >
                  <span
                    className={`material-symbols-outlined text-base ${on ? "text-white" : color}`}
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    {icon}
                  </span>
                  {label}
                  {on && (
                    <span className="material-symbols-outlined text-xs text-white">check</span>
                  )}
                </button>
              );
            })}
          </div>
          {active.size > 0 && (
            <p className="text-xs text-forest font-semibold pl-1">
              {active.size} restriction{active.size > 1 ? "s" : ""} active — analysis will flag relevant ingredients
            </p>
          )}
        </section>

        {/* Error */}
        {error && (
          <div className="mt-6 flex items-center gap-3 px-4 py-3 rounded-xl bg-error-container/40 border border-error/20 text-error text-sm font-medium">
            <span className="material-symbols-outlined text-lg">error</span>
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || loading}
          className="mt-8 w-full py-4 rounded-xl gradient-bg text-on-primary font-bold text-lg shadow-forest hover:shadow-forest-lg active:scale-[0.99] transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3"
        >
          {loading ? (
            <>
              <svg className="animate-spin w-5 h-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Analysing…
            </>
          ) : (
            <>
              <span className="material-symbols-outlined">biotech</span>
              Analyse Ingredients
            </>
          )}
        </button>

        {/* Scan alternative */}
        <p className="text-center text-on-surface-variant text-sm mt-6 font-body">
          Have a photo?{" "}
          <a href="/scan" className="text-forest font-bold hover:underline">Scan the label instead →</a>
        </p>
      </main>
    </div>
  );
}
