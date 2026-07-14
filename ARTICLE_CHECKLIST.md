# 글 1편 추가 체크리스트

> 이 파일만 던져주면 새 AI 세션도 바로 작업할 수 있게 쓴 것. 순서대로 진행할 것.
> 카테고리는 **데이터 분석 / 방법론 / 개발기** 3개로 고정 — 추가·변경하지 않는다.

---

## 0. 시작 전에 정할 것

- [ ] **제목**, **slug**(영문, `frontend/public/<slug>.html` 파일명이 됨), **카테고리**(3개 중 하나), **발행일**(YYYY-MM-DD), **한 줄 요약**을 정한다.
- [ ] 글 본문을 사용자가 이미 써서 준 경우 — **문장을 한 글자도 바꾸지 않는다.** 오탈자를 발견해도 고치지 말고 사용자에게 보고만 한다.

---

## 1. `frontend/public/<slug>.html` 생성

- [ ] `frontend/public/_article-template.html`을 복사해 `frontend/public/<slug>.html`로 저장한다.
- [ ] `{{TITLE}}` `{{DATE}}` `{{SLUG}}` `{{SUMMARY}}`를 전부 실제 값으로 치환한다 (`{{DATE}}`는 ISO `YYYY-MM-DD`).
- [ ] **`<meta name="robots" content="noindex" />` 줄을 삭제한다.** (템플릿에만 있어야 하는 줄 — 실제 글에 남으면 검색 색인에서 빠진다. 가장 잊기 쉬운 단계이니 커밋 전에 다시 한번 확인.)
- [ ] "본문 작성 위치" 사이에 글을 쓴다. 공용 클래스는 `.data-table`(표) / `.pull`(강조 인용) / `h2`(소제목) — 전부 `static-page.css`에 이미 정의돼 있으니 새로 스타일을 만들지 않는다.
- [ ] `footnotes` 블록: `{{DIVIDEND_NOTE}}` `{{UPDATE_POLICY_NOTE}}`를 채우거나, 해당 없으면 그 `<p>` 문단째 삭제한다. 나머지 3개(데이터 기준/생존 편향/투자 판단)는 문구를 손대지 않는다 — 사이트 전체에서 동일해야 하는 고정 문구다.
- [ ] "전체 랭킹 보기" 류 CTA 링크를 쓴다면, 글 주제에 맞는 쿼리 파라미터로 맞춘다.
  - 예: 주식·코스피·5년 랭킹 글 → `/?tab=stock&market=kospi&period=1825d`
  - 지원되는 쿼리: `tab`(`stock`|`realestate`), `market`(`kospi`|`nasdaq`, stock 탭에서만), `period`(`1d`|`7d`|`30d`|`90d`|`365d`|`1825d`, stock 탭에서만). 부동산 탭 쿼리(`seg`/`min_price`/`max_price`)는 `frontend/src/App.tsx`의 `reSeg`/`reMinPrice`/`reMaxPrice` `useState` 초기화 로직 참고.
  - 해당 사항 없으면 CTA 문단째 삭제.
- [ ] 글 안에 내부 링크(`/methodology.html` 등)를 걸었다면 실제로 존재하는 경로인지 확인한다.

---

## 2. `frontend/public/articles.html` 갱신

- [ ] 해당 카테고리 `<section>`이 **이미 있으면** 그 안의 `<ul class="article-list">`에 새 `<li>`를 추가한다.
- [ ] 해당 카테고리가 **지금 비어 있어서 주석 처리돼 있으면**, 그 `<!-- … -->` 블록의 주석을 해제하고 `<li>`를 채운다.
- [ ] `<li>` 안에는 제목 링크(`href="/<slug>.html"`) / `<span class="article-date">YYYY-MM-DD</span>` / `<p class="article-summary">한 줄 요약</p>` 세 가지만 넣는다.
- [ ] 파일 상단 HTML 주석(새 글 추가 방법 안내)은 그대로 둔다 — 지우지 않는다.

---

## 3. `frontend/public/sitemap.xml` 갱신

- [ ] `<url>` 항목을 추가한다. **`<loc>`와 `<lastmod>`만 정확히** 채우면 된다:
  ```xml
  <url>
    <loc>https://fomobot-dun.vercel.app/<slug>.html</loc>
    <lastmod>YYYY-MM-DD</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  ```
  - `<lastmod>`는 글의 **발행일**(= `datePublished`)을 넣는다. 본문 수치를 사후에 고치지 않으므로 발행 후 갱신하지 않는다.
  - `<priority>`와 `<changefreq>`는 Google이 무시한다. 값은 기존 글과 동일하게 유지하되, 고민할 필요 없다.
  - 글이 추가될 때마다 `articles.html` 항목의 `<lastmod>`도 오늘 날짜로 갱신한다.

---

## 4. `frontend/src/data/latestArticle.ts` 갱신 (조건부)

- [ ] 이번에 추가하는 글이 **지금까지 중 가장 최신 글**이면 `LATEST_ARTICLE` 객체를 이 글로 교체한다 (`href`/`ko.title`/`ko.summary`/`en.title`/`en.summary` 전부).
  - 이 값은 메인 화면 랭킹 리스트 하단의 "읽을거리" 카드(`ArticleTeaser.tsx`)에 그대로 노출된다.
- [ ] 예전 글을 추가하는 경우(백필 등)라면 이 파일은 건드리지 않는다.
- [ ] 이 파일을 고쳤다면 `frontend/`에서 `npx tsc --noEmit`으로 타입 에러 없는지 확인한다.

---

## 5. `BACKLOG.md`, `content-backlog.md` 갱신

- [ ] `## 5. 발행한 글` 섹션에 한 줄 추가: `제목 — 날짜 — 카테고리` 형식.
- [ ] `## 상태 요약` 섹션의 테이블을 갱신한다.

---

## 6. 절대 건드리지 않는 것 (건드리면 구조가 무너짐)

- [ ] **nav / `Footer.tsx`** — 정적 페이지 6종 nav와 `FOOTER_LINKS`에는 글 개별 링크를 추가하지 않는다. "읽을거리" 링크 하나로 `/articles.html`을 가리키는 구조가 글이 몇 편이 되든 nav 항목 수를 6개로 고정시키는 핵심이다.
- [ ] **카테고리 개수** — 데이터 분석/방법론/개발기 3개 고정. 새 카테고리가 필요해 보여도 먼저 사용자와 상의한다.
- [ ] **sitemap** — `<loc>`와 `<lastmod>`만 정확히. `priority`/`changefreq`는 Google이 무시하므로 신경 쓰지 않아도 된다. 기존 글의 `<lastmod>`는 발행 후 건드리지 않는다.

---

## 7. 마무리 확인

- [ ] `frontend/`에서 `npx tsc --noEmit` 통과 확인 (`latestArticle.ts`를 고친 경우 필수, 안 고쳤어도 습관적으로 한 번 돌리는 걸 권장).
- [ ] 가능하면 dev 서버로 새 글 페이지 / `articles.html` / 메인 화면 "읽을거리" 카드를 직접 렌더링해 확인한다.
- [ ] 커밋 메시지에 글 제목을 명시한다.
