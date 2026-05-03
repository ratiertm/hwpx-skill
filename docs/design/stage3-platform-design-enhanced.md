# Stage 3 설계 보강 — HTTP/SSE 트랜스포트 통합

> **근거**: 그래프 분석 Community 175에서 `BearerAuthMiddleware` +
> "hangul-docs MCP Remote Server — Bearer-token 인증을 포함한 HTTP/SSE 트랜스포트로
> FastMCP를 노출" 확인. 이 구현이 이미 프로젝트 소스에 존재함.

---

## 기존 Stage 3와의 차이

| 항목 | 기존 설계 | 보강 설계 |
|------|-----------|-----------|
| Claude Code 접속 | stdio만 | stdio (기본) + HTTP 선택 |
| Claude Desktop 접속 | stdio subprocess | **HTTP/SSE (권장)** + stdio 대안 |
| 서버 생명주기 | 세션마다 spawn/kill | **지속 서버** (한 번 시작) |
| 다중 클라이언트 | 불가 | **동시 접속 가능** |
| 원격 접속 | 불가 | **VPS/홈서버 배포 가능** |
| template 캐싱 | 없음 (매 세션 reload) | **메모리 캐시** (서버 유지) |

**핵심 변화**: stdio는 세션마다 새 프로세스를 spawn해서 상태가 없지만,
HTTP/SSE는 서버가 지속 실행되므로 template 목록을 메모리에 캐싱할 수 있다.

---

## 구성 재정리

```
Stage 3 (보강)
  ├── 3-A: MCP server 확장 (기존 유지)
  │     └── template_workspace / template_context / template_save_session 추가
  │
  ├── 3-B: Claude Code 통합 (기존 유지)
  │     └── stdio가 기본 — bash tool 직접 사용 가능하므로 HTTP 불필요
  │
  ├── 3-C: Claude Desktop 통합 (보강)
  │     ├── Option A: stdio subprocess (기존, 단순)
  │     └── Option B: HTTP/SSE (신규 권장) — 상태 유지, 빠른 응답
  │
  └── 3-D: Remote HTTP/SSE 서버 (신규)
        ├── Local: localhost:8765 — Claude Code + Desktop 공유
        └── Remote: VPS/홈서버 — 다중 기기 접속 (SaaS 전단계)
```

---

## Stage 3-C 보강 — Claude Desktop HTTP/SSE

### 기존 stdio 방식 (Option A, 단순)

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "hangul-docs": {
      "command": "python",
      "args": ["-m", "pyhwpxlib.mcp_server.server"]
    }
  }
}
```

**단점**:
- Claude Desktop이 대화마다 새 Python 프로세스 spawn
- 서버 시작 오버헤드 (~1–2초)
- template 목록을 매번 파일에서 재읽기
- 단일 클라이언트만 접속 가능

---

### HTTP/SSE 방식 (Option B, 권장)

#### 1단계: 서버 시작

```bash
# 환경변수로 토큰 설정
export MCP_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "MCP_TOKEN=$MCP_TOKEN" >> ~/.zshrc  # 또는 ~/.bashrc

# 서버 시작 (백그라운드)
python -m pyhwpxlib.mcp_server.remote_server --port 8765 &

# 또는 launchd로 자동 시작 (macOS)
```

#### 2단계: Claude Desktop 연결

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "hangul-docs": {
      "url": "http://localhost:8765/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

**장점**:
- 서버가 상시 실행 → Claude Desktop 응답 즉시
- template 목록 메모리 캐시 → `template_workspace()` 매우 빠름
- Claude Code + Claude Desktop 동시 접속 가능
- 추후 원격 배포로 전환 시 URL만 변경

---

## Stage 3-D: Remote HTTP/SSE 서버 (신규)

### remote_server.py 구조 (Community 175 기반)

```python
"""hangul-docs MCP Remote Server

Bearer-token 인증을 포함한 HTTP/SSE 트랜스포트로 FastMCP를 노출.
stdio(server.py)와 동일한 mcp 인스턴스를 공유 — tool 목록 동일.

실행:
  python -m pyhwpxlib.mcp_server.remote_server
  python -m pyhwpxlib.mcp_server.remote_server --port 8765 --host 0.0.0.0

환경변수:
  MCP_TOKEN  Bearer 인증 토큰 (필수)
  MCP_PORT   포트 (기본 8765)
  MCP_HOST   바인드 주소 (기본 127.0.0.1, 원격 시 0.0.0.0)
"""
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# server.py의 mcp 인스턴스 재사용 (tool 목록 동일)
from pyhwpxlib.mcp_server.server import mcp


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Bearer token 인증 미들웨어."""
    def __init__(self, app, token: str):
        super().__init__(app)
        self.token = token

    async def dispatch(self, request, call_next):
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {self.token}":
            return Response("Unauthorized", status_code=401,
                          media_type="text/plain")
        return await call_next(request)


def create_app(token: str):
    """Bearer 인증이 적용된 FastMCP HTTP 앱 생성."""
    # FastMCP의 streamable-http Starlette 앱
    app = mcp.streamable_http_app()
    app.add_middleware(BearerAuthMiddleware, token=token)
    return app


if __name__ == "__main__":
    import argparse, uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", 8765)))
    args = parser.parse_args()

    token = os.environ.get("MCP_TOKEN")
    if not token:
        raise SystemExit("MCP_TOKEN 환경변수 필수")

    app = create_app(token)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
```

---

### 배포 패턴 3종

#### 패턴 A: Local (단일 기기)

```
사용 시나리오: MacBook 한 대에서 Claude Code + Claude Desktop 동시 사용
            template 캐싱 이점, stdio 대비 빠른 응답

실행:
  MCP_TOKEN=xxx python -m pyhwpxlib.mcp_server.remote_server --host 127.0.0.1

접속:
  Claude Desktop: http://localhost:8765/mcp
  Claude Code:    claude mcp add hangul-docs --url http://localhost:8765/mcp \
                    --header "Authorization: Bearer xxx"
```

#### 패턴 B: LAN (사무실/홈네트워크)

```
사용 시나리오: 데스크탑에 서버, 노트북/태블릿에서 접속
            hwpx 파일은 공유 드라이브에 있음

실행 (데스크탑):
  MCP_TOKEN=xxx python -m pyhwpxlib.mcp_server.remote_server --host 0.0.0.0 --port 8765

접속 (노트북):
  Claude Desktop: http://192.168.1.100:8765/mcp
```

> **주의**: LAN 배포 시 토큰 유출 주의. `MCP_TOKEN`은 충분히 긴 랜덤 문자열 사용.
> HTTPS 미적용 시 평문 전송 — 신뢰할 수 있는 내부망에서만 사용.

#### 패턴 C: Remote VPS (SaaS 전단계)

```
사용 시나리오: VPS/홈서버에 상시 배포, 어디서든 접속
            ngrok 또는 Cloudflare Tunnel로 HTTPS 래핑

구성:
  VPS에서:
    MCP_TOKEN=xxx python -m pyhwpxlib.mcp_server.remote_server --host 0.0.0.0
    # HTTPS: Caddy/nginx 역방향 프록시 or Cloudflare Tunnel

  Claude Desktop (어디서든):
    {"url": "https://hwpx.yourdomain.com/mcp",
     "headers": {"Authorization": "Bearer xxx"}}
```

> **Phase**: Stage 3에서는 Local만 구현. LAN/Remote는 Stage 4 이후(SaaS 단계).

---

### macOS launchd 자동 시작 (선택)

파일: `~/Library/LaunchAgents/com.mindbuild.hwpx-mcp.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mindbuild.hwpx-mcp</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/python3</string>
    <string>-m</string>
    <string>pyhwpxlib.mcp_server.remote_server</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>8765</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>MCP_TOKEN</key>
    <string>YOUR_TOKEN_HERE</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/hwpx-mcp.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/hwpx-mcp-err.log</string>
</dict>
</plist>
```

```bash
# 등록
launchctl load ~/Library/LaunchAgents/com.mindbuild.hwpx-mcp.plist

# 상태 확인
launchctl list | grep hwpx-mcp

# 로그 확인
tail -f /tmp/hwpx-mcp.log
```

로그인 시 자동 시작 → Claude Desktop을 열면 서버가 이미 준비되어 있음.

---

## stdio vs HTTP/SSE 선택 가이드

| 상황 | 권장 방식 | 이유 |
|------|-----------|------|
| Claude Code만 사용 | stdio | bash tool 직접 호출 가능, 복잡도 ↓ |
| Claude Desktop만 사용 | HTTP/SSE | 서버 spawn 오버헤드 제거 |
| 둘 다 사용 | HTTP/SSE | 하나의 서버 공유 |
| 원격/다기기 | HTTP/SSE | stdio 불가 |
| 빠른 시작/테스트 | stdio | 설정 간단 |

---

## template 캐싱 설계 (HTTP/SSE 전용 이점)

서버가 지속 실행되므로 template 목록을 메모리에 캐싱할 수 있다.

```python
# remote_server.py에 추가 (server.py의 mcp와 동일 인스턴스)

from functools import lru_cache
import time

_template_cache: dict = {}
_cache_ts: float = 0
_CACHE_TTL = 30  # 30초 캐시

def get_cached_templates() -> list:
    """template list를 30초 캐싱."""
    global _template_cache, _cache_ts
    now = time.time()
    if now - _cache_ts > _CACHE_TTL:
        from pyhwpxlib.templates import list_templates
        _template_cache = list_templates()
        _cache_ts = now
    return _template_cache
```

**효과**:
- `template_workspace()` 첫 호출: 파일 읽기 (~20ms)
- 이후 30초간: 메모리 반환 (~0.1ms)
- Claude Desktop에서 세션 시작 시 체감 응답 속도 개선

---

## 동작 흐름 비교

### stdio (기존)
```
Claude Desktop 세션 시작
  ↓ Python 프로세스 spawn (~1초)
  ↓ pyhwpxlib import (~0.5초)
  ↓ template_workspace() → 파일 읽기
  ↓ 결과 반환
세션 종료 → 프로세스 kill
다음 세션 → 처음부터 반복
```

### HTTP/SSE (보강)
```
macOS 로그인 시 서버 자동 시작 (launchd)
  ↓ pyhwpxlib import 완료, 대기 중

Claude Desktop 세션 시작
  ↓ HTTP POST /mcp (0.01초)
  ↓ template_workspace() → 캐시 반환 (0.1ms)
  ↓ 결과 반환

세션 종료 → 서버는 계속 실행
다음 세션 → 즉시 응답
```

---

## 변경 파일 목록 (보강분)

| 파일 | 변경 타입 | 내용 |
|------|-----------|------|
| `pyhwpxlib/mcp_server/remote_server.py` | 신규 | HTTP/SSE 서버 (Community 175 구현체) |
| `pyhwpxlib/mcp_server/server.py` | 수정 | template tools 추가 (3-A 기존 유지) |
| `~/Library/.../claude_desktop_config.json` | 수정 | url 방식으로 변경 |
| `~/Library/LaunchAgents/com.mindbuild.hwpx-mcp.plist` | 신규 | 자동 시작 설정 |
| `~/.claude/claude.json` | 수정 | HTTP 접속으로 변경 (선택) |

---

## 구현 순서

```
Stage 3-A (기존): MCP server tools 추가 (template 3종)
  ↓
Stage 3-D (신규): remote_server.py 작성 (Community 175 구현)
  ↓
Stage 3-B (기존): Claude Code — stdio 유지 또는 HTTP 전환
  ↓
Stage 3-C (보강): Claude Desktop — HTTP/SSE 연결 설정
  ↓
선택: launchd 자동 시작 등록
```

> **Stage 1(template CLI) 완료가 전제**.  
> `template_workspace/context/save_session` MCP tool이 `template context/annotate/log-fill` CLI를 호출하므로.
