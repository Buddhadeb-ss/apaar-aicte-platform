/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        warm: {
          50: '#FBFBFA',
          100: '#FAF9F5',
          200: '#F4F3EE',
          300: '#EAE8E1',
          400: '#E5E4DF',
          500: '#D5D3CA',
          600: '#A8A29E',
          700: '#78716C',
          800: '#44403C',
          900: '#1C1917',
        },
        terracotta: {
          50: '#FDF8F6',
          100: '#F5ECE8',
          200: '#EBDBD5',
          500: '#CC785C',
          600: '#C2410C',
          700: '#9A3412',
          800: '#7C2D12',
        },
        aicte: {
          dark: '#1C1917',
          navy: '#0F172A',
          blue: '#1E3A8A',
          light: '#FAF9F5',
          saffron: '#C2410C',
          emerald: '#15803D',
          danger: '#B91C1C',
          warning: '#B45309'
        }
      },
      fontFamily: {
        serif: ['"Anthropic Serif"', 'Newsreader', 'Lora', 'Charter', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
}
