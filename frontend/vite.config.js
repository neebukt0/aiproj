import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
