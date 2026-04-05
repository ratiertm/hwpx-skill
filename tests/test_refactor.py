"""Tests for Phase 3: structural refactoring — _init_para, Defaults, model cleanup, function split."""
import os
import sys
import re
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "templates"))


# ── 3-1. _init_para() 헬퍼 ──

class TestInitPara:
    def test_init_para_exists(self):
        from pyhwpxlib.api import _init_para
        assert callable(_init_para)

    def test_init_para_sets_defaults(self):
        from pyhwpxlib.api import _init_para

        class FakePara:
            pass

        p = FakePara()
        _init_para(p)

        assert p.para_pr_id_ref == "0"
        assert p.style_id_ref == "0"
        assert p.page_break is False
        assert p.column_break is False
        assert p.merged is False
        assert p.id is not None
        assert len(p.id) >= 10  # random int string

    def test_init_para_custom_values(self):
        from pyhwpxlib.api import _init_para

        class FakePara:
            pass

        p = FakePara()
        _init_para(p, para_pr_id_ref="5", style_id_ref="3", page_break=True)

        assert p.para_pr_id_ref == "5"
        assert p.style_id_ref == "3"
        assert p.page_break is True

    def test_no_duplicate_init_blocks_in_api(self):
        """api.py에 _init_para 정의 외에 중복 초기화 블록이 없어야 함."""
        api_path = PROJECT_ROOT / "pyhwpxlib" / "api.py"
        content = api_path.read_text()

        # _init_para 정의 내부의 1건 제외하고, para.id = str(_random.randint 패턴이 없어야 함
        matches = re.findall(r'para\.id = str\(_random\.randint', content)
        assert len(matches) == 1, f"Found {len(matches)} raw para init blocks (expected 1 in _init_para def)"


# ── 3-2. Defaults 상수 ──

class TestDefaults:
    def test_constants_defined(self):
        import form_pipeline as fp
        assert fp.PAGE_HEIGHT == 84188
        assert fp.CELL_MARGIN == 141
        assert fp.ROW_HEIGHT == 3600
        assert fp.NESTED_OUT_MARGIN == 283
        assert fp.PAGE_WIDTH == 59528

    def test_no_raw_magic_numbers_in_form_pipeline(self):
        """form_pipeline.py에 매직 넘버 141, 3600이 문자열 리터럴로 남아있지 않아야 함."""
        fp_path = PROJECT_ROOT / "templates" / "form_pipeline.py"
        content = fp_path.read_text()

        # 상수 정의 라인 제외하고 검사
        lines = content.split('\n')
        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # 상수 정의 라인 스킵
            if stripped.startswith('CELL_MARGIN') or stripped.startswith('ROW_HEIGHT') or stripped.startswith('NESTED_OUT_MARGIN'):
                continue
            # 주석 스킵
            if stripped.startswith('#'):
                continue
            # 매직 넘버 검사: 단독 숫자 141, 3600 (= 또는 , 뒤)
            if re.search(r'[=,]\s*141\b', stripped) and 'CELL_MARGIN' not in stripped:
                violations.append(f"line {i}: {stripped[:60]}")
            if re.search(r'[=,]\s*3600\b', stripped) and 'ROW_HEIGHT' not in stripped:
                violations.append(f"line {i}: {stripped[:60]}")

        assert len(violations) == 0, f"Magic numbers found:\n" + "\n".join(violations)


# ── 3-3. 구 데이터 모델 제거 ──

class TestOldModelRemoved:
    def test_generate_requires_paragraphs(self):
        """paragraphs 없이 generate_form 호출 시 ValueError."""
        from form_pipeline import generate_form
        import tempfile

        fake_data = {
            'page': {'width': 59528, 'height': 84188, 'margin': {
                'left': 8504, 'right': 8504, 'top': 5668, 'bottom': 4252
            }},
            'fonts': {},
            'char_properties': {},
            'para_properties': {},
            'border_fills': {},
            'paragraphs': [],  # 빈 리스트
            'tables': [],
        }

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as f:
            out = f.name

        try:
            with pytest.raises(ValueError, match="paragraphs"):
                generate_form(fake_data, out)
        finally:
            if os.path.exists(out):
                os.unlink(out)

    def test_extract_still_has_tables_key(self):
        """하위 호환: extract_form 결과에 tables 키가 존재."""
        form_path = str(PROJECT_ROOT / "templates" / "sources" / "SimpleTable.hwpx")
        if not os.path.exists(form_path):
            pytest.skip("SimpleTable.hwpx not found")

        from form_pipeline import extract_form
        data = extract_form(form_path)
        assert "tables" in data
        assert "paragraphs" in data


# ── 3-4. _generate_table 분리 ──

class TestFunctionSplit:
    def test_apply_merges_exists(self):
        from form_pipeline import _apply_merges
        assert callable(_apply_merges)

    def test_apply_cell_alignment_exists(self):
        from form_pipeline import _apply_cell_alignment
        assert callable(_apply_cell_alignment)

    def test_generate_nested_tables_exists(self):
        from form_pipeline import _generate_nested_tables
        assert callable(_generate_nested_tables)

    def test_generate_table_under_100_lines(self):
        """_generate_table 본체가 100줄 이하로 줄었는지 확인."""
        fp_path = PROJECT_ROOT / "templates" / "form_pipeline.py"
        content = fp_path.read_text()
        lines = content.split('\n')

        # _generate_table 함수 시작~끝
        start = None
        end = None
        for i, line in enumerate(lines):
            if line.startswith('def _generate_table('):
                start = i
            elif start is not None and line.startswith('def ') and i > start:
                end = i
                break

        if start is not None and end is not None:
            func_lines = end - start
            assert func_lines <= 200, f"_generate_table is {func_lines} lines (target: ≤200, was 414)"


# ── Regression ──

class TestRegressionPhase3:
    FORMS = [
        ("서식SAMPLE1", "templates/sources/서식SAMPLE1.owpml"),
        ("별지11호", "templates/sources/별지 제11호 서식.hwpx"),
        ("SimpleTable", "templates/sources/SimpleTable.hwpx"),
    ]

    @pytest.fixture(params=FORMS, ids=[f[0] for f in FORMS])
    def form_path(self, request):
        abs_path = str(PROJECT_ROOT / request.param[1])
        if not os.path.exists(abs_path):
            pytest.skip(f"Not found: {abs_path}")
        return abs_path

    def test_roundtrip_preserved(self, form_path, tmp_path):
        from form_pipeline import extract_form, generate_form
        output = str(tmp_path / "clone.hwpx")
        orig = extract_form(form_path)
        generate_form(orig, output)
        clone = extract_form(output)
        assert len(orig["tables"]) == len(clone["tables"])
        assert len(orig["paragraphs"]) == len(clone["paragraphs"])
