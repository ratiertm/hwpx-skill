# 한글 문서 웹 배포 아키텍처 분석

**작성일**: 2026-04-16
**목표**: Claude Web/Desktop에서 한글(.hwpx) 파일 생성·편집·프리뷰를 "모든 사람"이 설치 없이 쓰게 만들기

---

## MCP 아키텍처 기본 개념 (먼저 이해해야 할 것)

### 방향성: LLM이 클라이언트, MCP 서버가 도구 창고

```
┌──────────────┐         MCP          ┌──────────────┐
│ LLM (Claude) │ ◄──────protocol────► │ MCP Server   │
│   = 클라이언트│                      │  = 도구 제공 │
└──────────────┘                      └──────────────┘
```

- **LLM은 MCP 클라이언트** — Claude.ai, Claude Desktop, Claude Code가 이미 내장
- **MCP 서버는 "도구 창고"** — LLM이 호출할 수 있는 함수들만 노출
- 서버 자체에는 LLM 없음. `analyze_form(file)` 같은 함수 실행 엔진일 뿐

### 동작 흐름

```
사용자: "이 hwpx 양식 채워줘"
    ↓
Claude.ai (LLM, 이미 존재)
    ↓ MCP 도구 호출
Cloudflare Workers (MCP 서버)
    ↓ WASM + 로직 실행
rhwp + pyhwpxlib 포팅 코드
    ↓ 결과 JSON
Claude.ai가 결과 해석 → 사용자 응답
```

**Claude = 두뇌, Workers = 손.** Workers에 LLM을 따로 넣을 필요 없음.

### 사용자 연결 방법
Claude.ai Settings → Connectors → Add custom connector → URL:
```
https://hangul-docs.your-domain.com/mcp
```
끝. 사용자의 Claude 구독이 LLM 비용 부담.

---

## 비즈니스 모델 선택: A vs B

| 구분 | A. MCP 서버만 | B. 독립 AI 서비스 |
|------|---------------|-------------------|
| **LLM 주체** | 사용자의 Claude 구독 | 우리가 API 호출 |
| **LLM 비용** | 사용자 부담 (0원, 자기 Claude Pro) | 우리 부담 (종량제) |
| **인프라 비용** | Workers 호스팅만 (월 $0~$10) | Workers + LLM API (토큰당 과금) |
| **사용자 진입** | Claude 구독 필수 | Claude 없어도 사용 가능 |
| **수익 모델** | Freemium (대용량만 유료) | 구독제 필수 |
| **개발 범위** | MCP 도구만 구현 | 대화 UI + 프롬프트 엔지니어링 + 결제 |
| **타겟** | AI 파워유저 | 일반 공무원/직장인 |
| **권장 시작점** | ✅ 1순위 (공수 작고 리스크 낮음) | Phase 6+ (A 검증 후) |

### 추천: A로 시작, B 병행 가능성 열어두기
- **A**: 기술 리스크 작고 Claude 생태계 편승 효과
- **B**: "Claude 모르는 일반인"까지 타겟하려면 필요. 하지만 LLM 비용·프롬프트 품질·UX까지 전부 직접 책임져야 함
- A의 MCP 도구를 잘 만들어두면, B를 얹을 때 그대로 재사용 가능 (도구는 그대로, 위에 LLM 오케스트레이션만 추가)

---

## 핵심 구조 — 3층 분리

```
┌─────────────────────────────────────────────────────────┐
│ 브라우저 (Claude.ai / 독립 웹앱)                         │
│  ┌─────────────────────┐    ┌──────────────────────┐    │
│  │ rhwp 에디터 (iframe)│    │ hwpx skill UI        │    │
│  │ - 편집/뷰어         │    │ - 양식 분석          │    │
│  │ - SVG 렌더링        │    │ - 라벨 매핑          │    │
│  └─────────────────────┘    └──────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                    ↕ Remote MCP (HTTP/SSE)
┌─────────────────────────────────────────────────────────┐
│ Oracle Cloud VM — hangul-docs MCP Server                │
│  - 현재 Python pyhwpxlib + FastMCP 그대로               │
│  - analyze_form, fill_form, patch, to_json, from_json   │
│  - wasmtime + resvg_py (현재 스택 유지)                 │
└─────────────────────────────────────────────────────────┘
```

> **결정**: Oracle Cloud VM 우선. Cloudflare Workers는 옵션 2.
> 이유: pyhwpxlib JS 포팅(3-4주) 불필요. Python 스택 그대로 HTTP 래핑만 필요.

## 레이어별 역할

| 레이어 | 담당 | 현재 상태 | 조치 |
|--------|------|----------|------|
| **렌더링 엔진** | rhwp (Rust→WASM) | ✅ 완성, `edwardkim.github.io/rhwp/` 호스팅 중 | 재사용 |
| **HWPX 비즈니스 로직** | hwpx skill + pyhwpxlib | 🟡 Python 완성 / JS 포팅 필요 | **포팅이 핵심 공수** |
| **MCP 서버 호스팅** | Oracle Cloud VM (1순위) / Cloudflare Workers (옵션) | ❌ 미구현 | 신규 구축 |
| **Claude 연결** | Remote MCP URL 등록 | 자동 | Workers URL만 제공 |

---

## 왜 이 조합인가

### 사용자 분포와 진입 장벽

| 사용자 | 비율 추정 | 진입 장벽 허용치 |
|--------|----------|------------------|
| 일반 직장인(공무원 등 HWPX 주 사용자) | 80% | **0이어야 함** — "파이썬 설치"에서 이탈 |
| 개발자 | 15% | npm/pip 설치 OK |
| AI 파워유저 | 5% | MCP JSON 편집 OK |

### 대안 비교

| 옵션 | 사용자 설치 장벽 | 개발 공수 | Claude 통합 | 종합 |
|------|-----------------|----------|-------------|------|
| 1. 웹앱만 (브라우저 JS+WASM) | 0 | 중 | ❌ 직접 연결 불가 | 반쪽 |
| 2. **Oracle VM Remote MCP (Python)** | 0 (URL만) | **낮음** (수일) | ✅ 전부 | **최적** |
| 3. Cloudflare Workers Remote MCP | 0 (URL만) | 높음 (3-4주, JS 포팅) | ✅ 전부 | 옵션 |
| 4. Node MCP stdio | npm 필요 | 중 | 개발자만 | 보조 |
| 5. Python MCP stdio (현재) | 파이썬+의존성 | 0 | 개발자만 | 초기만 |

### Oracle VM vs Cloudflare Workers 상세 비교

| 항목 | Oracle Cloud VM | Cloudflare Workers |
|------|-----------------|---------------------|
| **Python 그대로 사용** | ✅ 현재 pyhwpxlib 그대로 | ❌ JS/TS 포팅 필수 |
| **초기 공수** | 수일 (HTTP 래퍼만) | 3-4주 (전체 포팅) |
| **운영 부담** | TLS/업데이트/로그 직접 | 0 (완전 관리형) |
| **글로벌 지연** | 한국 사용자 OK | 엣지 배포로 빠름 |
| **실행 시간 제한** | 없음 | 30초 (유료), 10ms CPU (무료) |
| **파일 저장** | 로컬 디스크 자유 | R2/외부 필요 |
| **비용 (저트래픽)** | Free Tier 영구 (4 cores, 24GB RAM) | 월 10만 요청 무료 |
| **스케일링** | 수동 | 자동 무제한 |

**결정 근거**: pyhwpxlib JS 포팅 공수(3-4주) 절감이 결정적.  
트래픽 증가 또는 글로벌 사용자 요구 시 Workers 이관 검토.

---

## rhwp 번들 분석

### 발견: 이미 호스팅된 공개 에디터 존재
- `https://edwardkim.github.io/rhwp/` — GitHub Pages 배포
- 라이선스: **MIT** — 재사용/재배포/포크 자유 (기여자 크레딧 유지 필요)

### 자산 구조 (`/Users/leeeunmi/Projects/active/rhwp/`)

```
rhwp/
├── web/                    # 독립 웹앱 (정적 HTML+WASM)
│   ├── index.html          # 뷰어
│   ├── editor.html         # 편집 (editor.js 74KB)
│   ├── rhwp.js             # wasm-bindgen glue (60KB)
│   ├── rhwp_bg.wasm        # (wasm-pack 빌드 산출물)
│   ├── app.js, editor.js, text_selection.js, format_toolbar.js ...
│   └── fonts/
│
├── npm/editor/             # @rhwp/editor (iframe 래퍼 npm 패키지)
│   ├── index.js            # createEditor() — iframe + postMessage
│   └── index.d.ts          # TypeScript 타입
│
└── rhwp-studio/            # 에디터 본체
```

### WASM API 표면

**HwpDocument 클래스 (50+ 메서드)**
- 렌더링: `renderPageSvg`, `renderPageCanvas`, `renderPageHtml`, `renderPageToCanvas`
- 편집: `applyCharFormat`, `applyParaFormat`, `deleteText`, `splitParagraph`, `splitTableCell`
- 파일: `createEmpty`, `exportHwp`, `loadFile`
- 양식: `findOrCreateFontId`, `setFallbackFont`, `convertToEditable`

**HwpViewer 클래스** — 뷰포트·페이지네이션

### postMessage 프로토콜 (기정의)
```js
{ type: 'rhwp-request',  id, method, params }
  ↓
{ type: 'rhwp-response', id, result | error }
```
현재 지원: `ready`, `loadFile`, `pageCount`, `getPageSvg`

---

## 역할 분리 원칙

- **rhwp** = 뷰어/에디터 (렌더링에 특화)
- **hwpx skill (pyhwpxlib)** = 엔진 (라벨 기반 양식 채우기, JSON 라운드트립, 프리셋 등 rhwp에 없는 기능)

HWPX skill의 강점(fill_by_labels, form_pipeline, presets)은 rhwp에 없음 → **rhwp 포크 대신 병행 서비스**가 자연스러움.

---

## 로드맵

### Phase 1: Oracle VM에 Remote MCP 배포 (3-5일)
- [ ] FastMCP 트랜스포트 변경: `mcp.run(transport="sse", host="0.0.0.0", port=8000)`
- [ ] 인증 토큰 미들웨어 추가 (MCP 보안)
- [ ] 도메인 확보 + nginx 리버스 프록시 + Let's Encrypt TLS
- [ ] systemd 서비스 등록 (상시 구동, 자동 재시작)
- [ ] Rate limit, 파일 크기 제한, 디스크 정리 cron
- [ ] 로그/모니터링 설정

### Phase 2: Claude 연결 및 사용자 온보딩 (1-2일)
- [ ] Claude.ai Connector 등록 가이드 문서
- [ ] Claude Desktop `claude_desktop_config.json` 예시 제공
- [ ] 한국어 README + 스크린샷

### Phase 3: 웹 UI (1-2주)
- [ ] 파일 업로드 + 프리뷰 (rhwp iframe 임베드)
- [ ] 양식 필드 자동 감지 + 편집 폼
- [ ] "Claude와 연결" 버튼 → Remote MCP URL 복사

### Phase 4: 배포/공개 (1주)
- [ ] Anthropic MCP Directory 등록
- [ ] 문서 사이트 (사용법, 한글 사용자 온보딩)
- [ ] (선택) `pyhwpxlib` PyPI 배포 — 파워유저용 보조

### Phase 5: 수익 모델 (장기, 모델 A 기준)
- 무료 사용 한도 + 유료 API (대량 변환)
- 기업용 온프레미스 배포 패키지

### Phase 6+: 모델 B 확장 (선택)
- Claude 구독 없는 일반 사용자 타겟
- Workers에 Anthropic API 키 + 대화 UI 추가
- 한글 문서 특화 프롬프트 엔지니어링
- 구독 결제 연동 (Stripe 등)
- A의 MCP 도구를 내부적으로 재사용

---

## 결정 포인트 (미결)

1. **도메인**: 어디서 확보? (hangul-docs.ai, hwpx.ai 등)
2. **포팅 언어**: JS/TS vs WASM으로 Python 그대로 돌리기(Pyodide)
   - JS/TS 포팅 권장 (Workers 호환, 속도)
   - Pyodide는 초기 로딩 느림, Workers 무료 한도 초과 위험
3. **rhwp 포크 vs 원본 의존**: 원본 의존 시 Edward Kim의 API 변경 리스크
4. **기여**: rhwp에 `fillForm`, `analyzeForm` 메서드 PR 제출 vs 자체 유지

---

## 참고

- rhwp 원본: `https://github.com/edwardkim/rhwp`
- 라이브 데모: `https://edwardkim.github.io/rhwp/`
- pyhwpxlib 현황: `/Users/leeeunmi/Projects/active/hwpx-skill/pyhwpxlib/`
- 현재 MCP 서버 (stdio, 로컬): `pyhwpxlib/mcp_server/server.py`
- Anthropic Remote MCP 가이드: Claude.ai Settings → Connectors
