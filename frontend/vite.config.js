import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Example Code:
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});
