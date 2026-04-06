"""
HWPX Helper — 자주 쓰는 패턴을 모은 헬퍼 스크립트.

Usage:
    python hwpx_helper.py create-report "보고서 제목" -o report.hwpx
    python hwpx_helper.py fill-form input.hwpx data.json -o filled.hwpx
    python hwpx_helper.py html2hwpx input.html -o output.hwpx
    python hwpx_helper.py hwpx2html input.hwpx -o output.html
    python hwpx_helper.py extract-text input.hwpx
    python hwpx_helper.py clone-form input.hwpx -o clone.hwpx
"""
import argparse
import json
import sys
import os

# Ensure pyhwpxlib is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
# Try to find pyhwpxlib relative to skill location
for candidate in [
    os.path.join(SKILL_DIR, '..'),          # skill is inside hwpx-skill/
    os.path.join(SKILL_DIR, '..', '..'),    # skill is installed elsewhere
]:
    api_path = os.path.join(candidate, 'pyhwpxlib', 'api.py')
    if os.path.exists(api_path):
        sys.path.insert(0, os.path.abspath(candidate))
        break


def cmd_create_report(args):
    """간단한 보고서 HWPX 생성."""
    from pyhwpxlib.api import create_document, add_heading, add_paragraph, save

    doc = create_document()
    add_heading(doc, args.title, level=1)

    if args.body:
        for line in args.body:
            add_paragraph(doc, line)
    else:
        add_paragraph(doc, "(본문을 여기에 작성하세요)")

    save(doc, args.output)
    print(f"Created: {args.output}")


def cmd_fill_form(args):
    """양식 HWPX에 JSON 데이터를 채워넣기."""
    sys.path.insert(0, os.path.join(SKILL_DIR, '..'))
    from templates.form_pipeline import extract_form, generate_form

    # Load form structure
    schema = extract_form(args.input)

    # Load fill data
    with open(args.data, encoding='utf-8') as f:
        fill_data = json.load(f)

    # Fill cells by coordinate or label
    for table in schema.get("tables", []):
        for cell in table.get("cells", []):
            key = f"{cell['row']},{cell['col']}"
            if key in fill_data:
                cell["text"] = fill_data[key]
            # Also try matching by existing text as label
            label = cell.get("text", "").strip()
            if label in fill_data:
                cell["text"] = fill_data[label]

    generate_form(schema, args.output)
    print(f"Filled: {args.output}")


def cmd_html2hwpx(args):
    """HTML 파일을 HWPX로 변환."""
    from pyhwpxlib.api import create_document, convert_html_to_hwpx, save

    with open(args.input, encoding='utf-8') as f:
        html = f.read()

    doc = create_document()
    convert_html_to_hwpx(doc, html)
    save(doc, args.output)
    print(f"Converted: {args.output}")


def cmd_hwpx2html(args):
    """HWPX 파일을 HTML로 변환."""
    from pyhwpxlib.api import convert_hwpx_to_html

    html = convert_hwpx_to_html(args.input)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Converted: {args.output}")
    else:
        print(html)


def cmd_extract_text(args):
    """HWPX에서 텍스트 추출."""
    from pyhwpxlib.api import extract_text
    print(extract_text(args.input))


def cmd_clone_form(args):
    """양식 HWPX를 구조적으로 복제."""
    sys.path.insert(0, os.path.join(SKILL_DIR, '..'))
    from templates.form_pipeline import extract_form, generate_form

    schema = extract_form(args.input)
    generate_form(schema, args.output)
    print(f"Cloned: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="HWPX Helper")
    sub = parser.add_subparsers(dest="command")

    # create-report
    p = sub.add_parser("create-report", help="빈 보고서 HWPX 생성")
    p.add_argument("title", help="보고서 제목")
    p.add_argument("--body", "-b", nargs="*", help="본문 문단들")
    p.add_argument("--output", "-o", default="report.hwpx")

    # fill-form
    p = sub.add_parser("fill-form", help="양식에 데이터 채우기")
    p.add_argument("input", help="원본 양식 .hwpx")
    p.add_argument("data", help="채울 데이터 JSON 파일")
    p.add_argument("--output", "-o", default="filled.hwpx")

    # html2hwpx
    p = sub.add_parser("html2hwpx", help="HTML → HWPX 변환")
    p.add_argument("input", help="입력 HTML 파일")
    p.add_argument("--output", "-o", default="output.hwpx")

    # hwpx2html
    p = sub.add_parser("hwpx2html", help="HWPX → HTML 변환")
    p.add_argument("input", help="입력 HWPX 파일")
    p.add_argument("--output", "-o", default=None)

    # extract-text
    p = sub.add_parser("extract-text", help="HWPX에서 텍스트 추출")
    p.add_argument("input", help="입력 HWPX 파일")

    # clone-form
    p = sub.add_parser("clone-form", help="양식 복제")
    p.add_argument("input", help="원본 양식 .hwpx")
    p.add_argument("--output", "-o", default="clone.hwpx")

    args = parser.parse_args()

    commands = {
        "create-report": cmd_create_report,
        "fill-form": cmd_fill_form,
        "html2hwpx": cmd_html2hwpx,
        "hwpx2html": cmd_hwpx2html,
        "extract-text": cmd_extract_text,
        "clone-form": cmd_clone_form,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
