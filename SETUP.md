# FomoBot

KOSPI·NASDAQ 기간별 상승률 랭킹 서비스. **투자 조언이 아닙니다.**

## 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | React + Vite → Vercel |
| 백엔드 | FastAPI + PostgreSQL → Railway |
| 배치 | Railway Cron (독립 프로세스) |
| 모니터링 | Sentry (에러), UptimeRobot (uptime/데이터 신선도) |

---

## 로컬 개발

```bash
# 백엔드
cd backend-stock
cp .env.example .env          # 필요한 값 채우기
uv sync
uv run alembic upgrade head
uv run uvicorn fomobot.main:app --reload

# 로컬에서 배치 스케줄러도 함께 돌리려면 .env 에 추가:
# ENABLE_SCHEDULER=true

# 프론트엔드 (별도 터미널)
cd frontend
npm ci
npm run dev
```

---

## 배포

### 백엔드 — Railway

1. Railway 프로젝트 생성 → GitHub 저장소 연결
2. **Root Directory**: `backend-stock`
3. Railway 가 `backend-stock/Dockerfile` 을 자동 감지해 빌드
4. **PostgreSQL 서비스** 추가 → `DATABASE_URL` / `DATABASE_URL_SYNC` 환경변수 설정
5. 아래 환경변수 설정:

```
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql+psycopg2://...
APP_ENV=production
ALLOWED_ORIGINS=https://your-frontend.vercel.app
SENTRY_DSN=https://...@sentry.io/...
ENABLE_SCHEDULER=false
HEALTH_STALE_HOURS=25
```

#### Railway Cron 서비스 추가

Dashboard > **New Service > Cron** 으로 두 개의 Cron 서비스를 추가한다.
같은 이미지(웹 서비스와 동일 Dockerfile)를 사용하고 커맨드만 다르게 지정한다.

**KOSPI 수집**
```
Schedule : 0 9 * * 1-6
Command  : python -m fomobot.jobs.collect kospi
```
> 09:00 UTC = 18:00 KST.
> KOSPI 장 마감 15:30 KST(= 06:30 UTC) 기준 +2.5h.
> 한국은 서머타임 없으므로 연중 고정.

**NASDAQ 수집**
```
Schedule : 30 21 * * 1-5
Command  : python -m fomobot.jobs.collect nasdaq
```
> 21:30 UTC = 다음날 06:30 KST.
> NASDAQ 정규장 마감 16:00 EST = 21:00 UTC 기준 +30분,
> 서머타임(EDT) 기준 16:00 EDT = 20:00 UTC 기준 +90분.
> EST/EDT 양쪽에서 모두 마감 이후가 되는 단일 시각으로 선택.
> 두 개의 계절별 cron 으로 나누지 않아도 무방.

#### 초기 히스토리 데이터 수집

최초 배포 후 Railway 콘솔에서 1회 실행:
```bash
python scripts/init_history.py
```

> Railway Dashboard의 **Root Directory** 설정이 `backend-stock`인지 반드시 확인할 것.

---

### 프론트엔드 — Vercel

1. Vercel 프로젝트 생성 → GitHub 저장소 연결
2. **Root Directory**: `frontend`
3. Vercel 이 `frontend/vercel.json` 을 자동 감지
4. **Environment Variables** 설정:

```
VITE_API_BASE_URL=https://your-backend.up.railway.app
```

---

## 헬스체크 — UptimeRobot

`GET /health` 엔드포인트를 모니터링한다.

- 정상: `200 {"status": "ok", "last_updated": "2026-06-24"}`
- 비정상: `503 {"status": "unhealthy", "reason": "stale_data", ...}`
  - 마지막 랭킹 스냅샷이 `HEALTH_STALE_HOURS`(기본 25h) 이상 지난 경우
  - 배치 실패로 데이터가 멈춰 있어도 화면은 어제 데이터로 정상처럼 보이므로 이 엔드포인트로 감지

UptimeRobot 설정:
- Monitor Type: **HTTP(s)**
- URL: `https://your-backend.up.railway.app/health`
  (부동산 확장 시에도 `/health` 경로 유지 — 응답 body에 도메인별 필드 추가)
- Interval: 5분
- Alert condition: status code `!= 200`

---

## 프로젝트 구조

```
FomoBot/
├── backend-stock/               # 주식 백엔드 (Railway)
│   ├── src/fomobot/
│   │   ├── main.py              # FastAPI 앱 진입점 (/health, /api/stock/*)
│   │   ├── config.py            # pydantic-settings 기반 설정
│   │   ├── sentry_init.py       # 웹/배치 공용 Sentry 초기화
│   │   ├── api/                 # HTTP 엔드포인트 (/api/stock/rankings, /api/stock/backtest)
│   │   ├── batch/               # 수집·계산 로직 (웹 서버와 독립)
│   │   ├── jobs/
│   │   │   └── collect.py       # Railway Cron 진입점
│   │   ├── db/                  # ORM 모델, 세션, CRUD
│   │   └── services/            # 금융 계산, 노이즈 필터
│   ├── Dockerfile
│   ├── railway.toml
│   └── .env.example
└── frontend/
    ├── src/
    ├── vercel.json
    └── vite.config.ts
```
