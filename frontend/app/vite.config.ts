import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const PROXY_TARGET = process.env.VITE_PROXY_TARGET || 'https://riberball-lotsizingscheduling.felipecapalbo.workers.dev';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: PROXY_TARGET,
        changeOrigin: true,
        secure: true,
      },
    },
  },
});
