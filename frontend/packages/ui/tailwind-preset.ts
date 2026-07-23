import type { Config } from "tailwindcss";

// Preset global do design system Manto (feature 173) — fonte única dos tokens do painel
// interno, promovidos de apps/internal/tailwind.config.ts (que por sua vez portou
// app/static/style.css :root). Valores de sidebar/fundo atualizados conforme a spec da
// FASE A (Manto Dark Purple #1f1a30, fundo neutro #f4f5f7).
//
// ATENÇÃO: apps/public NÃO consome este preset — o catálogo público tem identidade
// própria (paleta creme/dourada) com os MESMOS nomes de token; aplicar o preset lá
// mudaria o visual do catálogo (ver research.md §2 da feature 173).
const mantoPreset: Partial<Config> = {
  theme: {
    extend: {
      colors: {
        bg: "#f4f5f7",
        panel: "#ffffff",
        ink: "#1a1a1a",
        muted: "#6b6b6b",
        line: "#e5e3ef",
        surface: "#f4f5f7",
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
        gold: { DEFAULT: "#b1793a", soft: "rgba(177,121,58,0.12)" },
        sidebar: {
          bg: "#1f1a30",
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
};

export default mantoPreset;
