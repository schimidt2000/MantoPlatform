import type { Config } from "tailwindcss";
import mantoPreset from "@manto/ui/tailwind-preset";

// O Portal consome o MESMO preset do design system (@manto/ui/tailwind-preset) em vez de
// redeclarar a paleta à mão: a cópia duplicada que existia aqui repetia token a token os
// valores do preset e fazia toda correção de contraste precisar ser aplicada duas vezes —
// além de omitir a família `gold`, o que fazia `StarRating`/`Badge tone="gold"` de @manto/ui
// renderizarem sem cor no portal (as classes nem chegavam a existir no CSS gerado).
//
// A ÚNICA divergência deliberada é o fundo: o Portal do Artista usa um cinza levemente
// arroxeado (#f4f3f8) no lugar do neutro do painel staff (#f4f5f7). Desde o dark mode isso
// NÃO é mais um override de cor aqui — um HEX fixo nesta camada anularia a variável CSS e
// deixaria o Portal preso no claro. O override virou `--c-bg`/`--c-surface` em `src/index.css`.
const config: Config = {
  presets: [mantoPreset as Config],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../packages/*/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
