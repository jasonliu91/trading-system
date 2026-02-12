import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#070b11",
        panel: "#0f1723",
        border: "#1f2a3a",
        text: "#d3deed",
        muted: "#7f8ba1",
        bull: "#17b26a",
        bear: "#f04438",
        accent: "#0ea5e9"
      },
      boxShadow: {
        panel: "0 12px 42px rgba(0, 0, 0, 0.42)"
      }
    }
  },
  plugins: []
};

export default config;

