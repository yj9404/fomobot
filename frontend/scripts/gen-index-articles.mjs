// index.html의 <!-- ARTICLES:START --> ~ <!-- ARTICLES:END --> 블록을
// src/data/articles.json에서 자동 생성한다. 새 글을 추가할 때 이 스크립트가
// articles.json → index.html 정적 폴백 목록에 반영하는 유일한 통로다.
// npm run build 실행 시 prebuild로 자동 호출된다 (package.json 참고).
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const articlesPath = path.join(root, 'src/data/articles.json')
const indexPath = path.join(root, 'index.html')

const START = '<!-- ARTICLES:START -->'
const END = '<!-- ARTICLES:END -->'

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

const articles = JSON.parse(readFileSync(articlesPath, 'utf8'))

const categories = []
for (const a of articles) {
  if (!categories.includes(a.category)) categories.push(a.category)
}

const body = categories
  .map((category) => {
    const items = articles
      .filter((a) => a.category === category)
      .map(
        (a) =>
          `          <li><a href="/${esc(a.slug)}.html">${esc(a.title)}</a><span class="fb-date">${esc(a.date)}</span></li>`,
      )
      .join('\n')
    return `        <div class="fb-article-group">\n          <h3>${esc(category)}</h3>\n          <ul class="fb-article-list">\n${items}\n          </ul>\n        </div>`
  })
  .join('\n')

const generated = `${START}\n${body}\n        ${END}`

const html = readFileSync(indexPath, 'utf8')
const pattern = new RegExp(`${START}[\\s\\S]*?${END}`)
if (!pattern.test(html)) {
  throw new Error(`index.html에서 ${START} / ${END} 마커를 찾지 못했습니다.`)
}
writeFileSync(indexPath, html.replace(pattern, generated))
console.log(`[gen-index-articles] ${articles.length}개 글, ${categories.length}개 카테고리로 index.html 갱신 완료`)
