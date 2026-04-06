# pyhwpxlib API Reference

`from pyhwpxlib.api import <function_name>` 으로 사용.

## 문서 생성/저장

### create_document() → HWPXFile
빈 HWPX 문서를 생성한다.

### save(hwpx_file, filepath)
HWPX 문서를 .hwpx 파일로 저장한다.

### open_document(filepath) → HWPXFile
기존 HWPX 파일을 열어 HWPXFile 객체로 반환한다.

## 텍스트

### add_paragraph(doc, text, font_size=None, bold=False, italic=False, font_name=None, align=None, section_index=0)
텍스트 문단을 추가한다. font_size는 HWPX 단위 (1600 = 약 11pt).

### add_styled_paragraph(doc, text, font_size=None, bold=False, italic=False, underline=False, color=None, bg_color=None, font_name=None, align=None, line_spacing=None, char_spacing=None, section_index=0)
스타일을 세밀하게 지정한 문단을 추가한다. color는 "#RRGGBB" 형식.

### add_heading(doc, text, level=1, section_index=0)
제목 문단 추가. level: 1~6.

### add_bullet_list(doc, items, section_index=0)
글머리 기호 목록 추가. items는 문자열 리스트.

### add_numbered_list(doc, items, section_index=0)
번호 목록 추가.

### add_nested_bullet_list(doc, items, section_index=0)
중첩 글머리 기호 목록. items는 (level, text) 튜플 리스트.

### add_nested_numbered_list(doc, items, section_index=0)
중첩 번호 목록.

### add_code_block(doc, code, language=None, section_index=0)
코드 블록 추가 (모노스페이스 폰트, 배경색 적용).

### add_highlight(doc, text, color=None, section_index=0)
형광펜 표시된 텍스트 추가.

## 표

### add_table(doc, rows, cols, data=None, width=42520, merge_info=None, cell_colors=None, col_widths=None, row_heights=None, cell_margin=None, cell_gradients=None, section_index=0)
표를 삽입한다.
- **data**: 2D 리스트 `[["셀1", "셀2"], ...]`
- **width**: 표 전체 너비 (기본 42520 = A4 본문영역)
- **col_widths**: 컬럼별 너비 리스트 (합 = width)
- **row_heights**: 행별 높이 리스트
- **merge_info**: 병합 정보 리스트 `[(시작행, 시작열, 끝행, 끝열), ...]`
- **cell_colors**: 셀 배경색 딕셔너리 `{(행, 열): "#RRGGBB"}`
- **cell_margin**: 셀 안쪽 여백 (left, right, top, bottom)

### set_cell_gradient(doc, table_para_index, row, col, start_color, end_color, gradient_type="LINEAR", angle=0, section_index=0)
기존 표의 특정 셀에 그라데이션 채우기를 적용한다.

## 이미지/도형

### add_image(doc, image_path, width=None, height=None, section_index=0)
인라인 이미지 삽입. width/height는 HWPX 단위.

### add_rectangle(doc, width, height, x=0, y=0, ...)
사각형 도형 추가.

### add_ellipse(doc, width, height, x=0, y=0, ...)
타원 도형 추가.

### add_line(doc, x1, y1, x2, y2, ...)
직선 추가.

### add_arc(doc, width, height, ...)
호(arc) 추가.

### add_polygon(doc, points, ...)
다각형 추가. points는 [(x, y), ...] 리스트.

### add_curve(doc, points, ...)
베지어 곡선 추가.

### add_connect_line(doc, x1, y1, x2, y2, ...)
연결선 추가.

### add_textart(doc, text, width, height, ...)
글맵시(TextArt) 추가.

### add_container(doc, children, ...)
여러 도형을 그룹으로 묶는 컨테이너.

### add_rectangle_with_image_fill(doc, image_path, width, height, ...)
이미지를 배경으로 채운 사각형.

## 양식 컨트롤

### add_checkbox(doc, checked=False, section_index=0)
체크박스 양식 컨트롤 추가.

### add_radio_button(doc, group_name="", section_index=0)
라디오 버튼 추가.

### add_button(doc, text="Button", section_index=0)
푸시 버튼 추가.

### add_combobox(doc, items=None, section_index=0)
콤보박스 추가.

### add_listbox(doc, items=None, section_index=0)
리스트박스 추가.

### add_edit_field(doc, text="", section_index=0)
텍스트 입력 필드 추가.

### add_scrollbar(doc, min_val=0, max_val=100, section_index=0)
스크롤바 추가.

## 페이지 설정

### set_page_setup(doc, width=59528, height=84188, landscape=False, margin_left=8504, margin_right=8504, margin_top=5668, margin_bottom=4252, header=4252, footer=4252, gutter=0, section_index=0)
용지 크기, 방향, 여백을 설정한다.
- 기본값: A4 세로, 표준 여백
- **정부 서식 표준**: margin_left=5104, margin_right=5104, margin_top=4252, margin_bottom=4252, header=2836, footer=2836

### set_columns(doc, col_count=2, same_gap=1200, separator_type="SOLID", ...)
다단 레이아웃 설정.

## 머리글/바닥글

### add_header(doc, text, section_index=0)
머리글 추가.

### add_footer(doc, text, section_index=0)
바닥글 추가.

### add_page_number(doc, section_index=0)
페이지 번호 추가.

## 주석/기타

### add_footnote(doc, text, note_text, section_index=0)
각주 추가.

### add_bookmark(doc, name, text, section_index=0)
북마크 추가.

### add_dutmal(doc, base_text, ruby_text, section_index=0)
루비 텍스트(덧말) 추가.

### add_hidden_comment(doc, text, comment_text, section_index=0)
숨은 주석 추가.

### add_indexmark(doc, text, keyword, section_index=0)
색인 표지 추가.

### add_tab(doc, text_before="", text_after="", tab_type="RIGHT", leader="NONE", position=None, section_index=0)
탭 문자 추가.

### add_special_char(doc, char_code, section_index=0)
특수문자 추가.

### add_hyperlink(doc, text, url, section_index=0)
하이퍼링크 추가.

### add_equation(doc, equation_text, section_index=0)
수식 추가.

## 변환

### convert_md_to_hwpx(doc, md_content, style="github") → int
Markdown 문자열을 HWPX 요소로 변환하여 문서에 추가.

### convert_md_file_to_hwpx(md_path, hwpx_path, style="github")
Markdown 파일을 HWPX 파일로 변환.

### convert_html_to_hwpx(doc, html_content) → int
HTML 문자열을 HWPX 요소로 변환하여 문서에 추가.

### convert_html_file_to_hwpx(html_path, hwpx_path)
HTML 파일을 HWPX 파일로 변환.

### convert_hwpx_to_html(filepath, ...) → str
HWPX 파일을 standalone HTML로 변환.

### extract_text(filepath, separator="\n") → str
HWPX 파일에서 텍스트만 추출.

### extract_markdown(filepath) → str
HWPX 파일 내용을 Markdown으로 추출.

### extract_html(filepath) → str
HWPX 파일 내용을 HTML로 추출.

### merge_documents(hwpx_paths, output_path)
여러 HWPX 파일을 하나로 병합.

## 양식 템플릿

### fill_template(doc, data)
템플릿 HWPX에서 플레이스홀더 텍스트를 데이터로 교체한다.

### fill_template_checkbox(doc, data)
템플릿에 데이터와 체크박스 마크를 채운다.

### fill_template_batch(template_path, data_list, output_dir)
하나의 템플릿으로 여러 건의 문서를 일괄 생성한다.

### extract_schema(filepath) → dict
HWPX/OWPML 템플릿에서 채울 수 있는 필드 스키마를 추출한다.

### analyze_schema_with_llm(schema) → dict
LLM을 사용하여 서식 필드를 자동 분류한다.
