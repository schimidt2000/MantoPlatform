import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scaffolding — conteúdo real do Portal do Artista é escopo da User Story 3.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { "/api": { target: "http://localhost:5000", changeOrigin: true } },
  },
});
