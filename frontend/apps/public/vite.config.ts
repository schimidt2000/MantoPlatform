import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Scaffolding — catálogo/cadastro/formulários/feedback são escopo da User Story 5.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    proxy: { "/api": { target: "http://localhost:5000", changeOrigin: true } },
  },
});
