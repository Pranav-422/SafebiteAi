"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, logout as apiLogout } from "@/lib/api";

const navLinks = [
  { href: "/dashboard", label: "Home",        icon: "dashboard" },
  { href: "/products",  label: "Products",    icon: "storefront" },
  { href: "/scan",      label: "Scan",        icon: "qr_code_scanner" },
  { href: "/analyze",   label: "Label Input", icon: "edit_note" },
];

export default function Navbar() {
  const path = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  // Every page that renders the Navbar requires a session.
  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  async function logout() {
    await apiLogout().catch(() => {});
    router.push("/login");
  }

  return (
    <>
      {/* Desktop */}
      <nav className="fixed top-0 w-full z-50 glass-nav shadow-[0px_20px_40px_rgba(42,52,57,0.06)]">
        <div className="flex justify-between items-center px-6 h-16 w-full max-w-screen-2xl mx-auto font-headline tracking-tight">
          <Link href="/dashboard" className="text-xl font-bold text-on-surface">
            Safe Bite <span className="text-primary">AI</span>
          </Link>
          <div className="hidden md:flex items-center space-x-2">
            {navLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`px-3 py-2 rounded-lg font-semibold text-sm transition-colors ${
                  path === href
                    ? "text-primary bg-primary/8"
                    : "text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={logout}
              className="hidden md:flex items-center gap-1 text-xs font-semibold text-on-surface-variant hover:text-primary transition-colors px-3 py-2 rounded-lg hover:bg-surface-container-high"
            >
              <span className="material-symbols-outlined text-sm">logout</span>
              Logout
            </button>
            <button
              className="md:hidden p-2 rounded-full hover:bg-surface-container-high"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <span className="material-symbols-outlined">{menuOpen ? "close" : "menu"}</span>
            </button>
          </div>
        </div>
        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden bg-surface/95 backdrop-blur-xl border-t border-outline-variant/10 px-4 pb-4">
            {navLinks.map(({ href, label, icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-3 rounded-xl font-semibold text-sm transition-colors ${
                  path === href ? "text-primary bg-primary/8" : "text-on-surface-variant"
                }`}
              >
                <span className="material-symbols-outlined text-lg">{icon}</span>
                {label}
              </Link>
            ))}
            <button
              onClick={logout}
              className="flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-semibold text-on-surface-variant w-full"
            >
              <span className="material-symbols-outlined text-lg">logout</span>
              Logout
            </button>
          </div>
        )}
      </nav>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-white/80 backdrop-blur-xl flex items-center justify-around z-50 shadow-[0px_-10px_40px_rgba(0,0,0,0.05)] px-4">
        {navLinks.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex flex-col items-center gap-1 ${path === href ? "text-primary" : "text-on-surface-variant"}`}
          >
            <span
              className="material-symbols-outlined"
              style={path === href ? { fontVariationSettings: "'FILL' 1" } : {}}
            >
              {icon}
            </span>
            <span className="text-[10px] font-bold">{label}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}
