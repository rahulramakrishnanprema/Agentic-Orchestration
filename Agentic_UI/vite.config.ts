import './suppress-errors.js';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import type { ProxyOptions } from 'vite';

// Custom error handler that completely swallows errors
const createSilentProxy = (): ProxyOptions => ({
  target: 'http://localhost:8080',
  changeOrigin: true,
  secure: false,
  ws: false,
  configure: (proxy, _options) => {
    // Remove all existing listeners to prevent default error logging
    proxy.removeAllListeners('error');
    proxy.removeAllListeners('proxyReq');
    proxy.removeAllListeners('proxyRes');

    // Add completely silent error handler
    proxy.on('error', (_err, _req, res) => {
      // Don't log anything, just handle the response
      if (!res.headersSent) {
        try {
          res.writeHead(503, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            error: 'Backend not available'
          }));
        } catch {
          // Ignore
        }
      }
    });
  }
});

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    proxy: {
      '/api': createSilentProxy()
    }
  }
});
