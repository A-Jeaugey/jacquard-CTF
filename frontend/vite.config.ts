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
  build: { target: "es2022", sourcemap: true },
});
