import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

import { cloudflare } from "@cloudflare/vite-plugin";

export default defineConfig({
  plugins: [react(), cloudflare()],
  server: {
    proxy: {
      // 부동산 백엔드 (8001) — 주식보다 먼저 매칭되어야 함
      '/api/realestate': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // 주식 백엔드 (8000)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // VITE_API_BASE_URL 이 설정된 경우 빌드 결과물에 포함됨
  // Vercel 환경변수로 주입: VITE_API_BASE_URL=https://fomobot-api.up.railway.app
})