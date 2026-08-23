import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const PROXY_TARGET = process.env.VITE_PROXY_TARGET || 'https://riberball-lotsizingscheduling.felipecapalbo.workers.dev';
const SHARED_SECRET = process.env.VITE_SHARED_SECRET;

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: true,
        headers: SHARED_SECRET ? { authorization: `Bearer ${SHARED_SECRET}` } : undefined,
      },
    },
  },
});
