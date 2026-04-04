"""
Form accuracy test — extract → clone → compare cycle for 10 core forms.

Usage:
    python form_accuracy_test.py              # test all 10 forms
    python form_accuracy_test.py <form_path>  # test single form
"""
import json
import os
import sys
import tempfile
import logging

# Silence noisy fallback messages during testing
logging.basicConfig(level=logging.WARNING)

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from templates.form_pipeline import extract_form, generate_form

# ============================================================
# 10 core forms (path relative to project root)
# ============================================================
CORE_FORMS = [
    ("의견제출서 (sample)",       "templates/sources/sample_의견제출서.hwpx"),
    ("의견제출서 (template)",     "templates/sources/template_의견제출서.hwpx"),
    ("근로지원인서비스신청서",       "templates/sources/근로지원인서비스신청서.hwpx"),
    ("별지 제11호 서식",           "templates/sources/별지 제11호 서식.hwpx"),
    ("서식SAMPLE1",               "templates/sources/서식SAMPLE1.owpml"),
    ("서식SAMPLE2",               "templates/sources/서식SAMPLE2.owpml"),
    ("SimpleTable",               "templates/sources/SimpleTable.hwpx"),
    ("HeaderFooter",              "templates/sources/HeaderFooter.hwpx"),
    ("별지 제11호 서식 (gen)",     "templates/sources/별지 제11호 서식_generated.hwpx"),
    ("NCS직무설명자료",             "docs/sample_NCS직무설명자료.hwpx"),
]


def _score_tables(orig_tables, clone_tables):
    """Score accuracy of clone tables vs original.

    Returns (score 0.0-1.0, details dict)
    """
    if not orig_tables and not clone_tables:
        return 1.0, {"msg": "no tables — OK"}

    if len(orig_tables) != len(clone_tables):
        return 0.0, {
            "msg": f"table count mismatch: {len(orig_tables)} → {len(clone_tables)}"
        }

    total_checks = 0
    passed_checks = 0
    details = []

    for ti, (ot, ct) in enumerate(zip(orig_tables, clone_tables)):
        # Table dimensions
        if ot["rows"] == ct["rows"] and ot["cols"] == ct["cols"]:
            passed_checks += 1
        else:
            details.append(f"tbl[{ti}] dims {ot['rows']}×{ot['cols']} → {ct['rows']}×{ct['cols']}")
        total_checks += 1

        # Cell count
        if len(ot["cells"]) == len(ct["cells"]):
            passed_checks += 1
        else:
            details.append(f"tbl[{ti}] cell count {len(ot['cells'])} → {len(ct['cells'])}")
        total_checks += 1

        # Merge count
        if len(ot["merges"]) == len(ct["merges"]):
            passed_checks += 1
        else:
            details.append(f"tbl[{ti}] merge count {len(ot['merges'])} → {len(ct['merges'])}")
        total_checks += 1

        # Table width
        if ot.get("width") == ct.get("width"):
            passed_checks += 1
        else:
            details.append(f"tbl[{ti}] width {ot.get('width')} → {ct.get('width')}")
        total_checks += 1

        # Text content per cell
        orig_texts = {(c["row"], c["col"]): c.get("text", "") for c in ot["cells"]}
        clone_texts = {(c["row"], c["col"]): c.get("text", "") for c in ct["cells"]}
        text_matches = sum(
            1 for k in orig_texts if orig_texts.get(k) == clone_texts.get(k)
        )
        total_checks += len(orig_texts)
        passed_checks += text_matches
        if text_matches < len(orig_texts):
            diff = len(orig_texts) - text_matches
            details.append(f"tbl[{ti}] {diff}/{len(orig_texts)} cells have text mismatch")

    score = passed_checks / total_checks if total_checks > 0 else 1.0
    return score, {"passed": passed_checks, "total": total_checks, "issues": details}


def test_form(name, path):
    """Test one form: extract → clone → compare.

    Returns (score, details)
    """
    abs_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.exists(abs_path):
        return None, f"File not found: {abs_path}"

    try:
        # Step 1: extract original
        orig_data = extract_form(abs_path)
    except Exception as e:
        return 0.0, f"extract failed: {e}"

    with tempfile.NamedTemporaryFile(suffix=".hwpx", delete=False) as tf:
        clone_path = tf.name

    try:
        # Step 2: generate clone
        generate_form(orig_data, clone_path)

        # Step 3: extract clone
        clone_data = extract_form(clone_path)

        # Step 4: score
        score, details = _score_tables(orig_data["tables"], clone_data["tables"])
        return score, details

    except Exception as e:
        return 0.0, f"generate/compare failed: {e}"
    finally:
        if os.path.exists(clone_path):
            os.unlink(clone_path)


def main():
    if len(sys.argv) >= 2:
        forms = [("custom", sys.argv[1])]
    else:
        forms = [(n, p) for n, p in CORE_FORMS]

    print("\n" + "=" * 70)
    print("Form Pipeline Accuracy Report — 핵심 양식 10종")
    print("=" * 70)

    results = []
    for name, path in forms:
        score, details = test_form(name, path)
        results.append((name, path, score, details))

        if score is None:
            status = "SKIP"
            pct = "  N/A"
        elif score >= 1.0:
            status = " OK "
            pct = "100%"
        elif score >= 0.9:
            status = "WARN"
            pct = f"{score*100:.1f}%"
        else:
            status = "FAIL"
            pct = f"{score*100:.1f}%"

        print(f"[{status}] {pct}  {name}")
        if isinstance(details, str):
            print(f"       ↳ {details}")
        elif details.get("issues"):
            for issue in details["issues"]:
                print(f"       ↳ {issue}")

    # Summary
    scored = [(s, d) for _, _, s, d in results if s is not None]
    if scored:
        avg = sum(s for s, _ in scored) / len(scored)
        perfect = sum(1 for s, _ in scored if s >= 1.0)
        print("\n" + "-" * 70)
        print(f"총 {len(scored)}종 테스트 | 완벽 재현: {perfect}종 | 평균 정확도: {avg*100:.1f}%")
        if avg >= 1.0:
            print("✅ 100% 정확도 달성")
        else:
            print(f"⚠️  목표까지 {(1.0 - avg)*100:.1f}% 남음")
    print()


if __name__ == "__main__":
    main()
