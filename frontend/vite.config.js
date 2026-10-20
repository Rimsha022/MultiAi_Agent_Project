import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Python backend (api/main.py) runs on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
