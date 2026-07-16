/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./resources/**/*.{vue,js,ts,jsx,tsx}",
    "./index.html",
  ],
  theme: {
    extend: {
      colors: {
        // Teal/ink "compliance" palette
        primary: {
          DEFAULT: '#0E7C86',
          dark:    '#0A5A62',
          light:   '#159AA5',
          soft:    '#E4F1F2',
        },
        secondary: {
          DEFAULT: '#1A424C',
          dark:    '#12333B',
          light:   '#2A5C67',
        },
        ink:     '#12333B',
        sidebar: '#12333B',
        danger:  '#B03030',
        warning: '#9A6B00',
        success: '#1F7A4D',
        info:    '#0E7C86',
      },
      fontFamily: {
        sans: ['Source Sans 3', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer':    'shimmer 1.5s infinite',
        'slide-up':   'slideUp 0.4s ease-out',
        'fade-in':    'fadeIn 0.3s ease-out',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      boxShadow: {
        'card':    '0 1px 4px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)',
        'card-md': '0 4px 24px rgba(0,0,0,0.08)',
        'nav':     '0 1px 0 rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}
