"""Tests for Phase 1: body text multi-run charPr preservation in form_pipeline."""
import os
import sys
import pytest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "templates"))

from form_pipeline import extract_form, generate_form

_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"


# ── Test fixtures ──

FORMS_WITH_BODY_TEXT = [
    ("서식SAMPLE1", "templates/sources/서식SAMPLE1.owpml"),
    ("서식SAMPLE2", "templates/sources/서식SAMPLE2.owpml"),
    ("별지11호", "templates/sources/별지 제11호 서식.hwpx"),
    ("SimpleTable", "templates/sources/SimpleTable.hwpx"),
]

MULTI_RUN_FORMS = [
    ("녹색환경", "samples/녹색환경지원센터 설립ㆍ운영에 관한 규정(안).owpml"),
    ("20250224", "samples/20250224112049_9119844.owpml"),
    ("ibgopongdang", "samples/ibgopongdang_230710.owpml"),
]


def _get_path(rel_path):
    abs_path = str(PROJECT_ROOT / rel_path)
    if not os.path.exists(abs_path):
        pytest.skip(f"Form not found: {abs_path}")
    return abs_path


def _clone(form_path, tmp_path):
    """Extract → generate round-trip, return clone path."""
    out = str(tmp_path / "clone.hwpx")
    data = extract_form(form_path)
    generate_form(data, out)
    return out


def _count_text_runs(para):
    """Count runs containing text in a paragraph."""
    return sum(
        1 for r in para['runs']
        if any(c['type'] == 'text' for c in r['contents'])
    )


# ── Regression: existing forms still work ──

class TestRegression:
    @pytest.fixture(params=FORMS_WITH_BODY_TEXT, ids=[f[0] for f in FORMS_WITH_BODY_TEXT])
    def form_path(self, request):
        return _get_path(request.param[1])

    def test_clone_generates_valid_hwpx(self, form_path, tmp_path):
        out = _clone(form_path, tmp_path)
        assert os.path.exists(out)
        assert zipfile.is_zipfile(out)

    def test_table_count_preserved(self, form_path, tmp_path):
        orig = extract_form(form_path)
        clone = extract_form(_clone(form_path, tmp_path))
        assert len(orig["tables"]) == len(clone["tables"])

    def test_paragraph_count_preserved(self, form_path, tmp_path):
        orig = extract_form(form_path)
        clone = extract_form(_clone(form_path, tmp_path))
        assert len(orig["paragraphs"]) == len(clone["paragraphs"])


# ── Multi-run preservation ──

class TestMultiRunPreservation:
    @pytest.fixture(params=MULTI_RUN_FORMS, ids=[f[0] for f in MULTI_RUN_FORMS])
    def form_path(self, request):
        return _get_path(request.param[1])

    def test_run_count_preserved(self, form_path, tmp_path):
        """Body text paragraphs must preserve run count after clone."""
        orig = extract_form(form_path)
        clone = extract_form(_clone(form_path, tmp_path))

        mismatches = 0
        total = 0
        for op, cp in zip(orig['paragraphs'], clone['paragraphs']):
            if not op['has_table'] and op['texts'] and not op['has_secpr']:
                total += 1
                if _count_text_runs(op) != _count_text_runs(cp):
                    mismatches += 1

        if total > 0:
            match_rate = (total - mismatches) / total
            assert match_rate >= 0.95, (
                f"Run count match rate {match_rate:.0%} < 95% "
                f"({mismatches}/{total} mismatches)"
            )

    def test_charpr_diversity_preserved(self, form_path, tmp_path):
        """Clone must use at least as many distinct charPr IDs as original for body text."""
        orig = extract_form(form_path)
        clone = extract_form(_clone(form_path, tmp_path))

        orig_cprs = set()
        clone_cprs = set()
        for op, cp in zip(orig['paragraphs'], clone['paragraphs']):
            if not op['has_table'] and op['texts']:
                for r in op['runs']:
                    orig_cprs.add(r['charPrIDRef'])
                for r in cp['runs']:
                    clone_cprs.add(r['charPrIDRef'])

        # Clone should have comparable charPr diversity
        assert len(clone_cprs) >= len(orig_cprs) * 0.8, (
            f"charPr diversity dropped: orig={len(orig_cprs)}, clone={len(clone_cprs)}"
        )


# ── XML-level verification ──

class TestXMLStructure:
    @pytest.fixture(params=MULTI_RUN_FORMS[:1], ids=[MULTI_RUN_FORMS[0][0]])
    def form_path(self, request):
        return _get_path(request.param[1])

    def test_body_p_has_multiple_runs_in_xml(self, form_path, tmp_path):
        """Generated HWPX section XML should contain p elements with multiple hp:run children."""
        out = _clone(form_path, tmp_path)
        with zipfile.ZipFile(out) as z:
            section_xml = z.read('Contents/section0.xml').decode('utf-8')

        root = ET.fromstring(section_xml)
        multi_run_count = 0
        for p in root.findall(f'.//{_HP}p'):
            runs = p.findall(f'{_HP}run')
            if len(runs) > 1:
                multi_run_count += 1

        assert multi_run_count > 0, "No body paragraphs with multiple runs found in section XML"

    def test_runs_have_distinct_charpr(self, form_path, tmp_path):
        """Within multi-run paragraphs, different runs should have different charPrIDRef."""
        out = _clone(form_path, tmp_path)
        with zipfile.ZipFile(out) as z:
            section_xml = z.read('Contents/section0.xml').decode('utf-8')

        root = ET.fromstring(section_xml)
        distinct_found = False
        for p in root.findall(f'.//{_HP}p'):
            runs = p.findall(f'{_HP}run')
            if len(runs) > 1:
                cprs = {r.get('charPrIDRef') for r in runs}
                if len(cprs) > 1:
                    distinct_found = True
                    break

        assert distinct_found, "No paragraph found with runs having distinct charPrIDRef"


# ── Edge cases ──

class TestEdgeCases:
    def test_empty_text_p(self, tmp_path):
        """Empty text paragraphs should not crash."""
        form_path = _get_path("templates/sources/SimpleTable.hwpx")
        out = _clone(form_path, tmp_path)
        assert os.path.exists(out)

    def test_single_run_still_works(self, tmp_path):
        """Forms with only single-run body text should still work."""
        form_path = _get_path("templates/sources/별지 제11호 서식.hwpx")
        orig = extract_form(form_path)
        clone = extract_form(_clone(form_path, tmp_path))

        for op, cp in zip(orig['paragraphs'], clone['paragraphs']):
            if not op['has_table'] and op['texts']:
                assert _count_text_runs(cp) >= 1
