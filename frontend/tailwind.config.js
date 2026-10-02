/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        raised: 'var(--raised)',
        border: 'var(--border)',
        accent: 'var(--accent)',
        'accent-dim': 'var(--accent-dim)',
        'accent-soft': 'var(--accent-soft)',
        primary: 'var(--text-primary)',
        muted: 'var(--text-muted)',
        danger: 'var(--danger)',
        'danger-soft': 'var(--danger-soft)',
        warning: 'var(--warning)',
        'warning-soft': 'var(--warning-soft)',
        success: 'var(--success)',
        'success-soft': 'var(--success-soft)',
        info: 'var(--info)',
        'info-soft': 'var(--info-soft)',
      },
      fontFamily: { sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
