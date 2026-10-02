"use client";

import { useMemo, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import SafetyScoreCard from "@/components/SafetyScoreCard";
import { AnalysisResult, FlaggedIngredient, Alternative } from "@/lib/api";

const RISK_CONFIG = {
  high: { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", dot: "bg-red-500", label: "High Risk" },
  medium: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-400", label: "Moderate" },
  low: { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200", dot: "bg-yellow-400", label: "Low Risk" },
  safe: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200", dot: "bg-emerald-500", label: "Safe" },
};

const subscribeNoop = () => () => {};

function DeltaBadge({ delta }: { delta: number }) {
  if (delta === 0) return null;
  const pos = delta > 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-black ${
        pos ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-600 border border-red-200"
      }`}
    >
      <span className="material-symbols-outlined text-xs">{pos ? "trending_up" : "trending_down"}</span>
      {pos ? "+" : ""}
      {delta} pts
    </span>
  );
}

function IngredientCard({ item }: { item: FlaggedIngredient }) {
  const cfg = RISK_CONFIG[item.risk_level] ?? RISK_CONFIG.safe;
  return (
    <div className={`flex flex-col gap-2 p-4 rounded-xl border forest-card ${cfg.border} fade-in`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5 ${cfg.dot}`} />
          <p className="font-body font-bold text-on-surface text-sm truncate capitalize">{item.name}</p>
        </div>
        <span className={`flex-shrink-0 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wide border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
          {cfg.label}
        </span>
      </div>

      {item.reason && <p className="text-xs text-on-surface-variant leading-relaxed pl-4">{item.reason}</p>}

      {item.age_restriction && (
        <div className="flex items-center gap-1.5 pl-4">
          <span className="material-symbols-outlined text-xs text-forest">child_care</span>
          <span className="text-[11px] text-forest font-semibold">{item.age_restriction}</span>
        </div>
      )}
    </div>
  );
}

function AlternativeCard({ alt }: { alt: Alternative }) {
  return (
    <div className="flex items-center gap-4 p-4 forest-card fade-in">
      {alt.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={alt.image_url} alt={alt.alt_name} className="w-14 h-14 rounded-xl object-cover flex-shrink-0 bg-ivory-warm" />
      ) : (
        <div className="w-14 h-14 rounded-xl gradient-bg flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-2xl text-white">grocery</span>
        </div>
      )}
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-body font-bold text-on-surface text-sm truncate">{alt.alt_name}</p>
          <DeltaBadge delta={alt.score_delta} />
        </div>
        {alt.alt_brand && <p className="text-xs text-on-surface-variant">{alt.alt_brand}</p>}
        {alt.reason && <p className="text-xs text-on-surface-variant leading-relaxed">{alt.reason}</p>}
      </div>
      <span className="material-symbols-outlined text-outline-variant text-xl flex-shrink-0">chevron_right</span>
    </div>
  );
}

export default function ReportPage() {
  const router = useRouter();
  // Read the last analysis from sessionStorage without setState-in-effect (server snapshot = not loaded yet).
  const raw = useSyncExternalStore(
    subscribeNoop,
    () => sessionStorage.getItem("safebite_result") ?? "",
    () => null
  );
  const result = useMemo<AnalysisResult | null>(() => {
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AnalysisResult;
    } catch {
      return null;
    }
  }, [raw]);
  const notFound = raw !== null && result === null;

  if (notFound) {
    return (
      <div className="min-h-screen bg-forest-gradient fade-in">
        <Navbar />
        <main className="pt-40 pb-24 px-6 flex flex-col items-center gap-6 text-center">
          <div className="w-20 h-20 rounded-2xl gradient-bg flex items-center justify-center shadow-forest">
            <span className="material-symbols-outlined text-4xl text-white">search_off</span>
          </div>
          <h1 className="font-headline text-3xl text-on-surface">No report found</h1>
          <p className="text-on-surface-variant max-w-xs font-body">It looks like you haven&apos;t scanned anything yet. Start by uploading a label.</p>
          <button
            onClick={() => router.push("/scan")}
            className="px-8 py-3 rounded-xl gradient-bg text-on-primary font-bold shadow-forest hover:shadow-forest-lg transition-all"
          >
            Scan a Label
          </button>
        </main>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-forest-gradient flex items-center justify-center">
        <svg className="animate-spin w-10 h-10 text-forest" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
      </div>
    );
  }

  const highRisk = result.flagged.filter((f) => f.risk_level === "high");
  const otherFlagged = result.flagged.filter((f) => f.risk_level !== "high");
  const scoreOutOf = result.score_out_of ?? 10;
  const confidence = result.match_confidence ?? 0;
  const confidenceLabel = confidence >= 0.7 ? "High confidence" : confidence >= 0.4 ? "Moderate confidence" : "Low confidence";

  return (
    <div className="min-h-screen bg-forest-gradient fade-in">
      <Navbar />

      <main className="pt-24 pb-24 px-6 max-w-screen-xl mx-auto grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Left sidebar */}
        <aside className="hidden xl:block xl:col-span-2">
          <div className="sticky top-28 forest-card p-4 space-y-3">
            <p className="text-xs uppercase tracking-wider font-black text-on-surface-variant">Scoring Guide</p>
            <ul className="space-y-2 text-xs text-on-surface-variant font-body">
              <li className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500" />9-10: Excellent choice</li>
              <li className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-green-400" />7-8: Generally good</li>
              <li className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber-400" />5-6: Use with caution</li>
              <li className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500" />0-4: Better to avoid</li>
            </ul>
          </div>
        </aside>

        <div className="space-y-10 xl:col-span-8">
          {/* Allergen alerts – shown first, they override the score */}
          {(result.allergen_alerts?.length ?? 0) > 0 && (
            <section role="alert" className="rounded-2xl border-2 border-red-300 bg-red-50 p-5 space-y-3 fade-in">
              <h2 className="font-headline text-xl text-red-700 flex items-center gap-2">
                <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>emergency</span>
                Allergen warning
              </h2>
              <ul className="space-y-1.5 text-sm text-red-800 font-body">
                {result.allergen_alerts!.map((a) => (
                  <li key={`${a.ingredient}-${a.allergen}`} className="flex gap-2">
                    <span className="font-bold capitalize">{a.ingredient}</span>
                    <span>
                      {a.trace ? "may contain" : "contains"} {a.allergen.replace(/_/g, " ")} — your profile:{" "}
                      {a.restriction.replace(/_/g, " ")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {(result.diet_conflicts?.length ?? 0) > 0 && (
            <section className="rounded-2xl border border-amber-300 bg-amber-50 p-5 space-y-2 fade-in">
              <h2 className="font-headline text-lg text-amber-800 flex items-center gap-2">
                <span className="material-symbols-outlined">no_food</span>
                Not suitable for your diet
              </h2>
              <p className="text-sm text-amber-900 font-body">
                {result.diet_conflicts!.map((d) => `${d.ingredient} (${d.restriction})`).join(", ")}
              </p>
            </section>
          )}

          {/* Score header */}
          <section className="forest-card overflow-hidden">
            <div className="gradient-bg px-6 pt-8 pb-2 text-center">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/20 text-on-primary text-xs font-black uppercase tracking-widest mb-1">
                <span className="material-symbols-outlined text-sm">biotech</span>
                Safety Report
              </div>
              {result.product && <h1 className="font-headline text-xl text-on-primary mt-2">{result.product.name}</h1>}
            </div>
            <div className="px-6 pb-6">
              <SafetyScoreCard score={result.safety_score} scoreOutOf={scoreOutOf} grade={result.grade} status={result.status} size="lg" />
              <div className="mt-1 mb-3 text-center">
                <p className="text-sm text-on-surface-variant font-body">
                  {confidenceLabel} based on ingredient matches ({Math.round(confidence * 100)}%)
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                {[
                  { label: "Total Ingredients", value: result.total_ingredients, icon: "list_alt", color: "text-secondary" },
                  { label: "Matched", value: result.matched_count ?? 0, icon: "search", color: "text-forest" },
                  { label: "Flagged", value: result.flagged_count, icon: "flag", color: "text-error" },
                  { label: "High Risk", value: highRisk.length, icon: "warning", color: "text-red-500" },
                ].map(({ label, value, icon, color }) => (
                  <div key={label} className="flex flex-col items-center gap-1 p-3 rounded-xl bg-ivory-warm/50 text-center">
                    <span className={`material-symbols-outlined text-xl ${color}`}>{icon}</span>
                    <span className="font-headline text-2xl text-on-surface">{value}</span>
                    <span className="text-[10px] text-on-surface-variant font-semibold leading-tight font-body">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* OCR text */}
          {result.ocr_text && (
            <section className="space-y-3">
              <h2 className="font-body font-bold text-on-surface text-lg flex items-center gap-2">
                <span className="material-symbols-outlined text-forest">document_scanner</span>
                Detected Text
              </h2>
              <div className="forest-card p-4 text-xs text-on-surface-variant font-mono leading-relaxed line-clamp-5">
                {result.ocr_text}
              </div>
            </section>
          )}

          {/* Flagged */}
          {result.flagged.length > 0 && (
            <section className="space-y-4">
              <h2 className="font-body font-bold text-on-surface text-lg flex items-center gap-2">
                <span className="material-symbols-outlined text-error">flag</span>
                Flagged Ingredients
                <span className="ml-auto px-2.5 py-1 rounded-full bg-error-container/40 text-error text-xs font-black border border-error/20">{result.flagged.length}</span>
              </h2>

              {highRisk.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-black uppercase tracking-widest text-red-500 px-1">High Risk</p>
                  {highRisk.map((item) => (
                    <IngredientCard key={item.id} item={item} />
                  ))}
                </div>
              )}

              {otherFlagged.length > 0 && (
                <div className="space-y-2">
                  {highRisk.length > 0 && <p className="text-xs font-black uppercase tracking-widest text-on-surface-variant px-1">Other Flags</p>}
                  {otherFlagged.map((item) => (
                    <IngredientCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </section>
          )}

          {result.flagged.length === 0 && (
            <div className="flex flex-col items-center gap-3 py-10 rounded-xl bg-emerald-50/50 border border-emerald-200 text-center forest-card">
              <span className="material-symbols-outlined text-5xl text-emerald-500" style={{ fontVariationSettings: "'FILL' 1" }}>
                check_circle
              </span>
              <p className="font-headline text-lg text-emerald-700">No concerning ingredients found.</p>
              <p className="text-emerald-600 text-sm max-w-sm font-body">
                None of the {result.total_ingredients} ingredients matched our list of concerning additives or your
                profile restrictions.
              </p>
            </div>
          )}

          {/* Alternatives */}
          {result.alternatives?.length > 0 && (
            <section className="space-y-4">
              <h2 className="font-body font-bold text-on-surface text-lg flex items-center gap-2">
                <span className="material-symbols-outlined text-forest">swap_horiz</span>
                Healthier Alternatives
              </h2>
              <div className="space-y-3">
                {result.alternatives.map((alt) => (
                  <AlternativeCard key={alt.id} alt={alt} />
                ))}
              </div>
            </section>
          )}

          <p className="text-xs text-on-surface-variant font-body leading-relaxed">
            SafeBite AI is an informational tool and can miss ingredients (especially with OCR). It is not medical
            advice. If you have a severe allergy, always read the full printed label and consult your doctor.
          </p>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              onClick={() => router.push("/scan")}
              className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl gradient-bg text-on-primary font-bold shadow-forest hover:shadow-forest-lg active:scale-[0.99] transition-all"
            >
              <span className="material-symbols-outlined">qr_code_scanner</span>
              Scan Another
            </button>
            <button
              onClick={() => router.push("/analyze")}
              className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl border-2 border-forest text-forest font-bold hover:bg-primary-container/20 active:scale-[0.99] transition-all"
            >
              <span className="material-symbols-outlined">edit_note</span>
              Enter Manually
            </button>
            <button
              onClick={() => router.push("/dashboard")}
              className="flex items-center justify-center gap-2 py-3.5 px-5 rounded-xl border-2 border-outline-variant/40 text-on-surface-variant font-bold hover:bg-ivory-warm transition-all"
            >
              <span className="material-symbols-outlined">home</span>
            </button>
          </div>
        </div>

        {/* Right sidebar */}
        <aside className="hidden xl:block xl:col-span-2">
          <div className="sticky top-28 forest-card p-4 space-y-2">
            <p className="text-xs uppercase tracking-wider font-black text-on-surface-variant">Summary</p>
            <p className="font-headline text-4xl text-on-surface leading-none">{result.safety_score}</p>
            <p className="text-xs text-on-surface-variant font-body">out of {scoreOutOf}</p>
            <p className="text-sm font-semibold text-on-surface font-body">Grade {result.grade ?? "N/A"}</p>
          </div>
        </aside>
      </main>
    </div>
  );
}
