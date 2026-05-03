# 구현 가이드: hwpx-skill API SaaS

**대상**: 2인 개발팀, 8주 일정

---

## Phase 1: 프로젝트 초기화 (Day 1-2)

### 1.1 프로젝트 구조 생성

```bash
mkdir hwpx-skill-api
cd hwpx-skill-api

# 디렉토리 구조 생성
mkdir -p app/{api/v1,core,services,models,workers}
mkdir -p tests
mkdir -p docker
mkdir -p migrations/versions
mkdir -p docs

# Git 초기화
git init
git remote add origin https://github.com/your-org/hwpx-skill-api.git
```

### 1.2 의존성 파일 생성

```bash
cat > requirements.txt << 'EOF'
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9

# Cache
redis==5.0.1

# Task Queue
celery==5.3.4
kombu==5.3.2

# File Upload
python-multipart==0.0.6

# Auth
python-jose[cryptography]==3.3.0
bcrypt==4.1.1
passlib[bcrypt]==1.7.4

# HTTP Client
httpx==0.25.1

# Logging & Monitoring
python-json-logger==2.0.7
requests==2.31.0

# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
httpx==0.25.1

# Development
black==23.12.0
flake8==6.1.0
mypy==1.7.1

# Environment
python-dotenv==1.0.0
EOF
```

### 1.3 설정 파일

```bash
cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/hwpx_skill
DATABASE_ECHO=False

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# S3 (NHN Cloud)
NHN_OBJECT_STORAGE_URL=https://api-object-storage.nhncloud.com
NHN_CONTAINER=hwpx-documents
NHN_TENANT_ID=your_tenant_id
NHN_USERNAME=your_username
NHN_PASSWORD=your_password

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256

# CORS
ALLOWED_ORIGINS=["http://localhost:3000", "https://app.example.com"]

# Logging
LOG_LEVEL=INFO

# Features
ENABLE_WEBHOOKS=True
WEBHOOK_TIMEOUT_SECONDS=10
EOF

cp .env.example .env
```

### 1.4 로컬 개발 환경 시작

```bash
# Docker Compose로 의존성 실행
docker-compose -f docker-compose.yml up -d

# 마이그레이션 준비
pip install -r requirements.txt
alembic init migrations --template generic

# 초기 마이그레이션 생성
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

## Phase 2: 핵심 API 구조 (Day 3-7)

### 2.1 `app/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    APP_NAME: str = "hwpx-skill API"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    # Database
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # Cache
    REDIS_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # S3
    NHN_OBJECT_STORAGE_URL: str
    NHN_CONTAINER: str
    NHN_TENANT_ID: str
    NHN_USERNAME: str
    NHN_PASSWORD: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
```

### 2.2 `app/models/schemas.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class APIKeyCreate(BaseModel):
    name: str
    tier: str  # free, pro, enterprise

class APIKeyResponse(BaseModel):
    id: int
    key_hash: str  # 앞 8자만 표시
    tier: str
    rate_limit_per_hour: int
    created_at: datetime

class JobResponse(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    created_at: datetime

class JobStatusResponse(JobResponse):
    progress_percent: Optional[int] = None
    completed_at: Optional[datetime] = None
    result_url: Optional[str] = None
    error: Optional[str] = None

class MarkdownRequest(BaseModel):
    content: str = Field(..., max_length=1_000_000)
    style: str = "default"

class FormFillRequest(BaseModel):
    form_data: Dict[str, Any]

class TemplateResponse(BaseModel):
    id: int
    name: str
    category: str
    description: str
    form_schema: Dict[str, Any]
    download_count: int
    created_at: datetime
```

### 2.3 `app/models/database.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, JSONB, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    key_hash = Column(String(64), unique=True, nullable=False)
    customer_id = Column(Integer, nullable=False)
    name = Column(String(255))
    tier = Column(String(20), default="free")  # free, pro, enterprise
    rate_limit_per_hour = Column(Integer, default=100)
    concurrent_jobs = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

class JobHistory(Base):
    __tablename__ = "job_history"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), unique=True, nullable=False)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)
    endpoint = Column(String(255))
    status = Column(String(20), default="pending")
    input_data = Column(JSONB)
    input_size_bytes = Column(Integer)
    output_size_bytes = Column(Integer)
    output_s3_url = Column(String(500))
    error_message = Column(String(1000))
    duration_seconds = Column(Float)
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    description = Column(Text)
    hwpx_file_key = Column(String(255))
    form_schema = Column(JSONB)
    version = Column(Integer, default=1)
    status = Column(String(20), default="draft")
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    download_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=False)
```

### 2.4 데이터베이스 연결

```python
# app/dependencies.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.5 기본 FastAPI 앱

```python
# app/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.dependencies import get_db

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS
    )
```

---

## Phase 3: API 엔드포인트 구현 (Day 8-15)

### 3.1 `app/core/security.py` - API 키 검증

```python
import bcrypt
import secrets
from sqlalchemy.orm import Session
from fastapi import Header, HTTPException, Depends
from app.dependencies import get_db
from app.models.database import APIKey

def hash_api_key(key: str) -> str:
    """API 키를 bcrypt로 해싱"""
    return bcrypt.hashpw(key.encode(), bcrypt.gensalt(rounds=12)).decode()

def generate_api_key() -> str:
    """새로운 API 키 생성"""
    return secrets.token_urlsafe(32)

async def verify_api_key(
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
) -> APIKey:
    """API 키 유효성 검사"""
    # 간단한 예: 실제로는 bcrypt로 검증해야 함
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == x_api_key
    ).first()

    if not api_key or not api_key.is_active:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key
```

### 3.2 `app/core/rate_limiter.py` - 토큰 버킷

```python
import time
import redis
import json
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

class RateLimiter:
    def is_allowed(self, api_key: str, limit: int, window: int = 3600) -> bool:
        """토큰 버킷 알고리즘"""
        key = f"rate_limit:{api_key}"
        current_time = int(time.time())
        window_start = (current_time // window) * window

        bucket_key = f"{key}:{window_start}"
        current_count = int(redis_client.get(bucket_key) or 0)

        if current_count < limit:
            redis_client.incr(bucket_key)
            redis_client.expire(bucket_key, window * 2)
            return True
        return False

rate_limiter = RateLimiter()
```

### 3.3 `app/api/v1/documents.py`

```python
from fastapi import APIRouter, Depends, Form, HTTPException
from app.models.schemas import JobResponse, MarkdownRequest
from app.models.database import APIKey, JobHistory
from app.dependencies import get_db
from app.core.security import verify_api_key
from app.core.rate_limiter import rate_limiter
from app.workers.celery_config import create_document_task
import uuid
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/create-from-markdown", status_code=202)
async def create_from_markdown(
    markdown_content: str = Form(...),
    style: str = Form("default"),
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
):
    """마크다운 → HWPX 변환"""

    # 1. API 키 검증
    api_key = await verify_api_key(x_api_key, db)

    # 2. 속도 제한 확인
    if not rate_limiter.is_allowed(x_api_key, api_key.rate_limit_per_hour):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # 3. Job 생성
    job_id = str(uuid.uuid4())
    job = JobHistory(
        job_id=job_id,
        api_key_id=api_key.id,
        endpoint="/documents/create-from-markdown",
        status="pending"
    )
    db.add(job)
    db.commit()

    # 4. Celery 작업 큐에 추가
    create_document_task.delay(job_id, markdown_content, style)

    return JobResponse(
        job_id=job_id,
        status="pending",
        created_at=job.created_at
    )
```

### 3.4 `app/api/v1/jobs.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.database import JobHistory
from app.models.schemas import JobStatusResponse
from app.core.security import verify_api_key

router = APIRouter()

@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    x_api_key: str = Header(...),
    db: Session = Depends(get_db)
) -> JobStatusResponse:
    """작업 상태 조회"""

    await verify_api_key(x_api_key, db)

    job = db.query(JobHistory).filter_by(job_id=job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        progress_percent=calculate_progress(job),
        completed_at=job.completed_at,
        result_url=job.output_s3_url if job.status == "completed" else None,
        error=job.error_message if job.status == "failed" else None
    )

def calculate_progress(job: JobHistory) -> int:
    """작업 진행률 계산"""
    if job.status == "pending":
        return 0
    elif job.status == "running":
        return 50
    elif job.status == "completed":
        return 100
    else:
        return 0
```

---

## Phase 4: Celery 워커 (Day 16-20)

### 4.1 `app/workers/celery_config.py`

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "hwpx_skill",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,
)

celery_app.autodiscover_tasks(["app.workers"])
```

### 4.2 `app/workers/document_tasks.py`

```python
from app.workers.celery_config import celery_app
from app.models.database import JobHistory
from app.dependencies import SessionLocal, engine
from app.models.database import Base
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def create_document_task(self, job_id: str, markdown_content: str, style: str = "default"):
    """마크다운 → HWPX 변환 작업"""

    db = SessionLocal()

    try:
        # 1. Job 상태 업데이트
        job = db.query(JobHistory).filter_by(job_id=job_id).first()
        job.status = "running"
        db.commit()

        logger.info(f"[{job_id}] Converting markdown to HWPX")

        # 2. HWPX 생성
        from app.services.hwpx_service import HWPXService
        hwpx_service = HWPXService()
        output_path = hwpx_service.create_from_markdown(markdown_content, style)

        # 3. S3 업로드
        from app.services.storage_service import StorageService
        storage = StorageService()
        s3_url = storage.upload_file(output_path, bucket="hwpx-documents")

        # 4. Job 완료
        job.status = "completed"
        job.output_s3_url = s3_url
        job.output_size_bytes = output_path.stat().st_size
        db.commit()

        logger.info(f"[{job_id}] Completed successfully")

        # 5. 임시파일 정리
        output_path.unlink()

        return {"status": "completed", "url": s3_url}

    except Exception as exc:
        logger.error(f"[{job_id}] Error: {exc}")
        job.status = "failed"
        job.error_message = str(exc)
        job.retry_count += 1
        db.commit()

        # 재시도 (3초, 9초, 27초)
        raise self.retry(exc=exc, countdown=3 ** self.request.retries)

    finally:
        db.close()
```

---

## Phase 5: 서비스 계층 (Day 21-25)

### 5.1 `app/services/hwpx_service.py`

```python
from pathlib import Path
import tempfile
import uuid
import logging
from pyhwpxlib.api import create_document, save
from pyhwpxlib.converter import convert_markdown_to_hwpx

logger = logging.getLogger(__name__)

class HWPXService:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir())

    def create_from_markdown(self, markdown_content: str, style: str = "default") -> Path:
        """마크다운 → HWPX"""
        try:
            doc = create_document()
            convert_markdown_to_hwpx(doc, markdown_content, style=style)

            output_path = self.temp_dir / f"doc_{uuid.uuid4().hex}.hwpx"
            save(doc, str(output_path))

            logger.info(f"Created HWPX: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise
```

### 5.2 `app/services/storage_service.py`

```python
from pathlib import Path
from app.core.config import settings
import swiftclient.client as swift

class StorageService:
    def __init__(self):
        # NHN Cloud Object Storage (Swift API)
        self.auth_url = settings.NHN_OBJECT_STORAGE_URL
        self.container = settings.NHN_CONTAINER

    def upload_file(self, file_path: Path, bucket: str = "") -> str:
        """파일을 Object Storage에 업로드"""
        try:
            conn = swift.Connection(
                authurl=self.auth_url,
                user=settings.NHN_USERNAME,
                key=settings.NHN_PASSWORD,
                tenant_name=settings.NHN_TENANT_ID
            )

            with open(file_path, 'rb') as f:
                headers = {
                    'Content-Type': 'application/octet-stream'
                }

                object_name = f"{bucket}/{file_path.name}"
                conn.put_object(
                    self.container,
                    object_name,
                    f,
                    headers=headers
                )

            # 다운로드 URL 생성
            url = f"{self.auth_url}/{self.container}/{object_name}"
            return url

        except Exception as e:
            logging.error(f"S3 upload failed: {e}")
            raise
```

---

## Phase 6: 테스트 (Day 26-30)

### 6.1 `tests/test_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """헬스 체크"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_create_document_unauthorized():
    """인증 없이 요청"""
    response = client.post(
        "/v1/documents/create-from-markdown",
        data={"markdown_content": "# Test"}
    )
    assert response.status_code == 422  # Missing header

@pytest.mark.asyncio
async def test_create_document_with_api_key(test_api_key):
    """API 키로 문서 생성"""
    response = client.post(
        "/v1/documents/create-from-markdown",
        data={"markdown_content": "# Hello\n\nWorld"},
        headers={"x-api-key": test_api_key}
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
```

---

## Phase 7: 배포 준비 (Day 31-35)

### 7.1 Docker 빌드

```bash
# Dockerfile 생성
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 빌드
docker build -t hwpx-skill-api:latest .
```

### 7.2 Kubernetes 배포 준비

```bash
# 네임스페이스 생성
kubectl create namespace hwpx-skill

# 시크릿 생성
kubectl create secret generic db-secret \
  --from-literal=connection-string="postgresql://user:pass@host/db" \
  -n hwpx-skill
```

---

## Phase 8: 최종 테스트 & 배포 (Day 36-56)

### 8.1 통합 테스트

```python
@pytest.mark.asyncio
async def test_end_to_end_document_creation():
    """전체 문서 생성 플로우"""
    # 1. 문서 생성 요청
    response = client.post(
        "/v1/documents/create-from-markdown",
        data={"markdown_content": "# 테스트\n\n내용입니다."},
        headers={"x-api-key": test_api_key}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # 2. 작업 완료 대기
    import time
    for _ in range(30):
        response = client.get(
            f"/v1/jobs/{job_id}",
            headers={"x-api-key": test_api_key}
        )
        if response.json()["status"] == "completed":
            break
        time.sleep(1)

    # 3. 다운로드 URL 확인
    assert response.json()["result_url"] is not None
```

### 8.2 부하 테스트

```bash
# locust로 부하 테스트
pip install locust

cat > locustfile.py << 'EOF'
from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def create_document(self):
        self.client.post(
            "/v1/documents/create-from-markdown",
            data={"markdown_content": "# Test"},
            headers={"x-api-key": "test-key"}
        )
EOF

locust -f locustfile.py --host=http://localhost:8000
```

---

## 체크리스트

### Week 1
- [ ] 프로젝트 구조 설정
- [ ] Docker Compose 환경 실행
- [ ] 기본 API 엔드포인트 작성
- [ ] Unit tests 작성

### Week 2
- [ ] FastAPI 엔드포인트 완성 (문서, 형식)
- [ ] Celery 워커 구현
- [ ] API 키 인증/Rate limiting
- [ ] Integration tests

### Week 3
- [ ] S3 storage 통합
- [ ] 웹훅 시스템
- [ ] 모니터링 설정
- [ ] 성능 테스트

### Week 4
- [ ] Docker 이미지 최적화
- [ ] Kubernetes YAML 작성
- [ ] CI/CD 파이프라인
- [ ] 프로덕션 배포

---

**중요**: 각 Phase를 마칠 때마다 커밋하고, 정기적으로 코드 리뷰를 하세요.
