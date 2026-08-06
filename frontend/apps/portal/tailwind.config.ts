import type { Config } from "tailwindcss";
import mantoPreset from "@manto/ui/tailwind-preset";

// O Portal consome o MESMO preset do design system (@manto/ui/tailwind-preset) em vez de
// redeclarar a paleta à mão: a cópia duplicada que existia aqui repetia token a token os
// valores do preset e fazia toda correção de contraste precisar ser aplicada duas vezes —
// além de omitir a família `gold`, o que fazia `StarRating`/`Badge tone="gold"` de @manto/ui
// renderizarem sem cor no portal (as classes nem chegavam a existir no CSS gerado).
//
// A ÚNICA divergência deliberada é o fundo: o Portal do Artista usa um cinza levemente
// arroxeado (#f4f3f8) no lugar do neutro do painel staff (#f4f5f7).
const config: Config = {
  presets: [mantoPreset as Config],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../packages/*/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#f4f3f8",
        surface: "#f4f3f8",
      },
    },
  },
  plugins: [],
};

export default config;
