import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    pool: 'forks',
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['e2e/**', 'node_modules/**'],
    globals: true,
  },
});
