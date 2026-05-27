import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    strictPort : true,
    proxy: {
      '/api': {
        target: 'http://13.39.106.131:5002',
        changeOrigin: true,
      }
    }
  }
})