"""Example 09: LLM integration — generate HWPX from Claude API response.

Requires: pip install anthropic
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import anthropic
except ImportError:
    print("Install anthropic: pip install anthropic")
    sys.exit(1)

from pyhwpxlib.api import create_document, save
from pyhwpxlib.converter import convert_markdown_to_hwpx as convert_md_to_hwpx

def generate_report_hwpx(topic: str, output_path: str = "report.hwpx") -> str:
    """Ask Claude to write a report and save it as HWPX."""
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"다음 주제로 간단한 보고서를 마크다운 형식으로 작성해 주세요: {topic}\n"
                       "제목, 개요, 주요 내용 3개 항목, 결론을 포함해 주세요."
        }]
    )

    markdown_text = message.content[0].text
    doc = create_document()
    convert_md_to_hwpx(doc, markdown_text)
    save(doc, output_path)
    print(f"Report saved: {output_path}")
    return output_path


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Python의 장단점"
    generate_report_hwpx(topic, "llm_report.hwpx")
