import type { Config } from "tailwindcss";
import mantoPreset from "@manto/ui/tailwind-preset";

// Tokens do painel interno vivem no preset compartilhado do design system
// (@manto/ui/tailwind-preset) desde a feature 173 — fonte única, nada de
// redeclarar cor/sombra/radius aqui.
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
