import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        /* ── Forest & Ivory Design System ─────────────────────── */
        "forest":                    "#2D5A3D",
        "forest-dark":               "#1A3A28",
        "forest-light":              "#3D7A52",
        "forest-muted":              "#4A8C62",
        "ivory":                     "#F5F0E8",
        "ivory-warm":                "#EDE7DA",
        "ivory-light":               "#FAF8F4",
        "ivory-dark":                "#E0D9CC",

        /* Semantic mapping */
        "primary":                   "#2D5A3D",
        "primary-dim":               "#1A3A28",
        "primary-container":         "#D4E8DB",
        "on-primary":                "#FAFAF7",
        "on-primary-container":      "#1A3A28",

        "secondary":                 "#6B8F7B",
        "secondary-dim":             "#5A7D6A",
        "secondary-container":       "#D4E8DB",
        "on-secondary":              "#FAFAF7",
        "on-secondary-container":    "#1A3A28",

        "tertiary":                  "#8B6F4E",
        "tertiary-container":        "#E8D9C4",
        "on-tertiary-container":     "#5A3E1F",

        "error":                     "#9B3B3B",
        "error-container":           "#F2D4D4",
        "on-error-container":        "#5C1A1A",

        "surface":                   "#FAF8F4",
        "surface-dim":               "#E8E3DA",
        "surface-bright":            "#FAF8F4",
        "surface-container-lowest":  "#FFFFFF",
        "surface-container-low":     "#F5F0E8",
        "surface-container":         "#EDE7DA",
        "surface-container-high":    "#E5DFD3",
        "surface-container-highest": "#DDD7CB",
        "surface-variant":           "#E5DFD3",
        "surface-tint":              "#2D5A3D",

        "background":                "#FAF8F4",
        "on-background":             "#2C2C28",
        "on-surface":                "#2C2C28",
        "on-surface-variant":        "#5C5C52",
        "outline":                   "#7A7A6E",
        "outline-variant":           "#C4BFB4",
        "inverse-on-surface":        "#8A8A7E",
        "inverse-primary":           "#7BC494",

        "primary-fixed":             "#A8D5B8",
        "primary-fixed-dim":         "#8BC4A0",
        "secondary-fixed":           "#D4E8DB",
        "tertiary-fixed-dim":        "#C4A882",
        "tertiary-fixed":            "#D4BC9A",
      },
      borderRadius: {
        DEFAULT: "0.375rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.5rem",
        md: "0.5rem",
        full: "9999px",
      },
      fontFamily: {
        headline: ["'DM Serif Display'", "Georgia", "serif"],
        body:     ["'DM Sans'", "'Inter'", "sans-serif"],
        label:    ["'DM Sans'", "'Inter'", "sans-serif"],
      },
      boxShadow: {
        "forest": "0 4px 24px rgba(45, 90, 61, 0.08)",
        "forest-lg": "0 12px 48px rgba(45, 90, 61, 0.12)",
        "ivory": "0 2px 12px rgba(44, 44, 40, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
