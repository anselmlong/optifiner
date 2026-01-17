/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Primary brand colors
        primary: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        // Semantic colors
        success: {
          bg: '#DCFCE7',
          border: '#86EFAC',
          text: '#166534',
          solid: '#22C55E',
          'bg-dark': '#14532D',
          'border-dark': '#166534',
          'text-dark': '#86EFAC',
        },
        warning: {
          bg: '#FEF9C3',
          border: '#FDE047',
          text: '#854D0E',
          solid: '#EAB308',
          'bg-dark': '#713F12',
          'border-dark': '#854D0E',
          'text-dark': '#FDE047',
        },
        error: {
          bg: '#FEE2E2',
          border: '#FECACA',
          text: '#991B1B',
          solid: '#EF4444',
          'bg-dark': '#7F1D1D',
          'border-dark': '#991B1B',
          'text-dark': '#FECACA',
        },
        info: {
          bg: '#DBEAFE',
          border: '#93C5FD',
          text: '#1E40AF',
          solid: '#3B82F6',
          'bg-dark': '#1E3A8A',
          'border-dark': '#1E40AF',
          'text-dark': '#93C5FD',
        },
        // Status colors
        status: {
          accepted: '#22C55E',
          rejected: '#EF4444',
          processing: '#F59E0B',
          analyzing: '#06B6D4',
          pending: '#94A3B8',
          mutating: '#8B5CF6',
        },
        // Chart colors
        chart: {
          1: '#3B82F6',
          2: '#06B6D4',
          3: '#22C55E',
          4: '#F59E0B',
          5: '#EF4444',
          6: '#8B5CF6',
        },
        // Surface colors - light
        surface: {
          primary: '#FFFFFF',
          elevated: '#FFFFFF',
          hover: '#F8FAFC',
          active: '#F1F5F9',
          selected: '#EFF6FF',
        },
        // Background colors - light
        bg: {
          primary: '#FFFFFF',
          secondary: '#F8FAFC',
          tertiary: '#F1F5F9',
        },
        // Border colors - light
        border: {
          primary: '#E2E8F0',
          secondary: '#CBD5E1',
          subtle: '#F1F5F9',
          focus: '#3B82F6',
        },
        // Syntax highlighting
        syntax: {
          keyword: '#8B5CF6',
          string: '#22C55E',
          number: '#F59E0B',
          function: '#3B82F6',
          comment: '#94A3B8',
          operator: '#EC4899',
          variable: '#06B6D4',
          type: '#F97316',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'SF Mono', 'Monaco', 'Cascadia Code', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1.5' }],
        'sm': ['0.875rem', { lineHeight: '1.5' }],
        'base': ['1rem', { lineHeight: '1.5' }],
        'lg': ['1.125rem', { lineHeight: '1.375' }],
        'xl': ['1.25rem', { lineHeight: '1.375' }],
        '2xl': ['1.5rem', { lineHeight: '1.25' }],
        '3xl': ['1.875rem', { lineHeight: '1.25' }],
        '4xl': ['2.25rem', { lineHeight: '1.1' }],
      },
      borderRadius: {
        'sm': '0.25rem',
        'md': '0.375rem',
        'lg': '0.5rem',
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        'sm': '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        'md': '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        'lg': '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        'xl': '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
        '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
        'primary': '0 4px 14px 0 rgb(59 130 246 / 0.3)',
        'success': '0 4px 14px 0 rgb(34 197 94 / 0.3)',
        'error': '0 4px 14px 0 rgb(239 68 68 / 0.3)',
        'glow-primary': '0 0 20px rgb(59 130 246 / 0.4)',
        'glow-success': '0 0 20px rgb(34 197 94 / 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 2s ease-in-out infinite',
        'spin-slow': 'spin 2s linear infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
