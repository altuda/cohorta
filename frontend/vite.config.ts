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
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
