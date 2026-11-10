/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#080b11",
        surface: "#0f1623",
        "surface-raised": "#162033",
        "surface-border": "#1e2c45",
        brand: {
          blue: "#0070ba", // PayPal Blue
          darkblue: "#003087",
          cyan: "#00d2ff",
          emerald: "#10b981",
          amber: "#f59e0b",
          crimson: "#ef4444"
        }
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      }
    },
  },
  plugins: [],
};

