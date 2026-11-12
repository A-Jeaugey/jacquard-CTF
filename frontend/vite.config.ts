import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.JACQUARD_API ?? "http://localhost:8000", changeOrigin: false },
    },
  },
  // three.js (la maquette en volume) forme un fichier à part, chargé seulement par la page des
  // défis : il dépasse le seuil d'alerte par défaut (500 ko), sans alourdir le reste du site.
  build: { target: "es2022", sourcemap: true, chunkSizeWarningLimit: 750 },
});
