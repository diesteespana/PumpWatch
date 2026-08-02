import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // PumpWatch brand palette — dark-first
        brand: {
          DEFAULT: "#00E5FF",   // cyan accent
          dark: "#0097A7",
          muted: "#00B8D4",
        },
        surface: {
          DEFAULT: "#0D1117",   // page background
          card: "#161B22",      // card background
          elevated: "#21262D",  // hover / active states
          border: "#30363D",
        },
        success: "#00C853",
        danger: "#FF3D00",
        warning: "#FFD600",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      keyframes: {
        "pulse-brand": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
      animation: {
        "pulse-brand": "pulse-brand 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
