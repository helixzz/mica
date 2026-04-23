/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      thresholds: {
        statements: 60,
        branches: 50,
        functions: 50,
        lines: 60,
      },
      exclude: [
        '**/*.d.ts',
        '**/node_modules/**',
        '**/dist/**',
        'src/main.tsx',
        'src/test/**',
        'src/i18n/**',
        'src/assets/**',
        'src/pages/**',
        'src/api/**',
        'src/auth/**',
        'src/routes/**',
        'src/components/Layout/**',
        'src/components/GlobalSearch/**',
        'src/components/NotificationBell/**',
        'src/components/AIStreamButton.tsx',
        'src/components/PrintButton.tsx',
        'src/components/LanguageSwitcher.tsx',
      ],
    },
  },
})
