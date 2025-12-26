/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./resources/**/*.{vue,js,ts,jsx,tsx}",
    "./index.html",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#10b981',
          dark: '#059669',
          light: '#34d399',
        },
        secondary: {
          DEFAULT: '#3b82f6',
          dark: '#2563eb',
          light: '#60a5fa',
        },
        sidebar: '#1e293b',
        danger: '#ef4444',
        warning: '#f59e0b',
        success: '#22c55e',
        info: '#0ea5e9',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 1.5s infinite',
        'float': 'float 6s ease-in-out infinite',
        'slide-up': 'slideUp 0.5s ease-out',
        'glow': 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 5px rgba(16, 185, 129, 0.5)' },
          '50%': { boxShadow: '0 0 20px rgba(16, 185, 129, 0.8)' },
        },
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.08)',
        'glass-lg': '0 20px 40px rgba(0, 0, 0, 0.12)',
        'glow-primary': '0 0 20px rgba(16, 185, 129, 0.4)',
        'glow-secondary': '0 0 20px rgba(59, 130, 246, 0.4)',
      },
    },
  },
  plugins: [],
}
