import type { Config } from "tailwindcss";

// Tokens portados de app/static/style.css (--bg/--panel/--accent/etc., mesma paleta usada em
// todo o portal clássico) — mesmos NOMES de token que apps/internal/apps/public para que os
// componentes @manto/ui (Button/Card/Input/Skeleton/FileUpload) herdem a identidade visual da
// Manto automaticamente, sem duplicar estilo (Princípio I). Preset próprio (não o do internal):
// o Portal do Artista é uma superfície mobile-only para talentos externos, não o painel staff.
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
        green: {
          DEFAULT: "#1a7f3c",
          soft: "#d4edda",
        },
        red: {
          DEFAULT: "#c0392b",
          soft: "#fde8e8",
        },
        blue: {
          DEFAULT: "#2563eb",
          soft: "#dbeafe",
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
