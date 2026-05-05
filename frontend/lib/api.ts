// lib/api.ts  – centralised fetch wrapper for Flask backend

const DEFAULT_BASES = ["http://127.0.0.1:5000/api", "http://localhost:5000/api"] as const;

function getApiBases() {
  const envBase = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!envBase) return [...DEFAULT_BASES];
  return [envBase, ...DEFAULT_BASES.filter(b => b !== envBase)];
}

function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("safebite_token");
}

async function req<T>(
  path: string,
  options: RequestInit = {},
  authenticated = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authenticated) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response | null = null;
  let lastNetworkError = false;
  const bases = getApiBases();

  for (const base of bases) {
    try {
      res = await fetch(`${base}${path}`, { ...options, headers });
      lastNetworkError = false;
      break;
    } catch {
      lastNetworkError = true;
    }
  }

  if (!res && lastNetworkError) {
    throw new Error(`Cannot connect to API (${bases[0]}). Start backend and verify NEXT_PUBLIC_API_URL.`);
  }
  if (!res) {
    throw new Error("Request failed before reaching API.");
  }

  const raw = await res.text();
  let data: any = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }

  if (!res.ok) {
    throw new Error(data.error ?? raw ?? `Request failed (${res.status})`);
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
  const qs = category ? `?category=${category}` : "";
  return req<Product[]>(`/products${qs}`);
}

export async function getProductByBarcode(barcode: string) {
  return req<Product>(`/products/barcode/${barcode}`);
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

export async function analyzeImageBase64(image_base64: string, age_group: string) {
  return req<AnalysisResult>("/analyze/image", {
    method: "POST",
    body: JSON.stringify({ image_base64, age_group }),
  }, true);
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
}

export interface Alternative {
  id: number;
  alt_name: string;
  alt_brand: string;
  reason: string;
  image_url: string;
  score_delta: number;
}

export interface AnalysisResult {
  safety_score: number;
  score_out_of?: number;
  grade?: string;
  match_confidence?: number;
  status: "safe" | "moderate" | "unsafe";
  flagged: FlaggedIngredient[];
  ingredient_details: { raw: string; matched: string | null; flagged: boolean }[];
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
