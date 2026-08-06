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
        // Espelha `line-strong` do preset do design system (com o marrom do catálogo no lugar
        // do roxo): `line` é divisória decorativa (1.2:1) e não serve de contorno de campo/
        // botão, onde a WCAG 1.4.11 exige 3:1. Aqui dá 4.09:1 sobre panel e 3.39:1 sobre
        // surface-2. Precisa existir neste config porque `content` inclui packages/ui/src —
        // sem o token, Input e Button variant="outline" sairiam SEM borda no catálogo.
        "line-strong": "#8f7a64",
        surface: "#faf6ef",
        "surface-2": "#f1e9db",
        accent: {
          DEFAULT: "#4a2f6b",
          dark: "#2f1d47",
          soft: "rgba(74,47,107,0.08)",
        },
        // Sólido, não translúcido: os componentes de `@manto/ui` passaram a desenhar o foco com
        // `ring-offset`, e um anel a 30% de opacidade sobre o creme do catálogo praticamente
        // some — quem navega por teclado perde a referência de onde está. Mesmo raciocínio do
        // preset; aqui precisa ser repetido porque o app público não consome o preset.
        ring: "#4a2f6b",
        gold: {
          DEFAULT: "#b1793a",
          soft: "rgba(177,121,58,0.12)",
          // Mesmo degrau de texto do preset: `DEFAULT` sobre `gold-soft` dá 3.25:1 e reprova
          // AA. `ink` dá 5.32:1 sobre gold-soft e 5.46:1 sobre o creme do catálogo.
          ink: "#8a5a28",
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
