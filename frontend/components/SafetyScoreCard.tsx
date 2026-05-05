"use client";

interface Props {
  score: number;
  status: "safe" | "moderate" | "unsafe";
  scoreOutOf?: number;
  grade?: string;
  size?: "sm" | "lg";
}

const STATUS_COLORS = {
  safe:     { ring: "stroke-emerald-500", text: "text-emerald-600", bg: "bg-emerald-50",  label: "Safe",     icon: "check_circle" },
  moderate: { ring: "stroke-amber-500",   text: "text-amber-600",   bg: "bg-amber-50",    label: "Moderate", icon: "warning" },
  unsafe:   { ring: "stroke-red-500",     text: "text-red-600",     bg: "bg-red-50",      label: "Unsafe",   icon: "cancel" },
};

export default function SafetyScoreCard({ score, status, scoreOutOf = 10, grade, size = "lg" }: Props) {
  const c = STATUS_COLORS[status];
  const r = 54;
  const circ = 2 * Math.PI * r;
  const normalizedScore = Math.max(0, Math.min(scoreOutOf, score));
  const offset = circ - (normalizedScore / scoreOutOf) * circ;
  const isLg = size === "lg";

  return (
    <div className={`flex flex-col items-center gap-4 ${isLg ? "py-8" : "py-4"}`}>
      {/* Donut */}
      <div className={`relative ${isLg ? "w-40 h-40" : "w-24 h-24"}`}>
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r={r} fill="none" stroke="#E5DFD3" strokeWidth="10" />
          <circle
            cx="60" cy="60" r={r} fill="none"
            className={c.ring}
            strokeWidth="10"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${isLg ? "text-4xl" : "text-2xl"} font-black font-headline ${c.text}`}>{normalizedScore}</span>
          {isLg && <span className="text-xs text-on-surface-variant font-semibold">/ {scoreOutOf}</span>}
        </div>
      </div>

      {/* Badge */}
      <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${c.bg}`}>
        <span className={`material-symbols-outlined text-lg ${c.text}`} style={{ fontVariationSettings: "'FILL' 1" }}>
          {c.icon}
        </span>
        <span className={`font-headline font-black text-sm uppercase tracking-wider ${c.text}`}>{c.label}</span>
        {grade && (
          <span className="px-2 py-0.5 rounded-full bg-white/80 text-[11px] font-black text-on-surface">
            Grade {grade}
          </span>
        )}
      </div>
    </div>
  );
}
