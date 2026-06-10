/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontSize: {
        base: ["14px", "1.4"],
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        "surface-3": "var(--surface-3)",
        inset: "var(--inset)",
        ink: "var(--ink)",
        "ink-2": "var(--ink-2)",
        "ink-3": "var(--ink-3)",
        border: "var(--border)",
        "border-2": "var(--border-2)",
        hairline: "var(--hairline)",
        brand: "var(--brand)",
        "brand-ink": "var(--brand-ink)",
        "brand-soft": "var(--brand-soft)",
        "on-brand": "var(--on-brand)",
        pos: "var(--pos)",
        "pos-soft": "var(--pos-soft)",
        neg: "var(--neg)",
        "neg-soft": "var(--neg-soft)",
        amber: "var(--amber)",
        "amber-soft": "var(--amber-soft)",
        info: "var(--info)",
        "info-soft": "var(--info-soft)",
      },
      borderRadius: {
        card: "var(--r-card)",
        ctrl: "var(--r-ctrl)",
        pill: "var(--r-pill)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
      },
    },
  },
  plugins: [],
};
