/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0b0f14",
        panel: "#0f1722",
        accent: "#6ee7ff",
        accent2: "#a78bfa"
      },
      boxShadow: {
        glow: "0 0 0.5rem rgba(110,231,255,.5)",
        soft: "0 10px 30px rgba(0,0,0,.35)"
      },
      backgroundImage: {
        grid: "radial-gradient(transparent 1px, rgba(255,255,255,0.06) 1px)"
      }
    }
  },
  plugins: []
}
