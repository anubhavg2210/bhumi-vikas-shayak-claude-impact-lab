import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Dev server proxies API calls to the FastAPI backend, so the browser talks to one
  // origin (no CORS needed). Override with BACKEND_URL in .env.local if it runs elsewhere.
  const backendUrl = env.BACKEND_URL || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': { target: backendUrl, changeOrigin: true },
        '/health': { target: backendUrl, changeOrigin: true }
      }
    },
    test: {
      environment: 'jsdom',
      globals: true
    }
  }
})
