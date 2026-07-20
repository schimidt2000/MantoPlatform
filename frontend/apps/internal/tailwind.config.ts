import type { Config } from "tailwindcss";

// Tokens portados de app/static/style.css (:root) — mesma paleta do painel interno atual,
// zero mudança visual como efeito colateral da migração de stack (T008, research.md §4).
const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../packages/*/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#f4f3f8",
        panel: "#ffffff",
        ink: "#1a1a1a",
        muted: "#6b6b6b",
        line: "#e5e3ef",
        surface: "#f4f3f8",
        "surface-2": "#eeecf5",
        accent: {
          DEFAULT: "#544596",
          dark: "#3c316b",
          soft: "rgba(84,69,150,0.10)",
        },
        ring: "rgba(84,69,150,0.30)",
        green: { DEFAULT: "#1a7f3c", soft: "#d4edda" },
        red: { DEFAULT: "#c0392b", soft: "#fde8e8" },
        blue: { DEFAULT: "#2563eb", soft: "#dbeafe" },
        sidebar: {
          bg: "#1e1635",
          accent: "#f7d897",
        },
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "20px",
      },
      boxShadow: {
        sm: "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)",
        md: "0 4px 14px rgba(0,0,0,0.07), 0 2px 6px rgba(0,0,0,0.04)",
        lg: "0 12px 32px rgba(0,0,0,0.10), 0 4px 10px rgba(0,0,0,0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
