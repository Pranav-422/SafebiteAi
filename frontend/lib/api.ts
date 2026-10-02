// lib/api.ts  – centralised fetch wrapper for Flask backend

const TOKEN_KEY = "safebite_token";

function getApiBase() {
  const envBase = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (envBase) return envBase.replace(/\/+$/, "");
  // Only fall back to a local backend during development; production must be configured explicitly.
  if (process.env.NODE_ENV !== "production") return "http://localhost:5000/api";
  throw new Error("NEXT_PUBLIC_API_URL is not configured.");
}

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem("safebite_result");
}

function handleUnauthorized() {
  clearSession();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    // Called outside React components, so a hard navigation is intended here.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/login");
  }
}

async function req<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false
): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  // Let the browser set the multipart boundary for FormData bodies.
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (authenticated) {
    const token = getToken();
    if (!token) {
      handleUnauthorized();
      throw new Error("Please log in again.");
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  const base = getApiBase();
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { ...options, headers });
  } catch {
    throw new Error("Cannot reach the SafeBite server. Please check your connection and try again.");
  }

  const raw = await res.text();
  let data: any = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }

  if (res.status === 401 && authenticated) {
    handleUnauthorized();
  }
  if (!res.ok) {
    throw new Error(data.error ?? `Request failed (${res.status})`);
  }
  return data as T;
}

// ── Auth ──────────────────────────────────────────────────────────
export async function login(email: string, password: string) {
  return req<{ token: string; user_id: number; email: string }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
}

export async function logout() {
  try {
    if (getToken()) await req<{ message: string }>("/auth/logout", { method: "POST" }, true);
  } finally {
    clearSession();
  }
}

export async function register(email: string, password: string, full_name: string) {
  return req<{ token: string; user_id: number; email: string }>(
    "/auth/register",
    { method: "POST", body: JSON.stringify({ email, password, full_name }) }
  );
}

// ── Profile ───────────────────────────────────────────────────────
export async function getProfile() {
  return req<UserProfile>("/user/profile", {}, true);
}

export async function updateProfile(data: Partial<UserProfile>) {
  return req<{ message: string }>("/user/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  }, true);
}

// ── Products ──────────────────────────────────────────────────────
export async function getProducts(category?: string) {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return req<Product[]>(`/products${qs}`);
}

export async function getProductByBarcode(barcode: string) {
  return req<Product>(`/products/barcode/${encodeURIComponent(barcode)}`);
}

// ── Analysis ──────────────────────────────────────────────────────
export async function analyzeText(
  ingredients_text: string,
  age_group: string,
  product_id?: number,
  restrictions?: string[]
) {
  return req<AnalysisResult>("/analyze/text", {
    method: "POST",
    body: JSON.stringify({ ingredients_text, age_group, product_id, restrictions }),
  }, true);
}

export async function analyzeProduct(product_id: number, age_group: string) {
  return req<AnalysisResult>(`/analyze/product/${product_id}`, {
    method: "POST",
    body: JSON.stringify({ age_group }),
  }, true);
}

export async function analyzeImage(image: Blob, age_group: string, restrictions?: string[]) {
  const form = new FormData();
  form.append("image", image, "label.jpg");
  form.append("age_group", age_group);
  if (restrictions?.length) form.append("restrictions", JSON.stringify(restrictions));
  return req<AnalysisResult>("/analyze/image", { method: "POST", body: form }, true);
}

export async function getRestrictions() {
  return req<string[]>("/restrictions");
}

// ── History ───────────────────────────────────────────────────────
export async function getHistory() {
  return req<ScanHistoryItem[]>("/history", {}, true);
}

// ── Types ─────────────────────────────────────────────────────────
export type AgeGroup = "child" | "teen" | "adult" | "senior";

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
  age_group: AgeGroup;
  restrictions: string[];
}

export interface Product {
  id: number;
  name: string;
  brand: string;
  barcode: string;
  category: string;
  image_url: string;
  raw_ingredients: string;
}

export interface FlaggedIngredient {
  id: number;
  name: string;
  risk_level: "high" | "medium" | "low" | "safe";
  category: string;
  reason: string;
  age_restriction: string;
  restriction_hit: boolean;
  risk_score: number;
  matched_as?: string;
  trace?: boolean;
}

export interface Alternative {
  id: number;
  alt_name: string;
  alt_brand: string;
  reason: string;
  image_url: string;
  score_delta: number;
}

export interface AllergenAlert {
  ingredient: string;
  allergen: string;
  restriction: string;
  trace: boolean;
}

export interface DietConflict {
  ingredient: string;
  restriction: string;
}

export interface AnalysisResult {
  safety_score: number;
  score_out_of?: number;
  grade?: string;
  match_confidence?: number;
  status: "safe" | "moderate" | "unsafe";
  flagged: FlaggedIngredient[];
  allergen_alerts?: AllergenAlert[];
  diet_conflicts?: DietConflict[];
  restrictions_applied?: string[];
  age_group?: AgeGroup;
  ingredient_details: { raw: string; matched: string | null; matches?: string[]; flagged: boolean }[];
  total_ingredients: number;
  matched_count?: number;
  flagged_count: number;
  analysis_id: number;
  alternatives: Alternative[];
  product?: Product;
  ocr_text?: string;
}

export interface ScanHistoryItem {
  id: number;
  scan_type: string;
  scanned_at: string;
  product_name: string;
  category: string;
  safety_score: number;
  status: string;
}
