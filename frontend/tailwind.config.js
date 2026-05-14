/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ef: {
          'navy-900': '#0B1426',
          'navy-800': '#111D35',
          'navy-700': '#1A2A4A',
          'navy-600': '#243B63',
          'slate-400': '#8B95A5',
          'slate-300': '#A8B2C1',
          'slate-200': '#C5CDD8',
          'orange-500': '#E8722A',
          'orange-400': '#F28B4A',
          'orange-300': '#F7A76B',
          'green-500': '#2ECC71',
          'red-500': '#E74C3C',
          'amber-500': '#F39C12',
          surface: '#0F1923',
          'surface-raised': '#162233',
          border: '#1E3048',
          text: '#E8ECF1',
          'text-secondary': '#8B95A5',
          'text-muted': '#5A6577',
        },
      },
      fontFamily: {
        display: ['Poppins', 'sans-serif'],
        body: ['Poppins', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
