/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          safe:     "#10b981",
          warning:  "#f59e0b",
          danger:   "#ef4444",
          critical: "#7f1d1d",
        },
      },
    },
  },
  plugins: [],
};
