import type { Config } from "tailwindcss"

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#fff7ed",
        panel: "#ffffff",
        card: "#ffffff",
        "card-2": "#ffedd5",
        border: "#fed7aa",
        "border-strong": "#fb923c",
        text: "#1f1308",
        muted: "#8a5a32",
        "muted-2": "#b77945",
        accent: "#ffffff",
        travel: "#f97316",
        success: "#16a34a",
        warning: "#f59e0b",
        blue: "#2563eb",
        ink: "#1f1308",
        "ink-soft": "#8a5a32",
        rice: "#fff7ed",
        mist: "#ffedd5",
        coral: "#f97316",
        "coral-dark": "#ea580c",
        jade: "#16a34a",
        lotus: "#f59e0b",
      },
      boxShadow: {
        soft: "0 18px 55px rgba(154, 86, 32, 0.13)",
        card: "0 12px 28px rgba(154, 86, 32, 0.10)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
}

export default config
