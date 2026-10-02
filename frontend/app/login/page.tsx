"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    setError("");
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await login(email, password)
          : await register(email, password, fullName);
      setToken(data.token);
      router.push("/dashboard");
    } catch (e: any) {
      setError(e.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row fade-in bg-white">
      {/* Left Panel - Green Slit */}
      <div className="w-full md:w-1/2 min-h-screen bg-forest flex flex-col justify-center px-8 md:px-16 lg:px-24 py-12 relative overflow-hidden">
        {/* Subtle decorative overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-forest-dark to-transparent opacity-50 z-0"></div>
        <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-forest-light/20 blur-[100px] z-0"></div>
        <div className="absolute bottom-[-10%] left-[-10%] w-[400px] h-[400px] rounded-full bg-forest-dark/40 blur-[80px] z-0"></div>

        <div className="relative z-10">
          {/* Leaf accent */}
          <div className="flex items-center gap-2 mb-8">
            <span className="material-symbols-outlined text-white text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>eco</span>
            <span className="text-sm font-bold uppercase tracking-[0.2em] text-white/80">Powered by Nature</span>
          </div>

          <h1 className="font-headline text-[4.5rem] lg:text-[5.5rem] leading-[0.95] font-normal tracking-tight text-white mb-6 drop-shadow-sm">
            Safe<br />Bite <span className="text-white/70 italic">AI</span>
          </h1>

          <p className="font-body text-xl text-white/90 max-w-md leading-relaxed">
            Scan food labels, detect allergens, and get instant safety scores — protecting your health one bite at a time.
          </p>

          <div className="mt-14 flex flex-col gap-6">
            {[
              { icon: "search", label: "OCR Label Scanner" },
              { icon: "warning", label: "Allergen Detection" },
              { icon: "verified", label: "Personalised Safety Score" },
              { icon: "eco", label: "Healthier Alternatives" },
            ].map(f => (
              <div key={f.label} className="flex items-center gap-4 text-white">
                <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center">
                  <span className="material-symbols-outlined text-white text-base">{f.icon}</span>
                </div>
                <span className="font-body font-medium text-base tracking-wide">{f.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="w-full md:w-1/2 min-h-screen bg-surface-container-lowest flex flex-col justify-center items-center px-6 py-12">
        <section className="animate-slide-in w-full max-w-[500px]">
          <div className="bg-white p-10 md:p-14 rounded-2xl border border-outline-variant/30 shadow-forest-lg">
            <div className="mb-10 text-center">
              <span className="font-headline text-4xl text-on-surface">
                {mode === "login" ? "Welcome Back" : "Create Account"}
              </span>
              <p className="text-on-surface-variant font-medium mt-3 text-base">
                {mode === "login" ? "Sign in to your Safe Bite AI account" : "Start your food safety journey"}
              </p>
            </div>

            <div className="space-y-6">
              {mode === "register" && (
                <div className="space-y-2.5">
                  <label className="text-on-surface-variant text-sm font-bold uppercase tracking-widest px-1">Full Name</label>
                  <div className="relative group">
                    <span className="material-symbols-outlined absolute left-5 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-forest transition-colors text-xl">person</span>
                    <input
                      className="w-full h-16 pl-14 pr-5 bg-ivory-warm/40 rounded-xl border-2 border-outline-variant/30 focus:border-forest focus:bg-white text-on-surface placeholder:text-on-surface-variant/40 transition-all outline-none text-base font-medium"
                      placeholder="Your name"
                      value={fullName}
                      onChange={e => setFullName(e.target.value)}
                    />
                  </div>
                </div>
              )}

              <div className="space-y-2.5">
                <label className="text-on-surface-variant text-sm font-bold uppercase tracking-widest px-1">Email Address</label>
                <div className="relative group">
                  <span className="material-symbols-outlined absolute left-5 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-forest transition-colors text-xl">alternate_email</span>
                  <input
                    className="w-full h-16 pl-14 pr-5 bg-ivory-warm/40 rounded-xl border-2 border-outline-variant/30 focus:border-forest focus:bg-white text-on-surface placeholder:text-on-surface-variant/40 transition-all outline-none text-base font-medium"
                    placeholder="name@example.com"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2.5">
                <label className="text-on-surface-variant text-sm font-bold uppercase tracking-widest px-1">Password</label>
                <div className="relative group">
                  <span className="material-symbols-outlined absolute left-5 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-forest transition-colors text-xl">lock</span>
                  <input
                    className="w-full h-16 pl-14 pr-5 bg-ivory-warm/40 rounded-xl border-2 border-outline-variant/30 focus:border-forest focus:bg-white text-on-surface placeholder:text-on-surface-variant/40 transition-all outline-none text-base font-medium"
                    placeholder="••••••••"
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleSubmit()}
                  />
                </div>
              </div>

              {error && (
                <div className="bg-error-container/40 text-error rounded-xl px-5 py-4 text-sm font-semibold flex items-center gap-2 border border-error/20">
                  <span className="material-symbols-outlined text-lg">error</span>
                  {error}
                </div>
              )}

              <div className="pt-4">
                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="w-full h-16 gradient-bg text-on-primary font-bold text-lg rounded-xl shadow-forest hover:shadow-forest-lg active:scale-[0.98] transition-all duration-300 disabled:opacity-60"
                >
                  {loading ? "Please wait…" : mode === "login" ? "Sign In to Safe Bite AI" : "Create Account"}
                </button>
              </div>
            </div>
          </div>

          <p className="mt-8 text-center text-on-surface-variant text-base">
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
              className="text-forest font-bold hover:underline"
            >
              {mode === "login" ? "Create Account" : "Sign In"}
            </button>
          </p>
          <p className="mt-6 text-center text-xs font-headline tracking-widest text-on-surface/30 uppercase">
            Safe Bite AI © 2025
          </p>
        </section>
      </div>
    </div>
  );
}
