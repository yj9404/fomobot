import { defineConfig, type Plugin } from 'vite'
import aitDevtools from '@apps-in-toss/devtools/unplugin'
import react from '@vitejs/plugin-react'

import { cloudflare } from "@cloudflare/vite-plugin";

// ait build는 webBundleDir 안의 index.html을 찾는다. 진입 html 이름(index.toss.html)을 맞춰준다.
const renameTossEntry = (): Plugin => ({
  name: 'rename-toss-entry',
  enforce: 'post',
  generateBundle: {
    order: 'post',
    handler(_, bundle) {
      const entry = bundle['index.toss.html']
      if (!entry) return
      entry.fileName = 'index.html'
      bundle['index.html'] = entry
      delete bundle['index.toss.html']
    },
  },
})

// toss 모드 dev 서버에서 /를 진입 html로 연결한다. 토스 SDK/devtools와 샌드박스는 루트 경로를 전제하기 쉽다.
const serveTossRoot = (): Plugin => ({
  name: 'serve-toss-root',
  configureServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url === '/' || req.url?.startsWith('/?')) req.url = '/index.toss.html' + req.url.slice(1)
      next()
    })
  },
})

// 토스 번들은 별도 오리진(*.tossmini.com)에서 서빙되므로 API를 상대 경로로 부르면 토스 정적 호스팅으로 간다
// (S3 AccessDenied XML 403). 그래서 toss 빌드에는 백엔드 절대 주소(HTTPS)를 박는다.
// wrangler.jsonc의 vars.API_BASE와 같은 서비스다. 다른 주소로 빌드하려면 TOSS_API_BASE_URL을 지정한다.
const TOSS_API_BASE_URL = process.env.TOSS_API_BASE_URL ?? 'https://fomobot-production-64fd.up.railway.app'

// 앱인토스 배너 광고 그룹 ID(콘솔 발급, 비밀값 아님 — 어차피 클라이언트 번들에 들어간다).
// build에서만 주입하고 dev 서버는 TossBanner의 테스트 ID를 쓴다(개발 중 실제 ID로 테스트하면 정책 위반).
// 다른 ID로 빌드하려면 VITE_TOSS_BANNER_AD_GROUP_ID를 지정한다.
const TOSS_BANNER_AD_GROUP_ID = process.env.VITE_TOSS_BANNER_AD_GROUP_ID ?? 'ait.v2.live.d7d803200c524f97'

// mode === 'toss' 는 앱인토스 미니앱 빌드. Worker(공유 카드)와 정적 글(public/)은 웹 전용이라 뺀다.
export default defineConfig(({ mode, command }) => {
  const isToss = mode === 'toss'
  return {
    // dev 서버(serve)는 기존처럼 Vite proxy(/api)를 쓰므로 build에서만 주입한다.
    define: isToss && command === 'build'
      ? {
          'import.meta.env.VITE_API_BASE_URL': JSON.stringify(TOSS_API_BASE_URL),
          'import.meta.env.VITE_TOSS_BANNER_AD_GROUP_ID': JSON.stringify(TOSS_BANNER_AD_GROUP_ID),
        }
      : undefined,
    plugins: isToss
      ? [
          // devtools(mock SDK + 패널)는 toss dev 서버에서만. 프로덕션 빌드와 웹에는 넣지 않는다.
          // 진입점 이름(main.toss.tsx)이 기본 패턴과 달라 패널 주입 대상을 직접 지정한다.
          ...(command === 'serve' ? [aitDevtools.vite({ entryPattern: /\/main\.toss\.tsx$/ })] : []),
          react(),
          renameTossEntry(),
          serveTossRoot(),
        ]
      : [react(), cloudflare()],
    build: isToss
      ? { outDir: 'dist-toss', emptyOutDir: true, rollupOptions: { input: 'index.toss.html' } }
      : undefined,
    publicDir: isToss ? false : 'public',
    // .ait 안에서 정적 자산을 상대 경로로 읽도록 toss 빌드에만 적용
    ...(isToss && { base: './' }),
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
    // Cloudflare Workers 환경변수로 주입: VITE_API_BASE_URL=https://fomobot-api.up.railway.app
  }
})
