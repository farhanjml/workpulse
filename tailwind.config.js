/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/renderer/**/*.{html,js,jsx}'],
  darkMode: ['attribute', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg:           'var(--bg)',
        s0:           'var(--s0)',
        s1:           'var(--s1)',
        s2:           'var(--s2)',
        s3:           'var(--s3)',
        gold:         'var(--gold)',
        'gold-dim':   'var(--gold-dim)',
        'gold-bg':    'var(--gold-bg)',
        'gold-border':'var(--gold-border)',
        t1:           'var(--t1)',
        t2:           'var(--t2)',
        t3:           'var(--t3)',
        border:       'var(--border)',
        'border-h':   'var(--border-h)',
        green:        'var(--green)',
        'green-bg':   'var(--green-bg)',
        'green-border':'var(--green-border)',
        red:          'var(--red)',
        'red-bg':     'var(--red-bg)',
        'red-border': 'var(--red-border)',
      },
      fontFamily: {
        sans: ['Sora', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      borderRadius: {
        card: '14px',
      }
    }
  },
  plugins: []
}
