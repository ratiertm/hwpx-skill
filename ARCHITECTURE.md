# hwpx-skill API SaaS 기술 아키텍처 문서

**작성일**: 2026-04-05
**대상**: 2인 개발팀 8주 구현 가이드
**기술 스택**: FastAPI + PostgreSQL + Redis + Celery

---

## 1. 시스템 아키텍처 개요

### 1.1 전체 시스템 구조 (ASCII Diagram)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  (Web Dashboard / Mobile App / Third-party integrations)            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────────┐
│                      API Gateway (NLB)                              │
│  - SSL/TLS termination                                             │
│  - Request routing                                                 │
│  - Rate limiting (DDoS protection)                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────┐  ┌──────────▼────────┐  ┌──────▼──────────┐
│  App Server  │  │  App Server       │  │  App Server     │
│  (FastAPI)   │  │  (FastAPI)        │  │  (FastAPI)      │
│  Instance 1  │  │  Instance 2       │  │  Instance N     │
└───────┬──────┘  └──────────┬────────┘  └──────┬──────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────────┐  ┌──────▼─────────┐  ┌──────▼──────────┐
│   PostgreSQL     │  │   Redis Cache  │  │  Task Queue    │
│   (Replication)  │  │   (Cluster)    │  │  (Celery +     │
│                  │  │                │  │   RabbitMQ)    │
└──────────────────┘  └────────────────┘  └──────┬──────────┘
                                                  │
        ┌─────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────┐
│        Worker Nodes (Celery Workers)         │
│  - Document generation workers               │
│  - AI prompt generation workers             │
│  - Email notification workers               │
│  - Cleanup workers                          │
└───────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────┐
│     External Storage (S3-Compatible)        │
│  - NHN Cloud Object Storage (Primary)       │
│  - AWS S3 Seoul (Backup)                    │
│  - Generated documents & templates          │
└───────────────────────────────────────────────┘
```

### 1.2 데이터 흐름 (각 API 엔드포인트별)

**엔드포인트 1: POST /v1/documents/create-from-markdown**
```
Client Request
    ↓
API Gateway (Rate Limit Check)
    ↓
FastAPI Endpoint Handler
    ↓
Input Validation (Markdown syntax)
    ↓
Create Task → Enqueue to Celery
    ↓
Return Job ID (202 Accepted)
    ↓
Worker Process
    ├→ Parse Markdown
    ├→ Convert to HWPX (pyhwpxlib)
    ├→ Upload to S3
    ├→ Store metadata in PostgreSQL
    ├→ Update job status
    └→ Trigger webhook callback
    ↓
Client polls /v1/jobs/{job_id} → Download URL when ready
```

**엔드포인트 2: POST /v1/forms/fill**
```
Client uploads template HWPX + JSON data
    ↓
API Gateway validation
    ↓
FastAPI Handler
    ├→ Download template from S3 → local temp
    ├→ Validate JSON against template schema
    ├→ Enqueue fill task
    └→ Return job ID
    ↓
Worker Process
    ├→ Load HWPX template (ZIP parse)
    ├→ Extract form_pipeline JSON
    ├→ Fill fields from user data
    ├→ Validate filled document
    ├→ Save result to temp
    ├→ Upload to S3
    └→ Return download URL
    ↓
Client downloads filled document
```

**엔드포인트 3: POST /v1/forms/clone**
```
Client uploads government form (HWPX/OWPML)
    ↓
Validation check (file type, size < 50MB)
    ↓
Enqueue form reverse-engineering task
    ↓
Worker Process
    ├→ Extract form structure (form_pipeline.py)
    ├→ Build JSON schema
    ├→ Generate clean HWPX clone
    ├→ Upload both (original + JSON + cloned HWPX)
    └→ Return extraction result
    ↓
Client receives JSON form definition + cloned HWPX
```

---

## 2. 기술 스택 선택 (한국 B2B SaaS 시장 기준)

### 2.1 웹 프레임워크: FastAPI vs Django vs Flask

| 항목 | FastAPI | Django REST | Flask |
|------|---------|------------|-------|
| **성능** | 매우 빠름 (async/await) | 중간 | 느림 |
| **개발 속도** | 빠름 (자동 문서화) | 매우 빠름 | 느림 |
| **API 문서** | 자동 생성 (Swagger UI) | 수동 작성 | 수동 작성 |
| **타입 힌팅** | 완벽 지원 | 기본 지원 | 없음 |
| **비동기** | 네이티브 | 한정적 | 제한적 |
| **학습곡선** | 낮음 | 가파름 | 낮음 |
| **프로덕션 준비** | 매우 좋음 | 매우 좋음 | 좋음 |

**선택: FastAPI**

**이유:**
- HWPX 문서 생성은 CPU 집약적 → async/await로 스레드 풀 활용 극대화
- 대용량 파일 업로드/다운로드 → 스트리밍 지원 우수
- 자동 OpenAPI 문서 → B2B 클라이언트 온보딩 가속화
- 한국 B2B SaaS 표준 스택 (당근마켓, 토스, 당근마켓 등이 사용)
- 마이크로서비스로 확장 용이

### 2.2 작업 큐: Celery + RabbitMQ vs RQ vs Dramatiq

| 항목 | Celery + RabbitMQ | RQ | Dramatiq |
|------|------------------|-----|----------|
| **메시지 브로커** | RabbitMQ / Redis | Redis only | RabbitMQ / Redis |
| **분산 처리** | 매우 강력 | 기본 | 강력 |
| **재시도** | 풍부한 옵션 | 기본 | 우수 |
| **모니터링** | Flower (매우 좋음) | 기본 | 기본 |
| **스케일** | 대규모 | 중규모 | 중~대규모 |
| **배우기 어려움** | 가파름 | 낮음 | 낮음 |

**선택: Celery + RabbitMQ**

**이유:**
- 한국 B2B SaaS 표준 (당근마켓, 쿠팡, NHN 사용)
- 장시간 실행 작업 (30MB HWPX 생성) 필요 → Celery 재시도 메커니즘 필수
- Flower 모니터링으로 8주 안에 개발팀이 디버깅 가능
- PostgreSQL + RabbitMQ 조합이 NHN Cloud에서 가장 안정적

**Dramatiq 거절 이유**: 모니터링 대시보드 부족 → 8주 내 프로덕션 문제 추적 어려움

### 2.3 스토리지: S3-호환 vs 데이터베이스 바이너리

| 서비스 | 비용/GB/월 | 대역폭 | 한국 리전 | 호환성 |
|--------|-----------|------|---------|--------|
| **NHN Cloud Object Storage** | ₩4,500 | 포함 | 서울 | S3 호환 |
| **AWS S3 Seoul (ap-northeast-2)** | $0.023 | ₩120/GB | 서울 | S3 네이티브 |
| **Naver Cloud Object Storage** | ₩4,200 | 포함 | 서울, 경기 | S3 호환 |
| **PostgreSQL BYTEA** | DB 용량 | DB 대역폭 | - | 트랜잭션 보장 |

**선택: NHN Cloud Object Storage (Primary) + AWS S3 Seoul (Backup)**

**이유:**
- NHN Cloud: 한국 기업 친화적, 빠른 기술 지원, 대역폭 무제한
- AWS S3: 재해복구(DR), 글로벌 확장 시 준비
- PostgreSQL BYTEA 거절: 데이터베이스 용량 빠르게 증가, 백업 속도 저하

### 2.4 데이터베이스: PostgreSQL vs MySQL vs MongoDB

| 항목 | PostgreSQL | MySQL 8.0 | MongoDB |
|------|-----------|----------|---------|
| **트랜잭션** | ACID (강력) | ACID | ACID (제한) |
| **한국 지원** | NHN Cloud RDS 우수 | AWS RDS | AWS DocumentDB |
| **JSON** | JSONB (강력) | JSON (기본) | 네이티브 |
| **확장성** | 대규모 | 중규모 | 매우 큼 |
| **B2B 표준** | 매우 높음 | 높음 | 낮음 |

**선택: PostgreSQL**

**이유:**
- 한국 B2B SaaS 표준 (당근마켓, 쿠팡, 배민 모두 사용)
- JSONB로 form_pipeline 추출 결과 저장 가능
- NHN Cloud RDS with 자동 백업/복제 → 8주 내 0 운영 복잡도
- 한글 전문검색 (Full Text Search) 지원 → 템플릿 검색 기능
- ACID 트랜잭션 → 결제/사용량 추적 정확성 보장

### 2.5 캐시: Redis vs Memcached

**선택: Redis Cluster (NHN Cloud Redis)**

**이유:**
- 세션 저장 (API key validation)
- API 응답 캐싱 (form template list)
- Rate limiter 상태 저장 (Token Bucket)
- Celery broker로도 사용 가능 (RabbitMQ 불가)
- 한국 B2B SaaS 표준

### 2.6 배포: NHN Cloud vs AWS Seoul vs Naver Cloud

| 항목 | NHN Cloud | AWS Seoul | Naver Cloud |
|------|-----------|----------|------------|
| **한국 기술지원** | 매우 빠름 (당일) | 느림 (24h+) | 빠름 (하루) |
| **RDS/DB 비용** | 저가 | 고가 | 저가 |
| **메인터넌스** | 한국팀 | 글로벌 | 한국팀 |
| **규제준수** | K-ISMS (우수) | FedRAMP | K-ISMS |
| **글로벌 확장** | 제한 | 매우 좋음 | 제한 |

**선택: NHN Cloud (Primary) + AWS Seoul (Backup/DR)**

**배포 구성:**
```
NHN Cloud (메인):
├── VPC: 10.0.0.0/16
├── EKS 클러스터 또는 VM 그룹 (3 인스턴스)
├── RDS PostgreSQL (Primary)
├── Redis Cluster
├── RabbitMQ (Managed)
└── Object Storage

AWS Seoul (재해복구):
├── Route53 (DNS failover)
├── RDS 읽기 복제본
└── S3 (크로스 리전 복제)
```

---

## 3. API 서버 설계 (FastAPI 구조)

### 3.1 디렉토리 구조

```
hwpx-skill-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 앱 초기화
│   ├── dependencies.py             # 공통 의존성 (DB, Redis)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── documents.py       # 문서 생성 엔드포인트
│   │       ├── forms.py           # 형식 채우기/복제
│   │       ├── templates.py       # 템플릿 관리
│   │       ├── ai.py              # AI 프롬프트 생성
│   │       ├── jobs.py            # 작업 상태 조회
│   │       └── health.py          # 헬스 체크
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # 환경설정
│   │   ├── security.py            # API 키 인증
│   │   └── rate_limiter.py        # 토큰 버킷 구현
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── hwpx_service.py        # pyhwpxlib 래핑
│   │   ├── form_service.py        # form_pipeline 통합
│   │   ├── ai_service.py          # Claude API 호출
│   │   └── storage_service.py     # S3 업로드/다운로드
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py             # Pydantic 스키마
│   │   ├── database.py            # SQLAlchemy ORM
│   │   └── enums.py               # 열거형
│   │
│   └── workers/
│       ├── __init__.py
│       ├── celery_config.py       # Celery 설정
│       ├── document_tasks.py      # 문서 생성 작업
│       ├── form_tasks.py          # 형식 작업
│       ├── ai_tasks.py            # AI 작업
│       └── cleanup_tasks.py       # 임시파일 정리
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_services.py
│   ├── test_workers.py
│   └── conftest.py
│
├── docker/
│   ├── Dockerfile                 # 앱 컨테이너
│   ├── Dockerfile.worker          # 워커 컨테이너
│   └── docker-compose.yml
│
├── migrations/
│   ├── alembic.ini
│   └── versions/
│
├── .env.example
├── requirements.txt
├── pyproject.toml
├── pytest.ini
└── README.md
```

### 3.2 FastAPI main.py (기본 구조)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware

from app.core.config import settings
from app.core.security import verify_api_key
from app.api.v1 import documents, forms, templates, ai, jobs, health

app = FastAPI(
    title="hwpx-skill API",
    version="1.0.0",
    description="HWPX 문서 생성 & 형식 처리 SaaS API"
)

# CORS (B2B 클라이언트용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 응답 압축
app.add_middleware(GZIPMiddleware, minimum_size=1024)

# 라우터 등록
app.include_router(
    documents.router,
    prefix="/v1/documents",
    tags=["documents"]
)
app.include_router(
    forms.router,
    prefix="/v1/forms",
    tags=["forms"]
)
app.include_router(
    templates.router,
    prefix="/v1/templates",
    tags=["templates"]
)
app.include_router(
    ai.router,
    prefix="/v1/ai",
    tags=["ai"]
)
app.include_router(
    jobs.router,
    prefix="/v1/jobs",
    tags=["jobs"]
)
app.include_router(
    health.router,
    tags=["health"]
)

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    # Redis 연결 확인
    # RabbitMQ 연결 확인
    # DB 마이그레이션 실행
    pass

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 정리"""
    # 임시 파일 삭제
    # Redis 연결 종료
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=4,
        loop="uvloop"  # 성능 향상
    )
```

### 3.3 주요 API 엔드포인트

```python
# POST /v1/documents/create-from-markdown
@router.post("/create-from-markdown", status_code=202)
async def create_document_from_markdown(
    markdown_content: str = Form(...),
    style: str = Form("default"),
    api_key: str = Header(...)
) -> JobResponse:
    """마크다운 → HWPX 변환 (비동기)"""

# POST /v1/forms/fill
@router.post("/fill", status_code=202)
async def fill_form(
    template_file: UploadFile,
    form_data: str = Form(...),  # JSON string
    api_key: str = Header(...)
) -> JobResponse:
    """형식 채우기 (비동기)"""

# POST /v1/forms/clone
@router.post("/clone", status_code=202)
async def clone_form(
    file: UploadFile,
    api_key: str = Header(...)
) -> FormExtractionResponse:
    """정부 형식 복제 (추출)"""

# GET /v1/jobs/{job_id}
@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    api_key: str = Header(...)
) -> JobStatusResponse:
    """작업 상태 조회"""

# GET /v1/jobs/{job_id}/download
@router.get("/jobs/{job_id}/download")
async def download_job_result(
    job_id: str,
    api_key: str = Header(...)
) -> FileResponse:
    """완료된 파일 다운로드"""
```

---

## 4. API 키 인증 & 속도 제한

### 4.1 API 키 관리 (데이터베이스 스키마)

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- bcrypt hash
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    name VARCHAR(255),
    tier VARCHAR(20),  -- free, pro, enterprise
    rate_limit_per_hour INTEGER,
    concurrent_jobs INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE rate_limit_usage (
    api_key_id INTEGER REFERENCES api_keys(id),
    hour TIMESTAMP,  -- YYYY-MM-DD HH:00:00
    request_count INTEGER,
    PRIMARY KEY (api_key_id, hour)
);

CREATE TABLE job_history (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    job_id VARCHAR(36) UNIQUE,
    endpoint VARCHAR(255),
    status VARCHAR(20),  -- pending, running, completed, failed
    input_size_bytes INTEGER,
    output_size_bytes INTEGER,
    duration_seconds FLOAT,
    cost_credits DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### 4.2 토큰 버킷 알고리즘 (Redis 구현)

```python
# rate_limiter.py
import redis
import time
from datetime import datetime

class TokenBucketRateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def is_allowed(self, api_key: str, limit: int, window_seconds: int = 3600) -> bool:
        """
        api_key에 대해 limit 요청이 window_seconds 내에 허용되는지 확인

        호출 예:
            is_allowed("key_abc123", limit=1000, window_seconds=3600)
            → 1시간에 1000 요청 허용
        """
        key = f"rate_limit:{api_key}"
        current_time = time.time()
        window_start = int(current_time // window_seconds) * window_seconds

        # Lua 스크립트로 원자적 연산 보장
        lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local current_time = tonumber(ARGV[3])
        local window_seconds = tonumber(ARGV[4])

        local bucket_key = key .. ":" .. window_start
        local current_count = redis.call('get', bucket_key)
        current_count = current_count and tonumber(current_count) or 0

        if current_count < limit then
            redis.call('incr', bucket_key)
            redis.call('expire', bucket_key, window_seconds * 2)
            return 1
        end
        return 0
        """

        result = self.redis.eval(
            lua_script, 1, key,
            limit, window_start, current_time, window_seconds
        )
        return bool(result)
```

### 4.3 API 키 검증 미들웨어

```python
# security.py
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

async def verify_api_key(
    api_key: str = Header(...),
    db: Session = Depends(get_db),
    rate_limiter: TokenBucketRateLimiter = Depends()
) -> APIKeyInfo:
    """
    API 키 유효성 검사 + 속도 제한 확인
    """
    # 1. Redis에서 캐시된 키 정보 확인
    cached = redis_client.get(f"apikey:{api_key}")
    if cached:
        key_info = json.loads(cached)
    else:
        # 2. DB에서 조회
        db_key = db.query(APIKey).filter(
            APIKey.key_hash == hash_api_key(api_key)
        ).first()

        if not db_key or not db_key.is_active:
            raise HTTPException(status_code=401, detail="Invalid API key")

        key_info = {
            "id": db_key.id,
            "customer_id": db_key.customer_id,
            "tier": db_key.tier,
            "rate_limit_per_hour": db_key.rate_limit_per_hour,
            "concurrent_jobs": db_key.concurrent_jobs
        }

        # 3. 1시간 캐시
        redis_client.setex(
            f"apikey:{api_key}",
            3600,
            json.dumps(key_info)
        )

    # 4. 속도 제한 확인
    if not rate_limiter.is_allowed(
        api_key,
        limit=key_info["rate_limit_per_hour"],
        window_seconds=3600
    ):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )

    return APIKeyInfo(**key_info)
```

### 4.4 요금 제도 (Tier 별)

```
Free (개발자):
├── 월 100 API 호출
├── 파일당 최대 10MB
├── 동시 작업 1개
└── 가격: ₩0

Pro (스타트업):
├── 월 10,000 API 호출 (시간당 500)
├── 파일당 최대 50MB
├── 동시 작업 10개
├── 우선 지원
└── 가격: ₩99,000/월

Enterprise (기업):
├── 무제한 API 호출
├── 파일당 최대 500MB
├── 동시 작업 100개
├── 전담 기술 지원
├── SLA 99.9%
└── 맞춤 가격
```

---

## 5. 문서 생성 파이프라인

### 5.1 pyhwpxlib 서비스 래핑

```python
# services/hwpx_service.py
from pathlib import Path
from typing import Optional
import tempfile
import logging

from pyhwpxlib.api import (
    create_document, add_paragraph, add_table, save
)
from pyhwpxlib.converter import convert_markdown_to_hwpx

class HWPXService:
    """pyhwpxlib 라이브러리 래핑"""

    def __init__(self, temp_dir: Path = None):
        self.temp_dir = temp_dir or Path(tempfile.gettempdir())
        self.logger = logging.getLogger(__name__)

    def create_from_markdown(
        self,
        markdown_content: str,
        style: str = "default"
    ) -> Path:
        """마크다운 → HWPX 변환"""
        try:
            doc = create_document()
            convert_markdown_to_hwpx(doc, markdown_content, style=style)

            output_path = self.temp_dir / f"doc_{uuid.uuid4().hex}.hwpx"
            save(doc, str(output_path))

            return output_path
        except Exception as e:
            self.logger.error(f"Failed to create document: {e}")
            raise

    def clone_form(self, input_path: Path) -> Path:
        """형식 복제 (역엔지니어링)"""
        # form_pipeline 참조
        from templates.form_pipeline import extract_form

        try:
            form_json = extract_form(str(input_path))

            # JSON → HWPX 재생성
            # (form_pipeline.generate_form 사용)
            output_path = self.temp_dir / f"clone_{uuid.uuid4().hex}.hwpx"

            return output_path
        except Exception as e:
            self.logger.error(f"Failed to clone form: {e}")
            raise

    def fill_template(
        self,
        template_path: Path,
        data: dict
    ) -> Path:
        """템플릿 채우기"""
        from pyhwpxlib.api import fill_template

        try:
            output_path = self.temp_dir / f"filled_{uuid.uuid4().hex}.hwpx"
            fill_template(str(template_path), data, str(output_path))
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to fill template: {e}")
            raise
```

### 5.2 임시 파일 관리 (메모리 효율성)

```python
# services/temp_file_manager.py
import shutil
import atexit
from pathlib import Path
from datetime import datetime, timedelta

class TempFileManager:
    """
    HWPX는 ZIP 기반 → 대용량 임시파일 발생
    임시파일 자동 정리 + 용량 제한
    """

    MAX_TEMP_SIZE_MB = 1000  # 최대 1GB
    CLEANUP_INTERVAL_HOURS = 24

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 프로세스 종료 시 정리
        atexit.register(self.cleanup_old_files)

    def allocate_temp_file(self, suffix: str = ".hwpx") -> Path:
        """임시파일 경로 할당"""
        temp_path = self.base_dir / f"{uuid.uuid4().hex}{suffix}"

        # 용량 확인
        total_size = sum(
            f.stat().st_size
            for f in self.base_dir.glob("**/*")
            if f.is_file()
        ) / (1024 * 1024)

        if total_size > self.MAX_TEMP_SIZE_MB:
            self.cleanup_old_files()

        return temp_path

    def cleanup_old_files(self, hours: int = 24):
        """24시간 이상 된 임시파일 삭제"""
        cutoff = datetime.now() - timedelta(hours=hours)
        for file in self.base_dir.glob("**/*"):
            if file.is_file():
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    try:
                        file.unlink()
                    except Exception as e:
                        logging.error(f"Failed to delete {file}: {e}")

    def get_temp_usage_mb(self) -> float:
        """현재 임시파일 총 용량"""
        return sum(
            f.stat().st_size
            for f in self.base_dir.glob("**/*")
            if f.is_file()
        ) / (1024 * 1024)
```

### 5.3 동시 요청 처리 (스레드 풀 + async)

```python
# workers/document_tasks.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.services.hwpx_service import HWPXService

# CPU 집약적 작업 → ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)

@celery_app.task(bind=True, max_retries=3)
def create_document_task(
    self,
    job_id: str,
    markdown_content: str,
    style: str = "default"
):
    """
    Celery 워커 작업 (별도 프로세스에서 실행)

    장점:
    - API 서버와 분리 → API 응답성 유지
    - 작업 재시도 자동 처리
    - 실패 시 재스케줄 가능
    """

    try:
        logger.info(f"[{job_id}] Starting document creation")

        hwpx_service = HWPXService()

        # 1. 마크다운 → HWPX 변환 (CPU 집약적)
        output_path = hwpx_service.create_from_markdown(
            markdown_content, style=style
        )

        # 2. S3 업로드
        storage_service = StorageService()
        s3_url = storage_service.upload_file(
            output_path,
            bucket="hwpx-documents",
            key=f"documents/{job_id}.hwpx"
        )

        # 3. DB에 결과 저장
        job = JobHistory.query.filter_by(job_id=job_id).first()
        job.status = "completed"
        job.output_size_bytes = output_path.stat().st_size
        job.s3_url = s3_url
        job.completed_at = datetime.now()
        db.session.commit()

        # 4. 웹훅 콜백
        webhook_service.trigger_webhook(job_id, s3_url)

        # 5. 임시파일 삭제
        output_path.unlink()

        logger.info(f"[{job_id}] Completed successfully")
        return {"status": "completed", "url": s3_url}

    except Exception as exc:
        logger.error(f"[{job_id}] Error: {exc}")

        # 지수 백오프 재시도 (3초, 9초, 27초)
        raise self.retry(
            exc=exc,
            countdown=3 ** self.request.retries
        )
```

---

## 6. 템플릿 저장소 & 관리

### 6.1 템플릿 데이터베이스 스키마

```sql
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE,
    name VARCHAR(255),
    category VARCHAR(100),  -- 법인, 인사, 계약, 정부서식
    description TEXT,
    hwpx_file_key VARCHAR(255),  -- S3 경로
    form_schema JSONB,  -- form_pipeline에서 추출
    version INTEGER DEFAULT 1,
    status VARCHAR(20),  -- draft, published, deprecated
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    download_count INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT FALSE,

    UNIQUE(name, version)
);

CREATE TABLE template_versions (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES templates(id),
    version INTEGER,
    hwpx_file_key VARCHAR(255),
    form_schema JSONB,
    changes TEXT,  -- 변경사항
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE template_usage (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES templates(id),
    api_key_id INTEGER REFERENCES api_keys(id),
    used_at TIMESTAMP DEFAULT NOW()
);

-- 검색용 인덱스
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_status ON templates(status);
CREATE INDEX idx_templates_name_gin ON templates USING GIN(
    to_tsvector('korean', name)
);
```

### 6.2 템플릿 관리 서비스

```python
# services/template_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json

class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def upload_template(
        self,
        hwpx_file: Path,
        name: str,
        category: str,
        description: str = ""
    ) -> dict:
        """
        정부 서식 업로드 + form_pipeline으로 추출
        """
        from templates.form_pipeline import extract_form

        # 1. 형식 구조 추출
        form_schema = extract_form(str(hwpx_file))

        # 2. S3 업로드
        storage = StorageService()
        s3_key = storage.upload_file(
            hwpx_file,
            bucket="templates",
            key=f"forms/{uuid.uuid4().hex}.hwpx"
        )

        # 3. DB 저장
        template = Template(
            uuid=str(uuid.uuid4()),
            name=name,
            category=category,
            description=description,
            hwpx_file_key=s3_key,
            form_schema=form_schema,
            status="published"
        )
        self.db.add(template)
        self.db.commit()

        return {"id": template.id, "schema": form_schema}

    def search_templates(
        self,
        query: str = "",
        category: str = "",
        limit: int = 10,
        offset: int = 0
    ) -> list:
        """한글 전문검색 지원"""
        q = self.db.query(Template).filter(
            Template.status == "published"
        )

        if category:
            q = q.filter(Template.category == category)

        if query:
            # PostgreSQL 한글 전문검색
            q = q.filter(
                func.to_tsvector('korean', Template.name).match(
                    func.plainto_tsquery('korean', query)
                )
            )

        return q.limit(limit).offset(offset).all()

    def get_template_by_id(self, template_id: int) -> dict:
        """템플릿 정보 조회"""
        template = self.db.query(Template).filter(
            Template.id == template_id
        ).first()

        if not template:
            raise ValueError("Template not found")

        # 사용 통계 기록
        usage = TemplateUsage(
            template_id=template_id,
            api_key_id=current_api_key.id
        )
        self.db.add(usage)
        self.db.commit()

        return {
            "id": template.id,
            "name": template.name,
            "category": template.category,
            "form_schema": template.form_schema,
            "s3_url": template.hwpx_file_key
        }
```

---

## 7. 비동기 처리 & 무거운 작업

### 7.1 어느 작업이 비동기인가?

**비동기 필수 (Celery 작업):**
- Markdown → HWPX (CPU 집약적, 5-30초)
- 형식 복제 (ZIP 파싱 + XML 처리, 10-60초)
- 대용량 파일 채우기 (메모리 집약적)
- Claude API 호출 (네트워크 대기)
- 이메일 발송

**동기 (FastAPI 직접):**
- API 키 검증
- 캐시된 템플릿 조회
- 작업 상태 조회
- 소규모 파일 업로드 (< 1MB)

### 7.2 웹훅 콜백 vs 폴링

**선택: 웹훅 콜백 (우선) + 폴링 (폴백)**

```python
# workers/webhook_service.py
import httpx
import json

class WebhookService:
    async def trigger_webhook(
        self,
        job_id: str,
        event: str,
        data: dict
    ):
        """
        작업 완료 시 클라이언트 웹훅 호출

        event: "document.created", "form.filled", "form.cloned"
        """

        # 1. 웹훅 URL 조회
        job = JobHistory.query.filter_by(job_id=job_id).first()
        webhook_url = job.webhook_url

        if not webhook_url:
            return  # 웹훅 없음 → 클라이언트는 폴링 사용

        # 2. 서명으로 위변조 방지
        payload = {
            "event": event,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        signature = hmac.new(
            self.webhook_secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()

        # 3. 비동기 POST 요청 (타임아웃 10초)
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={
                        "X-Webhook-Signature": signature,
                        "User-Agent": "hwpx-skill-api/1.0"
                    }
                )

                if response.status_code >= 500:
                    # 재시도 (Celery)
                    self.retry_webhook.apply_async(
                        (job_id, event, data),
                        countdown=60
                    )

                logger.info(f"Webhook triggered for {job_id}")

            except Exception as e:
                logger.error(f"Webhook failed: {e}")
                # Celery에서 재시도
                self.retry_webhook.apply_async(
                    (job_id, event, data),
                    countdown=60
                )
```

### 7.3 작업 상태 추적

```python
# models/database.py
from sqlalchemy import Column, String, Integer, DateTime, JSONB

class JobHistory(Base):
    __tablename__ = "job_history"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), unique=True)  # UUID
    api_key_id = Column(Integer, ForeignKey("api_keys.id"))
    endpoint = Column(String(255))
    status = Column(String(20))  # pending, running, completed, failed

    # 타이밍
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 입출력
    input_data = Column(JSONB)  # 입력 메타데이터
    output_s3_url = Column(String(500))
    output_size_bytes = Column(Integer)

    # 에러
    error_message = Column(String(1000))
    retry_count = Column(Integer, default=0)

    # 웹훅
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))

# GET /v1/jobs/{job_id}
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = db.query(JobHistory).filter_by(job_id=job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,  # pending, running, completed, failed
        created_at=job.created_at,
        completed_at=job.completed_at,
        progress_percent=calculate_progress(job),
        result_url=job.output_s3_url if job.status == "completed" else None,
        error=job.error_message if job.status == "failed" else None
    )
```

---

## 8. 배포 & DevOps

### 8.1 Docker 이미지 (멀티스테이지 빌드)

```dockerfile
# docker/Dockerfile (앱 서버)
FROM python:3.11-slim as builder

WORKDIR /build

# 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 실행 이미지
FROM python:3.11-slim

WORKDIR /app

# 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# docker/Dockerfile.worker (Celery 워커)
FROM python:3.11-slim as builder
# ... (위와 동일)

FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 1000 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

# 워커 실행
CMD ["celery", "-A", "app.workers.celery_config", "worker", "--loglevel=info"]
```

### 8.2 Docker Compose (로컬 개발)

```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: hwpx_skill
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    ports:
      - "5672:5672"
      - "15672:15672"
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s

  app:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:dev_password@postgres:5432/hwpx_skill
      REDIS_URL: redis://redis:6379
      CELERY_BROKER_URL: amqp://guest:guest@rabbitmq:5672//
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    volumes:
      - .:/app

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: celery -A app.workers.celery_config worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://postgres:dev_password@postgres:5432/hwpx_skill
      CELERY_BROKER_URL: amqp://guest:guest@rabbitmq:5672//
    depends_on:
      - postgres
      - rabbitmq
    volumes:
      - .:/app

volumes:
  postgres_data:
```

### 8.3 NHN Cloud Kubernetes 배포

```yaml
# k8s/app-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hwpx-api
  namespace: default
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0

  selector:
    matchLabels:
      app: hwpx-api

  template:
    metadata:
      labels:
        app: hwpx-api
    spec:
      containers:
      - name: app
        image: registry.nhncloud.com/hwpx-skill/app:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000

        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: connection-string
        - name: REDIS_URL
          value: "redis://redis-cluster:6379"
        - name: CELERY_BROKER_URL
          value: "amqp://rabbitmq:5672/"

        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"

---
apiVersion: v1
kind: Service
metadata:
  name: hwpx-api-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: hwpx-api

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hwpx-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hwpx-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 8.4 CI/CD 파이프라인 (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to NHN Cloud

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
      redis:
        image: redis:7

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt pytest pytest-cov

    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:password@localhost/test
      run: |
        pytest --cov=app tests/

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t registry.nhncloud.com/hwpx-skill/app:${{ github.sha }} .
        docker tag registry.nhncloud.com/hwpx-skill/app:${{ github.sha }} registry.nhncloud.com/hwpx-skill/app:latest

    - name: Push to NHN Container Registry
      run: |
        docker login -u ${{ secrets.NHN_REGISTRY_USER }} -p ${{ secrets.NHN_REGISTRY_PASS }} registry.nhncloud.com
        docker push registry.nhncloud.com/hwpx-skill/app:${{ github.sha }}
        docker push registry.nhncloud.com/hwpx-skill/app:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Update Kubernetes deployment
      run: |
        kubectl set image deployment/hwpx-api app=registry.nhncloud.com/hwpx-skill/app:${{ github.sha }} \
          --record \
          --kubeconfig=${{ secrets.KUBECONFIG }}
```

### 8.5 모니터링 & 로깅

```python
# app/core/logging_config.py
import logging
import json
from pythonjsonlogger import jsonlogger

# JSON 로깅 (ELK Stack 호환)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Datadog APM
from ddtrace import tracer, patch_all

patch_all()

# FastAPI 미들웨어
from fastapi import FastAPI
from ddtrace.contrib.fastapi import patch

patch()

# 커스텀 메트릭
from statsd import StatsClient

stats = StatsClient(host='localhost', port=8125)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    stats.timing(f"request.{request.url.path}", duration)
    stats.incr(f"request.status.{response.status_code}")

    return response
```

---

## 9. 보안 고려사항

### 9.1 API 키 로테이션

```python
# services/api_key_service.py
class APIKeyService:
    def rotate_key(self, api_key_id: int) -> str:
        """기존 키를 폐기하고 새 키 발급"""
        old_key = db.query(APIKey).filter_by(id=api_key_id).first()

        # 1. 새 키 생성
        new_key = secrets.token_urlsafe(32)
        new_hash = bcrypt.hashpw(new_key.encode(), bcrypt.gensalt(rounds=12))

        # 2. 새 키 저장
        new_api_key = APIKey(
            key_hash=new_hash,
            customer_id=old_key.customer_id,
            tier=old_key.tier,
            name=f"{old_key.name} (rotated)"
        )
        db.add(new_api_key)

        # 3. 이전 키 비활성화 (삭제 X → 감사 추적)
        old_key.is_active = False
        old_key.rotated_at = datetime.now()
        old_key.rotated_to = new_api_key.id

        db.commit()

        return new_key
```

### 9.2 입력 검증 (XML 주입 방지)

HWPX는 XML 기반 → XXE(XML External Entity) 주입 취약점 조심

```python
# core/security.py
import defusedxml.ElementTree as ET

def safe_parse_hwpx(file_path: str):
    """안전한 HWPX 파싱 (XXE 방지)"""
    import zipfile

    with zipfile.ZipFile(file_path) as zf:
        section_xml = zf.read('Contents/section0.xml')

    # defusedxml 사용 → XXE 공격 차단
    try:
        root = ET.fromstring(section_xml)
        return root
    except ET.ParseError as e:
        raise ValueError(f"Invalid HWPX file: {e}")

# FastAPI 요청 검증
from pydantic import BaseModel, validator

class MarkdownRequest(BaseModel):
    content: str
    style: str = "default"

    @validator('content')
    def validate_markdown(cls, v):
        # 마크다운 크기 제한
        if len(v) > 1_000_000:  # 1MB
            raise ValueError("Content too large")
        return v
```

### 9.3 파일 업로드 검증

```python
# services/upload_validator.py
import magic

class FileValidator:
    ALLOWED_MIMETYPES = {
        "application/vnd.ms-word.document.macroEnabled.12": ".hwpx",
        "application/vnd.hancom.hwpx": ".hwpx",
        "application/xml": ".owpml"
    }

    MAX_FILE_SIZE_MB = 50

    def validate_upload(self, file: UploadFile) -> bool:
        """파일 유효성 검사"""

        # 1. 파일 크기
        if file.size > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise ValueError("File too large")

        # 2. MIME 타입 검증 (magic bytes)
        file_mime = magic.from_buffer(file.file.read(1024), mime=True)
        if file_mime not in self.ALLOWED_MIMETYPES:
            raise ValueError(f"Invalid file type: {file_mime}")

        # 3. ZIP 구조 검증 (HWPX는 ZIP)
        import zipfile
        file.file.seek(0)
        try:
            with zipfile.ZipFile(file.file) as zf:
                # HWPX 필수 파일 확인
                required = ["Contents/section0.xml", "Contents/header.xml"]
                if not all(f in zf.namelist() for f in required):
                    raise ValueError("Invalid HWPX structure")
        except zipfile.BadZipFile:
            raise ValueError("Corrupted ZIP file")

        return True
```

### 9.4 CORS 정책

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://*.example.com",  # 도메인 화이트리스트
        "https://admin.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)
```

---

## 10. 비용 추정 (한국 클라우드 기준)

### 10.1 인프라 비용 (월단위)

**NHN Cloud 기준 (1,000 API 호출/일 = 30,000/월 기준)**

| 항목 | 규모 | 비용 | 비고 |
|------|------|------|------|
| **RDS PostgreSQL** | 16GB, 자동 백업 | ₩400,000 | 고가용성 복제 |
| **Redis Cluster** | 4GB | ₩150,000 | Rate limiter + 캐시 |
| **Object Storage** | 100GB | ₩450,000 | S3 호환, 대역폭 무제한 |
| **VM (API 서버)** | 2vCPU × 3대 | ₩600,000 | Auto-scaling |
| **VM (Worker)** | 4vCPU × 2대 | ₩400,000 | Celery workers |
| **RabbitMQ 관리형** | 기본 | ₩200,000 | 메시지 큐 |
| **로드밸런서** | 기본 | ₩150,000 | NLB |
| **대역폭** | 100GB/월 | ₩12,000 | 초과분 |
| **모니터링** | Datadog | ₩300,000 | APM + 로깅 |
| **백업/DR** | AWS S3 Seoul | ₩50,000 | 크로스 리전 복제 |
| **---|---|---|---|
| **총계** | | **₩2,712,000/월** | |

### 10.2 운영 비용

| 항목 | 1인-월 | 2인-팀/월 |
|------|--------|----------|
| **개발 (유지보수)** | 1,500,000 | 3,000,000 |
| **인프라 관리** | 800,000 | 1,600,000 |
| **고객 지원** | - | 1,000,000 |
| **법률/회계** | - | 500,000 |
| **---|---|---|
| **소계** | 2,300,000 | 6,100,000 |

### 10.3 손익분기점 분석

```
월 수익 = (유료 사용자 수) × (평균 ARPU) + 초과 API 호출 요금

Free Tier: ₩0
Pro Tier (₩99,000/월): 30% 전환율 목표
Enterprise (맞춤): 10% 전환율 목표

예시 시나리오 (6개월 후):
- 활성 사용자: 1,000명
- Pro 전환율: 5% (50명) → ₩4,950,000
- Enterprise: 1명 (₩1,000,000/월 맞춤)
- 초과 요금: ₩500,000
────────────────────
월 수익: ₩6,450,000

월 운영 비용: ₩2,712,000 (인프라) + ₩6,100,000 (팀)
= ₩8,812,000

⚠️ 아직 적자 → Pro 가격 인상 또는 사용자 확대 필요

12개월 후:
- 활성 사용자: 5,000명
- Pro 전환율: 8% (400명) → ₩39,600,000
- Enterprise: 5명 (₩5,000,000/월)
- 초과 요금: ₩3,000,000
────────────────────
월 수익: ₩47,600,000
월 비용: ₩8,812,000

손익분기점: ₩8,812,000 / (Pro 평균 구성률 × 99,000)
= 약 900명의 Pro 가입자 필요
```

### 10.4 비용 최적화 전략

1. **초기 6개월**: NHN Cloud 스타트업 프로모션 (50% 할인) 활용
2. **Scale-up**: 트래픽 예측에 따라 주문형 리소스로 전환
3. **Reserved Instance**: 6개월 이상 사용 확정 시 30% 할인
4. **멀티 리전**: 글로벌 확장 시 Spot Instance 활용

---

## 11. 8주 구현 로드맵 (2인 팀)

### Week 1-2: 기초 구축
- [ ] FastAPI + PostgreSQL + Redis + Celery 개발 환경
- [ ] API 키 인증 & Rate Limiter 구현
- [ ] 기본 CRUD 모델 (APIKey, Template, JobHistory)
- [ ] 단위 테스트 작성

### Week 3-4: API 엔드포인트
- [ ] POST /v1/documents/create-from-markdown (async)
- [ ] POST /v1/forms/fill (async)
- [ ] POST /v1/forms/clone (async)
- [ ] GET /v1/jobs/{job_id}
- [ ] GET /v1/templates (검색)

### Week 5-6: 프로덕션 준비
- [ ] Docker & docker-compose 설정
- [ ] NHN Cloud Kubernetes 배포
- [ ] CI/CD 파이프라인 (GitHub Actions)
- [ ] 모니터링 & 로깅 설정
- [ ] 보안 감사 (Input validation, XXE 방지)

### Week 7-8: 테스트 & 배포
- [ ] 통합 테스트 & 부하 테스트
- [ ] 문서화 (Swagger, API 문서)
- [ ] 프로덕션 배포
- [ ] 모니터링 대시보드
- [ ] 런칭

---

## 12. 기술 스택 최종 요약

```
Backend:          FastAPI (Python 3.11)
Database:         PostgreSQL 15 (NHN Cloud RDS)
Cache:            Redis Cluster (NHN Cloud)
Task Queue:       Celery 5 + RabbitMQ
File Storage:     NHN Cloud Object Storage + AWS S3 Seoul
Containerization: Docker + Kubernetes (NHN Cloud EKS)
CI/CD:            GitHub Actions
Monitoring:       Datadog / Grafana
Logging:          ELK Stack (Elasticsearch + Kibana)
IaC:              Terraform (선택사항)
Testing:          pytest + pytest-cov
```

---

**문서 완성일**: 2026-04-05
**다음 단계**: Week 1 개발 환경 구성 시작
