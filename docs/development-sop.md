# Development Standard Operation Protocol (SOP)

SbioChat Dashboard 개발 시 적용하는 원칙과 절차를 정리한 문서입니다.
Claude Code와 협업하거나 새 팀원이 합류할 때 참조합니다.

---

## 1. 개발 환경 구조

```
Host (WSL2 Ubuntu)
├── Docker Compose
│   ├── postgres (pgvector:pg16)     → port 5435
│   ├── backend (FastAPI/Python)     → port 8005
│   └── frontend (React/Vite)        → port 3005
└── Conda (Open WebUI)               → port 30072
```

### 핵심 원칙
- **모든 서비스는 Docker로 관리한다** (DB, Backend, Frontend)
- Open WebUI만 conda 환경에서 직접 서빙 (테스트 데이터 생성 목적)
- 포트 5432는 사내 운영 PostgreSQL이므로 **절대 사용하지 않는다**

### Hot Reload
소스 코드 변경이 즉시 반영되도록 Docker volume mount를 사용한다:

| 서비스 | Host 경로 | Container 경로 | 반영 방식 |
|--------|-----------|----------------|-----------|
| Backend | `./backend/app` | `/app/app` | uvicorn `--reload` |
| Frontend | `./frontend/src` | `/app/src` | Vite HMR |

`package.json`, `requirements.txt`, `Dockerfile` 변경 시에만 `docker compose up --build` 필요.

---

## 2. 기술 스택 & 패턴

### Backend (FastAPI)
- **단일 파일 구조**: `backend/app/main.py`에 모든 엔드포인트
- **Raw SQL**: SQLAlchemy `text()`로 직접 쿼리 작성 (ORM 모델 사용하지 않음)
- **DB 의존성**: `get_db()` 제너레이터로 세션 관리
- **인증 의존성**: `get_current_user()` — `AUTH_MODE`에 따라 mock/SSO 분기
- **테이블 자동 생성**: `@app.on_event("startup")`에서 `CREATE TABLE IF NOT EXISTS`
- **시간대**: 모든 시간은 `Asia/Seoul` (KST) 기준으로 변환하여 반환

### Frontend (React + TypeScript)
- **UI 프레임워크 없음**: Tailwind CSS만 사용 (shadcn, MUI 등 미사용)
- **아이콘**: lucide-react
- **HTTP 클라이언트**: axios (`frontend/src/lib/api.ts`에 집중)
- **상태 관리**: React useState (전역 상태 관리 라이브러리 없음)
- **다크 테마**: Tailwind CSS 변수 기반 (bg-card, text-foreground, border-border 등)
- **카드 스타일 통일**: `rounded-xl border border-border bg-card p-6`

### 코딩 원칙
- **과도한 엔지니어링 금지**: 요청한 것만 구현. 불필요한 추상화, 유틸리티 함수, 에러 핸들링 추가 금지
- **기존 패턴 따르기**: 새 컴포넌트/엔드포인트 추가 시 기존 코드의 스타일과 구조를 따른다
- **주석 최소화**: 코드가 자명한 경우 주석 불필요. 복잡한 비즈니스 로직에만 추가

---

## 3. 인증 (Auth)

### Mock Auth (개발)
```
ENV: AUTH_MODE=mock
```
- Frontend `MockAuthBanner`에서 사용자 전환 (화면 우하단)
- 모든 인증 API 호출에 `X-Auth-User: {email_prefix}` 헤더 포함
- `@samsung.com` 이메일만 허용, prefix 자동 추출
- `ADMIN_USERS` 환경변수로 관리자 지정 (쉼표 구분)

### SSO (운영) — 미구현
```
ENV: AUTH_MODE=sso
```
- Knox Portal (IdP) → Keycloak (SP/IdP, SAML 2.0) → Dashboard (OIDC 2.0)
- 전환 절차: `docs/sso-integration-guide.md` 참조

---

## 4. Docker 운영 절차

### 전체 빌드 & 실행
```bash
docker compose up --build -d
```

### 개별 서비스 재시작
```bash
docker compose restart backend    # Backend만 재시작
docker compose restart frontend   # Frontend만 재시작
```

### 로그 확인
```bash
docker compose logs -f backend    # Backend 로그 실시간
docker compose logs -f frontend   # Frontend 로그 실시간
docker compose logs -f postgres   # DB 로그 실시간
```

### DB 접속
```bash
docker exec -it openwebui-postgres psql -U openwebui_admin -d openwebui
```

### DB 백업
```bash
bash backup_db.sh
```

### 컨테이너 전체 중지
```bash
docker compose down
```

### 데이터 포함 전체 초기화 (주의)
```bash
docker compose down -v   # named volume도 삭제됨 → DB 데이터 유실
```

---

## 5. Git 운영

### 커밋 메시지 컨벤션
```
<동작> <대상> — <상세 설명 (선택)>

예:
Add Require Python Packages feature with mock auth
Switch daily chart to line plot, use emoji labels
Fix authentication bug in login flow
```

### 커밋 시점
- 기능 단위로 커밋 (하나의 논리적 변경 = 하나의 커밋)
- 문서 변경도 코드 변경과 함께 커밋
- `.env` 파일은 **절대 커밋하지 않는다** (민감 정보 포함)

### 브랜치
- `main`: 단일 브랜치로 운영 (현재 규모에서는 충분)

---

## 6. 새 기능 추가 절차

### Backend 엔드포인트 추가
1. `backend/app/main.py`에 엔드포인트 함수 추가
2. 필요 시 Pydantic 모델 (request/response body) 정의
3. DB 테이블 필요 시 `create_*_table()` startup 이벤트에 DDL 추가
4. curl로 수동 테스트

### Frontend 컴포넌트 추가
1. `frontend/src/lib/api.ts`에 interface + API 함수 추가
2. `frontend/src/components/`에 컴포넌트 파일 생성
3. `frontend/src/pages/Dashboard.tsx`에서 import 및 렌더링
4. 기존 카드 스타일(`rounded-xl border border-border bg-card p-6`) 따르기

### 인증이 필요한 기능
1. Backend: `current_user: str = Depends(get_current_user)` 파라미터 추가
2. Frontend: API 호출 시 `headers: { "X-Auth-User": authUser }` 포함
3. 관리자 전용: `if current_user not in ADMIN_USERS` 체크

---

## 7. 트러블슈팅

### WSL 파일 권한 문제
NTFS 마운트에서 Docker가 root로 파일을 생성하여 호스트에서 수정 불가할 수 있음:
```bash
sudo chmod -R a+rw /mnt/d/openwebui-dashboard/frontend/src/
sudo chmod -R a+rw /mnt/d/openwebui-dashboard/backend/app/
```

### DB 유실 (Windows 재부팅)
Docker named volume(`openwebui_pgdata`)을 사용하여 해결됨.
바인드 마운트(`./data/db`)는 NTFS에서 불안정하므로 사용하지 않는다.

### Frontend 변경 미반영
1. Volume mount 확인: `docker compose config`에서 `./frontend/src:/app/src` 존재 여부
2. 없으면 `docker compose up --build -d frontend`로 리빌드
3. 브라우저 캐시 강제 새로고침: `Ctrl+Shift+R`

### Backend 시작 실패
```bash
docker compose logs backend
```
- DB 연결 실패: postgres healthcheck 확인, 포트/비밀번호 검증
- Import 에러: `requirements.txt`에 패키지 누락 → 추가 후 `--build`

---

## 8. Claude Code 협업 가이드

### 작업 요청 시 포함할 정보
- **무엇을**: 구체적인 기능/변경 사항
- **어디에**: 관련 파일 또는 컴포넌트명
- **제약**: 사용하지 말아야 할 기술/패턴

### Claude Code에 전달할 컨텍스트
- 이 프로젝트는 Docker로 관리됨
- Backend는 raw SQL (ORM 없음)
- Frontend는 Tailwind만 사용 (UI 라이브러리 없음)
- 인증은 `AUTH_MODE`로 mock/sso 분기
- 커밋은 명시적 요청 시에만 수행

### 사내 환경에서의 주의사항
- 포트 5432 사용 금지 (사내 운영 DB)
- `.env` 파일의 비밀번호/시크릿 노출 주의
- SSO 연동은 사내 네트워크에서만 테스트 가능
