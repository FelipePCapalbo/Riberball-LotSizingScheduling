import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

const WORKER_URL_BY_MODE: Record<string, string> = {
  main: 'https://riberball-lotsizingscheduling.felipecapalbo.workers.dev',
  dev: 'https://riberball-lotsizingscheduling-dev.felipecapalbo.workers.dev',
};
const SHARED_SECRET = process.env.VITE_SHARED_SECRET;

export default defineConfig(({ mode }) => {
  let proxyTarget = WORKER_URL_BY_MODE[mode];
  if (process.env.VITE_PROXY_TARGET) {
    proxyTarget = process.env.VITE_PROXY_TARGET;
  }

  return {
    plugins: [react()],
    build: {
      outDir: `dist/${mode}`,
    },
    server: {
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: true,
          headers: SHARED_SECRET ? { authorization: `Bearer ${SHARED_SECRET}` } : undefined,
        },
      },
    },
  };
});
