import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Set ONCOPLOT_BASE_PATH for subdirectory deployments:
//   ONCOPLOT_BASE_PATH=/oncoplot/ npm run build
const basePath = process.env.ONCOPLOT_BASE_PATH || '/'

export default defineConfig({
  base: basePath,
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        // Use 127.0.0.1, not "localhost": Node 17+ resolves "localhost" to IPv6
        // (::1) first, but uvicorn binds IPv4 only by default, so a "localhost"
        // target makes every proxied request fail with ECONNREFUSED.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
