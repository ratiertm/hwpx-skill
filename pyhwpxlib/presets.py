"""Document type presets for HwpxBuilder.

Based on Korean government document standards and HwpForge style references.
Each preset defines page setup, fonts, spacing, and structural patterns.
"""

# Page setup units: 1mm ≈ 283 HWP units

PRESETS = {
    "official": {
        "name": "공문서",
        "description": "행정업무운영규정 기반 공문서",
        "page": {
            "width": 59528,    # A4
            "height": 84186,
            "margin_left": 5660,   # 20mm
            "margin_right": 5660,
            "margin_top": 8490,    # 30mm
            "margin_bottom": 4245, # 15mm
        },
        "title": {"font_size": 16, "bold": True, "alignment": "CENTER"},
        "heading2": {"font_size": 14, "bold": True},
        "body": {"font_size": 12},
        "line_spacing": 180,
        "numbering": "1. 가. 1) 가)",
        "footer_text": None,  # 쪽번호 없음 (공문서 표준)
        "colors": {
            "primary": "#1a1a1a",
            "heading": "#000000",
            "meta": "#333333",
        },
    },
    "report": {
        "name": "보고서",
        "description": "연구/용역 결과 보고서",
        "page": {
            "width": 59528,
            "height": 84186,
            "margin_left": 8490,   # 30mm
            "margin_right": 8490,
            "margin_top": 7075,    # 25mm
            "margin_bottom": 7075,
        },
        "title": {"font_size": 18, "bold": True, "alignment": "CENTER"},
        "heading2": {"font_size": 16, "bold": True},
        "heading3": {"font_size": 14, "bold": True},
        "body": {"font_size": 11},
        "line_spacing": 170,
        "numbering": "제1장 제1절",
        "footer_text": "- {page} -",
        "colors": {
            "primary": "#2c3e50",
            "heading": "#1a252f",
            "accent": "#2980b9",
            "meta": "#7f8c8d",
            "table_header": "#2c3e50",
            "table_header_text": "#ffffff",
            "highlight": "#ebf5fb",
        },
    },
    "proposal": {
        "name": "제안서",
        "description": "정부 RFP 대응 제안서",
        "page": {
            "width": 59528,
            "height": 84186,
            "margin_left": 7075,   # 25mm
            "margin_right": 7075,
            "margin_top": 5660,    # 20mm
            "margin_bottom": 5660,
        },
        "title": {"font_size": 22, "bold": True, "alignment": "CENTER"},
        "heading2": {"font_size": 16, "bold": True},
        "heading3": {"font_size": 13, "bold": True},
        "body": {"font_size": 11},
        "line_spacing": 160,
        "numbering": "1. 1.1 1.1.1",
        "footer_text": "- {page} -",
        "colors": {
            "primary": "#1b3a5c",
            "heading": "#1b3a5c",
            "accent": "#c0392b",
            "meta": "#666666",
            "table_header": "#1b3a5c",
            "table_header_text": "#ffffff",
            "highlight": "#eaf2f8",
            "cover_bg": "#1b3a5c",
            "cover_text": "#ffffff",
        },
    },
}


def get_preset(name: str) -> dict:
    """Get a document preset by name."""
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset: {name}. Available: {available}")
    return PRESETS[name]


def build_cover_page(builder, preset: dict, title: str,
                     subtitle: str = "", organization: str = "", date: str = ""):
    """Build a professional cover page using the preset style."""
    colors = preset.get("colors", {})
    ts = preset.get("title", {})

    # Top spacer
    builder.add_paragraph("", font_size=40)
    builder.add_paragraph("", font_size=40)

    # Organization
    if organization:
        builder.add_paragraph(organization,
                              font_size=14, text_color=colors.get("meta", "#666666"),
                              alignment="CENTER")
        builder.add_paragraph("")

    # Title
    builder.add_paragraph(title,
                          bold=ts.get("bold", True),
                          font_size=ts.get("font_size", 18),
                          text_color=colors.get("heading", "#000000"),
                          alignment=ts.get("alignment", "CENTER"))

    # Subtitle
    if subtitle:
        builder.add_paragraph("")
        builder.add_paragraph(subtitle,
                              font_size=14,
                              text_color=colors.get("meta", "#666666"),
                              alignment="CENTER")

    # Date
    if date:
        builder.add_paragraph("", font_size=30)
        builder.add_paragraph("", font_size=30)
        builder.add_paragraph(date,
                              font_size=13,
                              text_color=colors.get("meta", "#666666"),
                              alignment="CENTER")

    builder.add_page_break()


def build_official_footer(builder, preset: dict,
                          sender: str = "", receiver: str = "",
                          drafter: str = "", reviewer: str = "", approver: str = "",
                          doc_number: str = "", date: str = "",
                          address: str = "", phone: str = "", fax: str = "",
                          website: str = "", classification: str = "공개"):
    """Build the standard government document footer (결문)."""
    colors = preset.get("colors", {})
    body_size = preset.get("body", {}).get("font_size", 12)

    builder.add_paragraph("")

    # 발신 명의
    if sender:
        builder.add_paragraph(sender, bold=True, font_size=body_size,
                              alignment="CENTER")
    builder.add_paragraph("")

    # 기안/검토/결재
    if drafter or reviewer or approver:
        row = []
        if drafter:
            row.append(f"기안자: {drafter}")
        if reviewer:
            row.append(f"검토자: {reviewer}")
        if approver:
            row.append(f"결재자: {approver}")
        builder.add_paragraph("  ".join(row), font_size=9,
                              text_color=colors.get("meta", "#333333"))

    # 시행
    if doc_number:
        builder.add_paragraph(f"시행: {doc_number} ({date})",
                              font_size=9, text_color=colors.get("meta", "#333333"))
        builder.add_paragraph("접수:", font_size=9,
                              text_color=colors.get("meta", "#333333"))

    # 주소/연락처
    if address:
        builder.add_paragraph("")
        parts = [address]
        if website:
            parts.append(f"홈페이지: {website}")
        builder.add_paragraph("  ".join(parts), font_size=8,
                              text_color=colors.get("meta", "#333333"))
        if phone:
            contact = f"전화: {phone}"
            if fax:
                contact += f"  전송: {fax}"
            builder.add_paragraph(contact, font_size=8,
                                  text_color=colors.get("meta", "#333333"))

    # 공개 구분
    if classification:
        builder.add_paragraph(f"/{classification}/", font_size=9,
                              text_color=colors.get("meta", "#333333"),
                              alignment="CENTER")
