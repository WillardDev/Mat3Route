/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        background: '#F6F8F7',
        surface: '#FFFFFF',
        ink: '#0F172A',
        muted: '#64748B',
        border: '#E2E8F0',
        primary: {
          DEFAULT: '#0F766E',
          dark: '#115E59',
          tint: '#CCFBF1',
        },
        alert: {
          DEFAULT: '#DC2626',
          tint: '#FEE2E2',
        },
        'fare-normal': {
          DEFAULT: '#16A34A',
          tint: '#DCFCE7',
          text: '#166534',
        },
        'fare-up': {
          DEFAULT: '#D97706',
          tint: '#FEF3C7',
          text: '#92400E',
        },
        pending: {
          DEFAULT: '#94A3B8',
          tint: '#F1F5F9',
          text: '#475569',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
