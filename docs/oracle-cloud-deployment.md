# Oracle Cloud 배포 가이드 — hangul-docs MCP 서버

**배포일**: 2026-04-16
**서버**: Oracle Cloud VM (opc@158.180.83.142)
**도메인**: https://hangul-docs.lchfkorea.com
**상태**: ✅ 운영 중

---

## 1. 서버 환경

| 항목 | 값 |
|------|----|
| OS | Oracle Linux 9.7 (x86_64) |
| Python | 3.12 (`/usr/bin/python3.12`) |
| RAM | 503MB + Swap 4GB |
| Disk | 30GB (47% 사용) |
| 기존 서비스 | postgres(5432), nginx(80/443), phoenix(4000), 8000, 8080, 8443 |
| 신규 포트 | **8001** (hangul-docs 내부) |
| SSH | `ssh -i ssh-key-2026-02-06_v4.0.key opc@158.180.83.142` |

---

## 2. 설치 경로

```
/home/opc/hwpx-skill/              ← git clone
├── .venv/                          ← Python 3.12 venv
├── pyhwpxlib/                      ← 라이브러리 본체
├── scripts/mcp_http_server.py      ← HTTP/SSE 런처 (Bearer 인증)
└── ...

/etc/systemd/system/hangul-docs.service   ← systemd 서비스
/etc/nginx/conf.d/hangul-docs.conf        ← nginx 리버스 프록시
/etc/letsencrypt/live/hangul-docs.lchfkorea.com/  ← TLS 인증서
```

---

## 3. 배포 단계 기록

### 3.1 저장소 클론 & 의존성 설치
```bash
cd ~
git clone https://github.com/ratiertm/hwpx-skill.git
cd hwpx-skill
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[all]"   # fastmcp, wasmtime, resvg-py, fonttools, lxml, Pillow
pip install uvicorn starlette
```

### 3.2 HTTP 런처 작성
파일: `scripts/mcp_http_server.py`

핵심 로직:
- `pyhwpxlib.mcp_server.server.mcp.http_app(transport="streamable-http")` 호출
- Bearer 토큰 미들웨어 (`HANGUL_DOCS_TOKEN` 환경변수)
- `/health` 엔드포인트는 인증 우회

환경변수:
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `HANGUL_DOCS_TOKEN` | (필수) | Bearer 토큰 |
| `HANGUL_DOCS_HOST` | `127.0.0.1` | 바인드 호스트 |
| `HANGUL_DOCS_PORT` | `8001` | 바인드 포트 |
| `HANGUL_DOCS_TRANSPORT` | `streamable-http` | `http` / `sse` / `streamable-http` |

### 3.3 토큰 생성
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
로컬 저장: `/Users/leeeunmi/Projects/active/hwpx-skill/.mcp-token` (0600, gitignore됨)

### 3.4 systemd 서비스 등록

파일: `/etc/systemd/system/hangul-docs.service`
```ini
[Unit]
Description=hangul-docs MCP Server
After=network.target

[Service]
Type=simple
User=opc
WorkingDirectory=/home/opc/hwpx-skill
Environment=HANGUL_DOCS_TOKEN=<토큰>
Environment=HANGUL_DOCS_HOST=127.0.0.1
Environment=HANGUL_DOCS_PORT=8001
Environment=HANGUL_DOCS_TRANSPORT=streamable-http
ExecStart=/home/opc/hwpx-skill/.venv/bin/python /home/opc/hwpx-skill/scripts/mcp_http_server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**🔑 SELinux 처리 (중요!)**:
```bash
sudo chown root:root /etc/systemd/system/hangul-docs.service
sudo chmod 644 /etc/systemd/system/hangul-docs.service
sudo restorecon -v /etc/systemd/system/hangul-docs.service
# /home/opc/ 아래 venv 실행 권한
sudo chcon -R -t bin_t /home/opc/hwpx-skill/.venv/bin/
```

활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hangul-docs
sudo systemctl status hangul-docs
```

### 3.5 nginx 리버스 프록시

파일: `/etc/nginx/conf.d/hangul-docs.conf`
```nginx
server {
    listen 80;
    server_name hangul-docs.lchfkorea.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection '';
        proxy_buffering off;      # SSE/streaming 필수
        proxy_cache off;
        proxy_read_timeout 86400;
        chunked_transfer_encoding on;
    }
}
```

**SELinux**:
```bash
sudo chown root:root /etc/nginx/conf.d/hangul-docs.conf
sudo chmod 644 /etc/nginx/conf.d/hangul-docs.conf
sudo restorecon -v /etc/nginx/conf.d/hangul-docs.conf
sudo nginx -t && sudo systemctl reload nginx
```

### 3.6 DNS 설정 (도메인 레지스트라에서)

```
Type: A
Name: hangul-docs
Value: 158.180.83.142
TTL: 300
```

### 3.7 Let's Encrypt TLS

certbot 경로: `/usr/local/bin/certbot` (Python 3.9 기반 구버전)
```bash
sudo /usr/local/bin/certbot --nginx \
  -d hangul-docs.lchfkorea.com \
  --non-interactive --agree-tos \
  --email ratiertm72@gmail.com \
  --redirect
```

결과: 443 리스너 + 80→443 리다이렉트 자동 설정. 인증서 만료 2026-07-14.

---

## 4. 검증 결과

| 테스트 | 명령 | 기대 | 결과 |
|--------|------|------|------|
| 헬스체크 | `curl https://hangul-docs.lchfkorea.com/health` | 200 | ✅ |
| 인증 없음 | `curl https://.../mcp` | 401 | ✅ |
| 잘못된 토큰 | `curl -H "Authorization: Bearer WRONG" .../mcp` | 403 | ✅ |
| 유효한 토큰 | `curl -H "Authorization: Bearer <TOKEN>" .../mcp` | 400 (Missing session ID — MCP 프로토콜 정상 응답) | ✅ |

---

## 5. 클라이언트 연결

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "hangul-docs": {
      "url": "https://hangul-docs.lchfkorea.com/mcp",
      "headers": {
        "Authorization": "Bearer <TOKEN>"
      }
    }
  }
}
```

> 구버전 Claude Desktop은 Remote MCP 미지원. 이 경우 `mcp-remote` 프록시 사용:
> ```json
> {
>   "mcpServers": {
>     "hangul-docs": {
>       "command": "npx",
>       "args": ["-y", "mcp-remote", "https://hangul-docs.lchfkorea.com/mcp",
>                "--header", "Authorization:Bearer <TOKEN>"]
>     }
>   }
> }
> ```

### Claude.ai 웹
Settings → Connectors → Add custom connector:
- URL: `https://hangul-docs.lchfkorea.com/mcp`
- Authentication: Bearer `<TOKEN>`

---

## 6. 운영

### 로그 확인
```bash
sudo journalctl -u hangul-docs -f
sudo journalctl -u hangul-docs -n 100 --no-pager
```

### 재시작
```bash
sudo systemctl restart hangul-docs
sudo systemctl status hangul-docs
```

### 코드 업데이트
```bash
cd ~/hwpx-skill
git pull
source .venv/bin/activate
pip install -e ".[all]" --upgrade
sudo systemctl restart hangul-docs
```

### TLS 자동 갱신
certbot cron/timer가 기존 `www.lchfkorea.com` 인증서와 함께 처리.
수동 확인:
```bash
sudo /usr/local/bin/certbot renew --dry-run
```

### 헬스체크 모니터링 (권장)
```bash
# crontab -e
*/5 * * * * curl -sf https://hangul-docs.lchfkorea.com/health > /dev/null || echo "hangul-docs DOWN" | mail -s "Alert" ratiertm72@gmail.com
```

---

## 7. 트러블슈팅

### 문제 1: systemd "Permission denied"로 Python 실행 실패
**원인**: SELinux가 `/home/opc/.../python` 바이너리 접근 차단
**해결**:
```bash
sudo chcon -R -t bin_t /home/opc/hwpx-skill/.venv/bin/
```

### 문제 2: nginx conf 로드 실패 (Permission denied)
**원인**: `/tmp`에서 옮긴 파일의 SELinux 라벨이 `user_tmp_t`
**해결**:
```bash
sudo restorecon -v /etc/nginx/conf.d/hangul-docs.conf
```

### 문제 3: 서비스 활성화 시 "Unit file does not exist"
**원인**: SELinux가 `systemd_unit_file_t` 라벨 아닌 파일 무시
**해결**: `restorecon` 적용 후 `daemon-reload`

### 문제 4: 포트 충돌 (8000, 8080, 8443 이미 사용 중)
**해결**: 8001 사용. 추가 확장 시 9000번대 사용 고려.

---

## 8. 미해결 / 다음 할 일

- [ ] **파일 업로드 방식 설계** — 현재 MCP 도구는 서버 로컬 경로(`file` 파라미터)를 받음. 원격 환경에서는:
  - 옵션 A: base64 업로드 파라미터 추가
  - 옵션 B: 업로드 엔드포인트 + temp storage
  - 옵션 C: S3/Presigned URL
- [ ] **Rate limit** — nginx 또는 앱 미들웨어
- [ ] **파일 크기 제한** — nginx `client_max_body_size`
- [ ] **디스크 정리 cron** — 임시 PNG/HWPX 파일 자동 삭제
- [ ] **사용량 메트릭** — 요청 수, 응답 시간, 에러율
- [ ] **Claude Desktop 실제 도구 호출 테스트** — `hwpx_build`, `hwpx_analyze_form`, `hwpx_fill_form`
- [ ] **TLS 자동 갱신 훅** — 갱신 후 nginx reload 확인
- [ ] **백업 정책** — systemd unit, nginx conf, .env 토큰

---

## 9. 보안 체크리스트

- [x] Bearer 토큰 인증
- [x] HTTPS (Let's Encrypt)
- [x] systemd 제한 사용자(`opc`)로 실행
- [x] 내부 포트(8001)는 localhost 바인드
- [ ] nginx rate limit 미설정
- [ ] 파일 업로드 크기 제한 미설정
- [ ] fail2ban 미설정
- [ ] `.mcp-token` 파일을 `key.md`와 분리 저장 (완료)
- [ ] **`key.md`에 노출된 API 키들 전부 회전 권장** (GitHub PAT, Gemini, Claude x2, Discord)

---

## 10. 비용

| 항목 | 비용 |
|------|------|
| Oracle Cloud VM | Free Tier (기존 사용) |
| 도메인 `lchfkorea.com` | 기존 보유 |
| Let's Encrypt TLS | 무료 |
| 추가 운영비 | **$0/월** |

글로벌 트래픽 증가 또는 한국 외 지역 지연 이슈 발생 시 Cloudflare Workers 이관 검토.
