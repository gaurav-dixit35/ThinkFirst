import type {Config} from 'tailwindcss';
export default {content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'], theme: {extend: {colors: {paper: '#f7f8f2', ink: '#26382e', accent: '#b7ca8a'}, fontFamily: {display: ['Georgia', 'serif'], sans: ['Arial', 'sans-serif']}}}, plugins: []} satisfies Config;
