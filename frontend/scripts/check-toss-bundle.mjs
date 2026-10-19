// 토스 빌드(dist-toss)에 들어가면 안 되는 토큰을 찾아 개수와 위치를 출력한다.
// 지금은 리포트 전용이라 발견돼도 실패(exit 1)시키지 않는다. --strict 를 주면 실패시킨다.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, extname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('..', import.meta.url))
const distDir = join(root, 'dist-toss')
const srcDir = join(root, 'src')
const strict = process.argv.includes('--strict')

// 웹 도메인은 코드에서 확인한 값(https://fomobot.net). Gmail 작성창 링크(mail.google.com)와
// AdSense 호스트(googlesyndication)도 같은 이유로 포함.
const TOKENS = [
  '백테스트', '샀다', '샀죠', '매수',
  'adsbygoogle', 'pagead', 'googlesyndication', 'adfit', 'kakaocdn',
  'fomobot.net', 'mail.google.com', '_blank', 'mailto',
]

// 빌드 산출물에서 한글이 \uXXXX로 이스케이프될 수 있어 그 형태로도 찾는다.
const escaped = (t) => [...t].map((c) => (c.charCodeAt(0) > 127 ? '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0') : c)).join('')
const variants = (t) => (escaped(t) === t ? [t] : [t, escaped(t)])

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) yield* walk(p)
    else yield p
  }
}

const TEXT_EXT = new Set(['.html', '.js', '.css', '.json', '.svg', '.txt', '.ts', '.tsx'])

function scan(dir, label) {
  const counts = new Map(TOKENS.map((t) => [t, new Map()])) // token -> file -> count
  for (const file of walk(dir)) {
    if (!TEXT_EXT.has(extname(file))) continue
    const text = readFileSync(file, 'utf8')
    for (const t of TOKENS) {
      let n = 0
      for (const v of variants(t)) n += text.split(v).length - 1
      if (n) counts.get(t).set(relative(root, file).split('\\').join('/'), n)
    }
  }
  console.log(`\n[${label}]`)
  let total = 0
  for (const t of TOKENS) {
    const files = counts.get(t)
    const sum = [...files.values()].reduce((a, b) => a + b, 0)
    total += sum
    const detail = [...files].sort((a, b) => b[1] - a[1]).map(([f, n]) => `${f}(${n})`).join(', ')
    console.log(`  ${t.padEnd(18)} ${String(sum).padStart(3)}  ${detail}`)
  }
  return total
}

let bundleTotal = 0
try {
  bundleTotal = scan(distDir, '번들 dist-toss — 최종 판정 대상')
} catch (e) {
  console.error('dist-toss를 읽을 수 없습니다. 먼저 vite build --mode toss 를 실행하세요.', e.message)
  process.exit(1)
}
// 번들은 minify되어 출처를 알 수 없으므로 소스 파일별 분포를 참고용으로 같이 낸다.
scan(srcDir, '소스 src — 출처 참고용(웹 전용 코드 포함)')

console.log(`\n번들 내 금지 토큰 합계: ${bundleTotal}${strict ? '' : ' (리포트 모드: 실패시키지 않음)'}`)
if (strict && bundleTotal > 0) process.exit(1)
