"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { analyzeImage, AgeGroup } from "@/lib/api";

const AGE_GROUPS: { value: AgeGroup; icon: string; label: string; sub: string }[] = [
  { value: "child", icon: "child_care", label: "Child", sub: "Ages 0-12. Strict toxicity thresholds." },
  { value: "teen", icon: "school", label: "Teen", sub: "Ages 13-19. Focus on hormonal health." },
  { value: "adult", icon: "person", label: "Adult", sub: "Ages 20+. Balanced safety profile." },
  { value: "senior", icon: "elderly", label: "Senior", sub: "Ages 60+. Extra caution." },
];

const MAX_UPLOAD_MB = 8;

export default function ScanPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [ageGroup, setAgeGroup] = useState<AgeGroup>("adult");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFile(f: File) {
    if (!f.type.startsWith("image/")) {
      setError("Please choose an image file (JPG, PNG, WEBP).");
      return;
    }
    if (f.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`Image is too large (max ${MAX_UPLOAD_MB} MB).`);
      return;
    }
    setFile(f);
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(f);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }

  async function handleScan() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeImage(file, ageGroup);
      sessionStorage.setItem("safebite_result", JSON.stringify(result));
      router.push("/report");
    } catch (err: any) {
      setError(err.message ?? "Scan failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-forest-gradient fade-in">
      <Navbar />
      <main className="pt-28 pb-24 px-6 max-w-2xl mx-auto">
        {/* Header */}
        <header className="text-center mb-10 space-y-3">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-container/40 text-forest text-xs font-bold uppercase tracking-[0.15em] mb-2">
            <span className="material-symbols-outlined text-sm">qr_code_scanner</span>
            Scan Label
          </div>
          <h1 className="font-headline text-4xl md:text-5xl text-on-surface">
            Verify ingredients in <span className="text-forest italic">seconds.</span>
          </h1>
          <p className="text-on-surface-variant text-base max-w-md mx-auto font-body leading-relaxed">
            Our clinical-grade AI scans product labels to identify potential allergens and harmful additives tailored to your profile.
          </p>
        </header>

        {/* Upload area */}
        <div
          className={`relative forest-card p-8 mb-8 transition-all duration-300 ${
            dragOver ? "ring-2 ring-forest bg-primary-container/20" : ""
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          {preview ? (
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview} alt="Label preview" className="w-full rounded-xl max-h-80 object-contain mx-auto" />
              {loading && <div className="ocr-scanner-line" />}
              <button
                onClick={() => { setFile(null); setPreview(null); }}
                className="absolute top-3 right-3 w-8 h-8 rounded-full bg-white/90 flex items-center justify-center text-on-surface-variant hover:bg-error-container hover:text-on-error-container transition-colors shadow-ivory"
              >
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          ) : (
            <label className="flex flex-col items-center gap-4 py-10 cursor-pointer">
              <div className="w-20 h-20 rounded-2xl bg-primary-container/40 flex items-center justify-center">
                <span className="material-symbols-outlined text-4xl text-forest">cloud_upload</span>
              </div>
              <div className="text-center">
                <p className="font-body font-bold text-on-surface text-base">Drop label or Click to Upload</p>
                <p className="text-xs text-on-surface-variant mt-1">Supports JPG, PNG, or PDF. Max size 10MB.</p>
              </div>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
              />
            </label>
          )}
        </div>

        {/* Age Group Risk Profile */}
        <section className="mb-8">
          <h2 className="font-headline text-xl text-on-surface mb-1">Age Group Risk Profile</h2>
          <p className="text-xs text-on-surface-variant mb-4 font-body">Analysis sensitivity adjusts based on age requirements.</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {AGE_GROUPS.map((a) => (
              <button
                key={a.value}
                onClick={() => setAgeGroup(a.value)}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200 ${
                  ageGroup === a.value
                    ? "border-forest bg-primary-container/30 shadow-forest"
                    : "border-outline-variant/40 bg-white hover:border-forest/40"
                }`}
              >
                <span className="material-symbols-outlined text-2xl text-forest" style={{ fontVariationSettings: "'FILL' 1" }}>{a.icon}</span>
                <span className={`text-sm font-bold ${ageGroup === a.value ? "text-forest" : "text-on-surface"}`}>{a.label}</span>
                <span className={`text-[10px] text-center leading-tight ${ageGroup === a.value ? "text-forest/70" : "text-on-surface-variant"}`}>{a.sub}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-error-container/40 text-error text-sm font-medium border border-error/20 mb-6">
            <span className="material-symbols-outlined text-lg">error</span>
            {error}
          </div>
        )}

        {/* Scan button */}
        <button
          onClick={handleScan}
          disabled={!preview || loading}
          className="w-full py-4 rounded-xl gradient-bg text-on-primary font-bold text-lg shadow-forest hover:shadow-forest-lg active:scale-[0.98] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
        >
          {loading ? (
            <>
              <svg className="animate-spin w-5 h-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Scanning…
            </>
          ) : (
            <>
              <span className="material-symbols-outlined">center_focus_strong</span>
              Scan Label
            </>
          )}
        </button>

        {/* Bottom nav hint */}
        <div className="flex items-center justify-center gap-8 mt-10 pt-6 border-t border-outline-variant/30">
          {[
            { icon: "center_focus_strong", label: "Scan", href: "/scan", active: true },
            { icon: "receipt_long", label: "History", href: "/dashboard", active: false },
            { icon: "person", label: "Health Profile", href: "/analyze", active: false },
          ].map(item => (
            <a
              key={item.label}
              href={item.href}
              className={`flex flex-col items-center gap-1 text-xs font-body font-semibold transition-colors ${
                item.active ? "text-forest" : "text-on-surface-variant hover:text-forest"
              }`}
            >
              <span className="material-symbols-outlined text-xl" style={item.active ? { fontVariationSettings: "'FILL' 1" } : {}}>{item.icon}</span>
              {item.label}
            </a>
          ))}
        </div>
      </main>
    </div>
  );
}
