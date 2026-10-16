# 공유 카드 R2 캐시 삭제 런북

공유 카드(`/og/...png`, `/og/...json`)는 Worker가 R2 버킷 `fomobot-og`에 **영구 캐시**한다.
R2에 한 번 들어간 카드는 backend를 다시 호출하지 않으므로, `price_daily` 정정만으로는
이미 만들어진 카드가 바뀌지 않는다. 종목 정정 작업 때 이 런북으로 해당 종목의 캐시를 지운다.

## 키 구조

```
og/{버전}/{market}/{ticker}/{from}_{to}.png
og/{버전}/{market}/{ticker}/{from}_{to}.json
```

- `{버전}`: `frontend/worker/index.ts`의 `CACHE_VERSION` (현재 `v1`)
- 한 종목의 모든 카드 = prefix `og/v1/{market}/{ticker}/`
- prefix는 **반드시 `/`로 끝낸다.** `og/v1/kospi/00593`처럼 끝을 빼면 `005930`, `005935` 등 다른 종목까지 지워진다.

## 언제, 어떤 순서로

정정 대상 종목이 생기면 아래 순서를 지킨다.

1. **`corporate_action_flag`를 `excluded` 또는 `pending`으로 둔다.**
   이 상태에서는 backend가 `/api/share`, `/api/og`를 404로 막으므로 새 카드가 만들어지지 않는다.
   단, **이미 R2에 있는 카드는 계속 서빙된다**(Worker는 R2 hit이면 backend를 부르지 않음).
2. **이 런북으로 해당 종목 prefix를 삭제한다.** 이 시점부터 그 종목의 공유 링크는 "유효하지 않은 공유 링크"가 된다.
3. `price_daily` 정정.
4. 플래그를 `resolved`로 바꾼다. 이후 요청부터 정정된 값으로 카드가 새로 만들어진다.

2를 3보다 먼저 하는 이유: 플래그가 걸려 있는 동안에는 새 캐시가 생기지 않으므로,
삭제 후 정정까지 시간이 걸려도 오염된 값이 다시 캐시되지 않는다.

## 준비 (최초 1회)

1. **R2 API 토큰 발급**: Cloudflare 대시보드 → R2 → Manage R2 API Tokens → Create API token
   - 권한: **Object Read & Write**
   - 범위: **버킷 `fomobot-og`만** (Apply to specific buckets only)
   - 발급 후 표시되는 Access Key ID / Secret Access Key를 보관한다(Secret은 다시 볼 수 없음).
2. **Account ID 확인**: 대시보드 R2 개요 화면 우측. 엔드포인트는 `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.
3. **aws CLI 설치 후 프로필 등록**:

   ```bash
   aws configure --profile r2
   # AWS Access Key ID:     <R2 Access Key ID>
   # AWS Secret Access Key: <R2 Secret Access Key>
   # Default region name:   auto
   # Default output format: (엔터)
   ```

   aws CLI 2.23 이상은 R2가 지원하지 않는 체크섬을 기본으로 보내므로 `~/.aws/config`의
   `[profile r2]` 아래에 다음 두 줄을 추가한다(R2 문서 권고).

   ```ini
   request_checksum_calculation = when_required
   response_checksum_validation = when_required
   ```

> `wrangler r2 object delete`는 키 하나씩만 지울 수 있고 목록 조회 명령이 없어서
> prefix 단위 삭제에는 쓸 수 없다. 키를 정확히 아는 단건 삭제만 아래 "단건 삭제"를 참고.

## 종목 단위 삭제

아래 예시는 `kospi` / `005930`. bash 기준이며, PowerShell은 줄 끝 `\` 대신 한 줄로 쓴다.

```bash
ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
PREFIX=og/v1/kospi/005930/

# 1) 무엇이 지워질지 먼저 확인
aws s3 ls "s3://fomobot-og/$PREFIX" --recursive --profile r2 --endpoint-url "$ENDPOINT"

# 2) dry-run — 실제로 지우지 않고 대상만 출력
aws s3 rm "s3://fomobot-og/$PREFIX" --recursive --dryrun --profile r2 --endpoint-url "$ENDPOINT"

# 3) 삭제
aws s3 rm "s3://fomobot-og/$PREFIX" --recursive --profile r2 --endpoint-url "$ENDPOINT"

# 4) 비었는지 확인 (출력 없음이 정상)
aws s3 ls "s3://fomobot-og/$PREFIX" --recursive --profile r2 --endpoint-url "$ENDPOINT"
```

예전 버전(`v0` 등)에 남은 같은 종목 카드까지 지우려면 버전 목록을 먼저 본다.

```bash
aws s3 ls "s3://fomobot-og/og/" --profile r2 --endpoint-url "$ENDPOINT"   # PRE v1/ ...
```

예전 버전 키는 Worker가 더 이상 읽지 않으므로 서비스에는 영향이 없다. 저장 용량 정리 목적일 때만 지운다.

## 단건 삭제 (키를 정확히 알 때)

```bash
npx wrangler r2 object delete "fomobot-og/og/v1/kospi/005930/2025-10-15_2026-10-15.png" --remote
npx wrangler r2 object delete "fomobot-og/og/v1/kospi/005930/2025-10-15_2026-10-15.json" --remote
```

- `--remote`를 빼면 wrangler 4는 **로컬 개발용 R2**에서 지우고 끝난다.
- PNG와 JSON은 항상 **쌍으로** 지운다. 하나만 지우면 다음 요청에서 새로 계산된 쪽과 남아 있는 쪽의 숫자가 다를 수 있다.

## R2 밖에 남는 캐시

R2를 지워도 아래 캐시는 남는다. 응답이 `Cache-Control: immutable, max-age=1년`이기 때문이다.

- **이미 카드를 연 사용자의 브라우저 캐시**: 서버에서 지울 방법이 없다.
- **카카오톡 링크 미리보기**: 카카오 [공유 디버거](https://developers.kakao.com/tool/debugger/sharing)에 `/s/...` URL을 넣고 캐시 초기화.
- **Facebook/Threads**: [Sharing Debugger](https://developers.facebook.com/tools/debug/)에서 Scrape Again.
- **X**: 별도 초기화 도구가 없다. 시간이 지나면 다시 수집된다.

## 확인

```bash
# 삭제 후 첫 요청은 MISS(플래그가 걸려 있으면 404)여야 한다
curl -sI "https://fomobot.net/og/kospi/005930.png?from=2025-10-15&to=2026-10-15" | grep -i -E "^HTTP|x-og-cache"
```
