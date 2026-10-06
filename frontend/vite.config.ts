import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import federation from "@originjs/vite-plugin-federation";
export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: "P115MediaOrganizer",
      filename: "remoteEntry.js",
      exposes: {
        "./Page": "./src/components/Page.vue",
        "./Config": "./src/components/Config.vue",
        "./Dashboard": "./src/components/Dashboard.vue",
      },
      shared: { vue: { requiredVersion: false, generate: false } },
    }),
  ],
  build: {
    target: "esnext",
    outDir: "../plugins.v3/p115mediaorganizer/dist",
    emptyOutDir: true,
    cssCodeSplit: true,
  },
});
