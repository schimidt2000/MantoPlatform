import type { Config } from "tailwindcss";

// Tokens portados de app/templates/catalogo/_head_shared.html (--cat-*) — mesma paleta do
// catálogo público atual, zero mudança visual como efeito colateral da migração de stack
// (T003, research.md §1). Usa os MESMOS nomes de token que apps/internal (bg/panel/accent/
// ring/etc.) para que os componentes @manto/ui (Button/Card/Input/Skeleton) herdem a
// identidade visual do catálogo automaticamente, sem duplicar estilo (Princípio I).
const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../packages/*/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#faf6ef",
        "bg-alt": "#f1e9db",
        panel: "#ffffff",
        ink: "#241c2e",
        muted: "#7d7188",
        line: "#e7ddcd",
        surface: "#faf6ef",
        "surface-2": "#f1e9db",
        accent: {
          DEFAULT: "#4a2f6b",
          dark: "#2f1d47",
          soft: "rgba(74,47,107,0.08)",
        },
        ring: "rgba(74,47,107,0.30)",
        gold: {
          DEFAULT: "#b1793a",
          soft: "rgba(177,121,58,0.12)",
        },
        red: {
          DEFAULT: "#c0392b",
          soft: "#fde8e8",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Manrope", "-apple-system", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "18px",
        xl: "24px",
      },
      boxShadow: {
        sm: "0 1px 2px rgba(36,28,46,0.04)",
        md: "0 12px 32px rgba(36,28,46,0.08)",
        lg: "0 18px 40px rgba(36,28,46,0.14)",
      },
    },
  },
  plugins: [],
};

export default config;
