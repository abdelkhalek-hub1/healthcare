/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f7ff",
          100: "#e0effe",
          200: "#bae0fd",
          300: "#7cc8fc",
          400: "#38aef7",
          500: "#0e94eb",
          600: "#0277cb",
          700: "#035fa3",
          800: "#075186",
          900: "#0c446f",
          950: "#082b49",
        },
        dark: {
          bg: "#0b0f19",
          card: "#151b2c",
          border: "#222d44",
          input: "#1b233a",
          text: "#f3f4f6",
          muted: "#9ca3af",
        }
      },
      fontFamily: {
        sans: ["Outfit", "Inter", "sans-serif"],
      },
      animation: {
        "pulse-subtle": "pulse-subtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
      keyframes: {
        "pulse-subtle": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: .85 },
        }
      }
    },
  },
  plugins: [],
}
