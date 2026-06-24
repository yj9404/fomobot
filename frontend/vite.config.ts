import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 로컬 개발 전용: VITE_API_BASE_URL 이 없을 때 백엔드로 프록시
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // VITE_API_BASE_URL 이 설정된 경우 빌드 결과물에 포함됨
  // Vercel 환경변수로 주입: VITE_API_BASE_URL=https://fomobot-api.up.railway.app
})
