/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'cyber-green': '#00ff41',
                'cyber-blue': '#00d4ff',
                'cyber-pink': '#ff006e',
            },
            fontFamily: {
                mono: ['JetBrains Mono', 'Courier New', 'monospace'],
            },
            animation: {
                'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
            },
            keyframes: {
                'pulse-glow': {
                    '0%, 100%': {
                        opacity: '1',
                        boxShadow: '0 0 20px currentColor'
                    },
                    '50%': {
                        opacity: '0.5',
                        boxShadow: '0 0 40px currentColor'
                    },
                },
            },
        },
    },
    plugins: [],
}
