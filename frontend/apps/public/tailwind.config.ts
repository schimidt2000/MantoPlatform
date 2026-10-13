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
        // Tinta sobre preenchimento saturado. No painel interno este token existe porque lá o
        // acento CLAREIA no tema escuro e o branco reprovaria AA; aqui o catálogo não tem tema
        // escuro, então é branco fixo (7.85:1 sobre o roxo do catálogo). Precisa existir neste
        // config pelo mesmo motivo de `line-strong`/`ring`: `content` inclui packages/ui/src, e
        // o `Button` do design system usa `text-on-color` — sem o token o botão primário do
        // catálogo sairia com o texto herdado, sem cor nenhuma.
        "on-color": "#ffffff",
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
        // Feature 255 — paleta da luminária "Magia de Sonhar" para a página pública `/nfc`.
        // Cores da peça física (estrela que acende em laranja quente, borda escura, nuvem
        // clara), registradas AQUI para a página não hardcodar cor nenhuma (Constituição V).
        lamp: {
          glow: "#ffa93d",
          "glow-deep": "#f07f1f",
          script: "#7a3a0d",
          border: "#33205c",
          cloud: "#efe8fa",
        },
        // Feature 304 — tema da Loja de Interações Virtuais (`/v*`, o que `alo.*` abre). Mesmo
        // arranjo do `lamp.*`: namespace próprio, para o Natal não vazar no catálogo de festa
        // (que usa os tokens globais acima). A estação atual é o Natal das artes de marketing —
        // verde-floresta, vermelho veludo e dourado. Trocar de estação = trocar estes valores e
        // a copy de `src/lib/lojaTema.ts`; as páginas só falam `alo-*`.
        // Contraste (WCAG) medido sobre `bg` / `surface` / `surface-2`: ink 14.7/11.5/9.6,
        // muted 9.1/7.1/6.0, gold 10.0/7.8/6.5, line-strong 4.7/3.7/3.1 (contorno de campo ≥ 3).
        alo: {
          bg: "#0c2219",
          surface: "#143728",
          "surface-2": "#1b4434",
          line: "rgba(230,196,126,0.22)",
          "line-strong": "#9c8657",
          ink: "#f8f0e1",
          muted: "#c9bfa5",
          gold: "#e6c47e",
          "gold-deep": "#c99a4a",
          // Botão principal: creme sobre vermelho dá 8.0:1. O vermelho sozinho some no verde
          // (1.9:1), por isso o botão leva contorno dourado — como o "Agende esse momento" da arte.
          red: "#8f1d24",
          "red-hover": "#a3262e",
          "on-red": "#fbf3e4",
          error: "#ffb4a8",
        },
      },
      backgroundImage: {
        // Brilho quente no topo, como as luzes desfocadas das artes. Só gradiente: nenhuma
        // imagem a mais para baixar no 4G.
        "alo-glow":
          "radial-gradient(ellipse 90% 45% at 50% 0%, rgba(230,196,126,0.16), transparent 70%), radial-gradient(ellipse 60% 40% at 100% 30%, rgba(143,29,36,0.18), transparent 70%)",
      },
      dropShadow: {
        // Halo da estrela acesa — dois raios, como a luz da luminária vazando no escuro.
        lamp: ["0 0 24px rgba(255,169,61,0.55)", "0 0 72px rgba(255,169,61,0.30)"],
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["Manrope", "-apple-system", "Segoe UI", "sans-serif"],
        // Serifa de alto contraste das artes de Natal (feature 304), só na loja de conversas.
        "alo-display": ["'Playfair Display'", "Georgia", "serif"],
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
