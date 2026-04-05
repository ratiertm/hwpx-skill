"""Tests for Phase 2: stability improvements — exception handling, tempfile, graceful degradation."""
import os
import sys
import pytest
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "templates"))

from form_pipeline import extract_form, generate_form


# ── Test fixtures ──

FORMS = [
    ("sample_의견제출서", "templates/sources/sample_의견제출서.hwpx"),
    ("별지11호", "templates/sources/별지 제11호 서식.hwpx"),
    ("서식SAMPLE1", "templates/sources/서식SAMPLE1.owpml"),
    ("SimpleTable", "templates/sources/SimpleTable.hwpx"),
]


def _get_path(rel_path):
    abs_path = str(PROJECT_ROOT / rel_path)
    if not os.path.exists(abs_path):
        pytest.skip(f"Form not found: {abs_path}")
    return abs_path


# ── TemporaryDirectory 사용 확인 ──

class TestTempFileCleanup:
    """tempfile.mktemp → TemporaryDirectory 전환 검증."""

    def test_no_temp_files_left_after_generate(self, tmp_path):
        """generate_form 실행 후 임시 파일이 남지 않아야 함."""
        form_path = _get_path("templates/sources/서식SAMPLE1.owpml")
        output = str(tmp_path / "output.hwpx")

        # 생성 전 tmp 디렉토리 파일 목록
        temp_dir = tempfile.gettempdir()
        before = set(os.listdir(temp_dir))

        data = extract_form(form_path)
        generate_form(data, output)

        # 생성 후 새로 생긴 hwpx 임시파일 없어야 함
        after = set(os.listdir(temp_dir))
        new_files = {f for f in (after - before) if f.endswith('.hwpx')}
        assert len(new_files) == 0, f"Temp files not cleaned up: {new_files}"

    def test_output_valid_after_header_replacement(self, tmp_path):
        """header 교체 후에도 유효한 HWPX 파일이어야 함."""
        form_path = _get_path("templates/sources/서식SAMPLE1.owpml")
        output = str(tmp_path / "output.hwpx")

        data = extract_form(form_path)
        generate_form(data, output)

        assert os.path.exists(output)
        assert zipfile.is_zipfile(output)

        with zipfile.ZipFile(output) as z:
            assert 'Contents/header.xml' in z.namelist()
            assert 'Contents/section0.xml' in z.namelist()


# ── 예외 처리 검증 ──

class TestExceptionHandling:
    """except Exception as e → 구체적 예외 + 로깅 검증."""

    def test_no_bare_except_in_form_pipeline(self):
        """form_pipeline.py에 bare except (except:)가 없어야 함."""
        fp_path = PROJECT_ROOT / "templates" / "form_pipeline.py"
        content = fp_path.read_text()

        import re
        # bare except: (except 뒤에 바로 :)
        bare = re.findall(r'^\s*except\s*:', content, re.MULTILINE)
        assert len(bare) == 0, f"Bare except found: {bare}"

    def test_no_except_exception_pass_in_form_pipeline(self):
        """form_pipeline.py에 except Exception: pass 패턴이 없어야 함."""
        fp_path = PROJECT_ROOT / "templates" / "form_pipeline.py"
        content = fp_path.read_text()

        import re
        # except Exception:\n            pass 패턴
        silent = re.findall(r'except\s+Exception\s*:\s*\n\s*pass', content)
        assert len(silent) == 0, f"Silent exception swallow found: {silent}"

    def test_no_bare_except_in_html_to_hwpx(self):
        """html_to_hwpx.py에 bare except가 없어야 함."""
        fp_path = PROJECT_ROOT / "pyhwpxlib" / "html_to_hwpx.py"
        content = fp_path.read_text()

        import re
        bare = re.findall(r'^\s*except\s*:', content, re.MULTILINE)
        assert len(bare) == 0, f"Bare except found: {bare}"

    def test_no_bare_except_in_html_converter(self):
        """html_converter.py에 bare except가 없어야 함."""
        fp_path = PROJECT_ROOT / "pyhwpxlib" / "html_converter.py"
        content = fp_path.read_text()

        import re
        bare = re.findall(r'^\s*except\s*:', content, re.MULTILINE)
        assert len(bare) == 0, f"Bare except found: {bare}"

    def test_no_indexerror_exception_combo(self):
        """(IndexError, Exception) 같은 무의미한 중복이 없어야 함."""
        fp_path = PROJECT_ROOT / "templates" / "form_pipeline.py"
        content = fp_path.read_text()

        assert '(IndexError, Exception)' not in content, \
            "Redundant (IndexError, Exception) found — Exception already covers IndexError"


# ── Graceful degradation ──

class TestGracefulDegradation:
    """잘못된 입력에도 크래시하지 않고 처리."""

    def test_generate_with_empty_tables(self, tmp_path):
        """빈 tables로도 크래시 없이 생성."""
        form_path = _get_path("templates/sources/SimpleTable.hwpx")
        output = str(tmp_path / "output.hwpx")

        data = extract_form(form_path)
        # 테이블 셀 데이터를 비워도 동작해야 함
        for tbl in data.get('tables', []):
            for cell in tbl.get('cells', []):
                cell['lines'] = [{'runs': [{'text': '', 'charPr': '0'}], 'horizontal': 'LEFT'}]

        generate_form(data, output)
        assert os.path.exists(output)

    def test_extract_nonexistent_file_raises(self):
        """존재하지 않는 파일 extract 시 적절한 예외."""
        with pytest.raises((FileNotFoundError, KeyError, zipfile.BadZipFile)):
            extract_form("/nonexistent/file.hwpx")


# ── Regression: 기존 299개 테스트와 충돌 없음 확인 ──

class TestRegression:
    """Phase 2 변경이 기존 기능을 깨뜨리지 않음."""

    @pytest.fixture(params=FORMS, ids=[f[0] for f in FORMS])
    def form_path(self, request):
        return _get_path(request.param[1])

    def test_roundtrip_still_works(self, form_path, tmp_path):
        output = str(tmp_path / "clone.hwpx")
        orig = extract_form(form_path)
        generate_form(orig, output)
        clone = extract_form(output)
        assert len(orig["tables"]) == len(clone["tables"])

    def test_paragraph_count_preserved(self, form_path, tmp_path):
        output = str(tmp_path / "clone.hwpx")
        orig = extract_form(form_path)
        generate_form(orig, output)
        clone = extract_form(output)
        assert len(orig["paragraphs"]) == len(clone["paragraphs"])
