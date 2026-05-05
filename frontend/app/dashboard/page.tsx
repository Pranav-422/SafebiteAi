"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { getHistory, getProfile, ScanHistoryItem, UserProfile } from "@/lib/api";

const STATUS_COLORS = {
  safe:     "bg-emerald-50 text-emerald-700 border-emerald-200",
  moderate: "bg-amber-50 text-amber-700 border-amber-200",
  unsafe:   "bg-red-50 text-red-700 border-red-200",
};

const QUICK_ACTIONS = [
  { href: "/products", icon: "storefront",     label: "Select Product",  sub: "Browse product gallery" },
  { href: "/scan",     icon: "qr_code_scanner",label: "Scan Label",      sub: "Upload or capture label" },
  { href: "/analyze",  icon: "edit_note",       label: "Enter Manually",  sub: "Type ingredient list" },
];

export default function DashboardPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [history, setHistory] = useState<ScanHistoryItem[]>([]);

  useEffect(() => {
    getProfile().then(setProfile).catch(() => {});
    getHistory().then(setHistory).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-forest-gradient fade-in">
      <Navbar />
      <main className="pt-24 pb-24 px-6 max-w-screen-xl mx-auto">

        {/* Hero */}
        <header className="text-center mb-16 space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-container/40 text-forest text-xs font-bold uppercase tracking-[0.15em] mb-2">
            <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>eco</span>
            Dashboard
          </div>
          <h1 className="font-headline text-5xl md:text-6xl text-on-surface">
            Begin Your <span className="text-forest italic">Journey</span>
          </h1>
          <p className="text-on-surface-variant text-lg max-w-md mx-auto font-body">
            {profile ? `Welcome back, ${profile.full_name || profile.email}!` : "Scan, detect allergens, and stay safe."}
          </p>
        </header>

        {/* Quick action cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl mx-auto mb-16">
          {QUICK_ACTIONS.map(({ href, icon, label, sub }, i) => (
            <Link
              key={href}
              href={href}
              className="group forest-card flex flex-col items-center p-8 cursor-pointer"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <div className="w-16 h-16 rounded-2xl gradient-bg flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <span className="material-symbols-outlined text-3xl text-white">{icon}</span>
              </div>
              <h2 className="font-headline text-xl mb-1 text-on-surface">{label}</h2>
              <p className="text-on-surface-variant text-sm font-body text-center">{sub}</p>
              <div className="mt-5 w-10 h-10 rounded-full bg-primary-container/50 text-forest flex items-center justify-center group-hover:bg-forest group-hover:text-white transition-all duration-300">
                <span className="material-symbols-outlined text-xl">arrow_forward</span>
              </div>
            </Link>
          ))}
        </div>

        {/* Scan History */}
        {history.length > 0 && (
          <section className="max-w-4xl mx-auto">
            <h2 className="font-headline text-2xl mb-6 text-on-surface">Recent Scans</h2>
            <div className="space-y-3">
              {history.slice(0, 6).map(item => (
                <div
                  key={item.id}
                  className="flex items-center gap-4 forest-card p-4"
                >
                  <div className="w-10 h-10 rounded-xl bg-ivory-warm flex items-center justify-center">
                    <span className="material-symbols-outlined text-on-surface-variant">
                      {item.scan_type === "image" ? "image" : item.scan_type === "manual" ? "edit_note" : "qr_code_scanner"}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-body font-bold text-sm truncate text-on-surface">{item.product_name ?? "Unknown product"}</p>
                    <p className="text-xs text-on-surface-variant">{new Date(item.scanned_at).toLocaleDateString()}</p>
                  </div>
                  {item.status && (
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${STATUS_COLORS[item.status as keyof typeof STATUS_COLORS] ?? ""}`}>
                      {item.status}
                    </span>
                  )}
                  {item.safety_score != null && (
                    <span className="font-headline text-sm text-on-surface">{item.safety_score}/10</span>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
