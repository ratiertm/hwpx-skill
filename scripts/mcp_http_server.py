"""hangul-docs MCP Remote Server

Bearer-token 인증을 포함한 HTTP/SSE 트랜스포트로 FastMCP를 노출.

환경변수:
  HANGUL_DOCS_TOKEN  필수. Bearer 토큰.
  HANGUL_DOCS_HOST   기본 127.0.0.1
  HANGUL_DOCS_PORT   기본 8001
  HANGUL_DOCS_TRANSPORT  http | sse | streamable-http (기본 streamable-http)
"""
from __future__ import annotations

import os
import sys

import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from pyhwpxlib.mcp_server.server import mcp


TOKEN = os.environ.get("HANGUL_DOCS_TOKEN", "").strip()
if not TOKEN:
    print("ERROR: HANGUL_DOCS_TOKEN 환경변수가 비어있다.", file=sys.stderr)
    sys.exit(1)

HOST = os.environ.get("HANGUL_DOCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("HANGUL_DOCS_PORT", "8001"))
TRANSPORT = os.environ.get("HANGUL_DOCS_TRANSPORT", "streamable-http")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in ("/health", "/"):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"error": "missing bearer token"}, status_code=401)
        if auth[7:].strip() != TOKEN:
            return JSONResponse({"error": "invalid token"}, status_code=403)
        return await call_next(request)


app = mcp.http_app(transport=TRANSPORT)
app.add_middleware(BearerAuthMiddleware)


async def health(request):
    return JSONResponse({"status": "ok", "service": "hangul-docs"})


app.routes.insert(0, type(app.routes[0])(path="/health", endpoint=health, methods=["GET"]))


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
