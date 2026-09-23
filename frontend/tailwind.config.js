/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        orange: {
          50: '#FFF8E7',
          100: '#FFE4B5',
          200: '#FFE0B2',
          300: '#FFCC80',
          400: '#FFB74D',
          500: '#FFA726',
          600: '#E65100',
          700: '#BF360C',
          800: '#8D6E63',
          900: '#3E2723',
        },
        beige: {
          50: '#FDFBF7',
          100: '#F5F5DC',
          200: '#F0E6D3',
          300: '#E8DCC5',
          400: '#D4C4A8',
          500: '#C4B48E',
          600: '#A89070',
          700: '#8B7355',
          800: '#6B5344',
          900: '#4A3728',
        },
      },
      backgroundImage: {
        'paper-texture': "url(\"data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.08'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
