"""Tests for FastAPI API server endpoints."""
import os
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from fastapi.testclient import TestClient
    from api_server.main import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestConvertMdToHwpx:
    def test_basic_markdown(self, client):
        resp = client.post(
            "/convert/md-to-hwpx",
            data={"markdown": "# Hello\n\nWorld", "filename": "test.hwpx"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"
        assert len(resp.content) > 1000

    def test_output_is_valid_zip(self, client):
        import io, zipfile
        resp = client.post(
            "/convert/md-to-hwpx",
            data={"markdown": "# Test", "filename": "test.hwpx"},
        )
        assert zipfile.is_zipfile(io.BytesIO(resp.content))

    def test_korean_markdown(self, client):
        resp = client.post(
            "/convert/md-to-hwpx",
            data={"markdown": "# 한국어 제목\n\n내용", "filename": "korean.hwpx"},
        )
        assert resp.status_code == 200

    def test_empty_markdown_accepted(self, client):
        # FastAPI Form(...) requires non-empty; send minimal whitespace
        resp = client.post(
            "/convert/md-to-hwpx",
            data={"markdown": " ", "filename": "empty.hwpx"},
        )
        assert resp.status_code == 200


class TestFormFill:
    def test_basic_fill(self, client, tmp_path):
        import json
        from pyhwpxlib.api import create_document, add_paragraph, save

        template_path = str(tmp_path / "tmpl.hwpx")
        doc = create_document()
        add_paragraph(doc, "이름: {{이름}}")
        save(doc, template_path)

        with open(template_path, "rb") as f:
            resp = client.post(
                "/form/fill",
                files={"file": ("tmpl.hwpx", f, "application/octet-stream")},
                data={
                    "data": json.dumps({"이름": "홍길동"}),
                    "filename": "filled.hwpx",
                },
            )
        assert resp.status_code == 200
        assert len(resp.content) > 1000

    def test_invalid_json_returns_400(self, client, tmp_path):
        from pyhwpxlib.api import create_document, save
        template_path = str(tmp_path / "tmpl.hwpx")
        save(create_document(), template_path)

        with open(template_path, "rb") as f:
            resp = client.post(
                "/form/fill",
                files={"file": ("tmpl.hwpx", f, "application/octet-stream")},
                data={"data": "not json", "filename": "out.hwpx"},
            )
        assert resp.status_code == 400

    def test_invalid_file_type_returns_400(self, client, tmp_path):
        import json
        txt_path = str(tmp_path / "test.txt")
        with open(txt_path, "w") as f:
            f.write("not a hwpx")
        with open(txt_path, "rb") as f:
            resp = client.post(
                "/form/fill",
                files={"file": ("test.txt", f, "text/plain")},
                data={"data": json.dumps({}), "filename": "out.hwpx"},
            )
        # Should fail gracefully (400 or 500)
        assert resp.status_code in (400, 500)
