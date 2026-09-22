/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#060D20",
          900: "#0A142E",
          800: "#0D1B3C",
          700: "#14264E",
          600: "#1B3166",
          500: "#274080",
        },
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(15, 23, 42, 0.05), 0 1px 3px 0 rgba(15, 23, 42, 0.08)",
        "card-hover": "0 8px 24px -6px rgba(15, 23, 42, 0.14)",
        popover: "0 10px 40px -6px rgba(15, 23, 42, 0.22)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
}