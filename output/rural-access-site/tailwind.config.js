/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Neutral slate base
        ink: {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
          500: '#64748b',
          400: '#94a3b8',
          300: '#cbd5e1',
          200: '#e2e8f0',
          100: '#f1f5f9',
          50: '#f8fafc',
        },
        // Muted forest / teal accent
        forest: {
          900: '#14302a',
          800: '#1c4339',
          700: '#225a4b',
          600: '#2c7363',
          500: '#3d8c79',
          400: '#5ba593',
          300: '#8cc4b6',
          200: '#bfe0d7',
          100: '#e3f2ed',
        },
      },
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      maxWidth: {
        reading: '680px',
      },
    },
  },
  plugins: [],
}
