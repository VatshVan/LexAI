import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          900: "#0a0e1a",
          800: "#111827",
          700: "#1f2937",
          600: "#374151"
        },
        accent: "#3b82f6",
        verified: "#10b981",
        flagged: "#f59e0b",
        purged: "#ef4444",
        "null-field": "#dc2626"
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"]
      }
    }
  },
  plugins: []
} satisfies Config;
