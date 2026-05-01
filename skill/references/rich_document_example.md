# Rich Mode 골든 샘플 — 보고서/제안서

새 문서 만들 때 사용자가 "최대한 기능 활용" / "풍부하게" / 보고서·제안서를 요청하면
이 패턴을 참고. 한 문서에 builder 15개 add_* 중 14개를 자연스럽게 결합한 예시.

> 출처: `Test/output/lotte_ai/build.py` (warm_executive 테마, 3페이지)

## 페이지 구성 패턴

| 페이지 | 역할 | 주요 add_* |
|--------|------|-----------|
| 1 | 표지 + Executive Summary + 진단 | heading×2, paragraph, highlight, bullet_list, table |
| 2 | 핵심 주제 전개 + 수식 + 인포그래픽 | heading, table, equation, image, paragraph |
| 3 | 로드맵 + KPI + 마일스톤 + 리스크 + 결론 | heading, table×2, numbered_list, nested_bullet_list, highlight |
| 결문 | 머리말/꼬리말/페이지번호 | header, footer, page_number (deferred) |

## 활용된 메서드 14/15

```
✅ add_heading        ✅ add_paragraph     ✅ add_table
✅ add_image          ✅ add_bullet_list   ✅ add_numbered_list
✅ add_nested_bullet_list                  ✅ add_equation
✅ add_highlight      ✅ add_page_break    ✅ add_header
✅ add_footer         ✅ add_page_number
✅ (image with PIL ratio calc)

⏸️ add_line / add_rectangle / add_draw_line — 인포그래픽이 이미지로 들어가
   도형이 자연스럽지 않은 케이스. 도형이 본문 흐름을 끊지 않을 때만 사용.
⏸️ add_image_from_url — 로컬 PIL 이미지가 더 신뢰성 있음. URL 첨부 자료
   참조가 필요한 경우만.
⏸️ add_footnote / add_nested_numbered_list — 본 샘플은 미사용 (다른 문서
   유형: 학술 보고서·법률 의견서에서 자주 등장).
```

## 핵심 패턴 5가지

### 1. 헤딩 두 단계 위계 (level=1 / level=2)

```python
b.add_heading("롯데홈쇼핑 AI 도입 전략 제안서", level=1)
...
b.add_heading("Executive Summary", level=2)
b.add_heading("시장·내부 진단 (Snapshot)", level=2)
```
level=1 은 페이지·장 단위, level=2 는 섹션 단위. 3단계 이상은 본문 가독성 떨어짐.

### 2. highlight = 핵심 메시지 박스

```python
b.add_highlight("핵심 메시지: 추천·응대·콘텐츠·이상감지·물류 5대 영역 동시 추진",
                color="#FFEFE9")
```
페이지당 1~2번. 테마 primary 의 옅은 톤 (warm_executive #B85042 → #FFEFE9).

### 3. 표 헤더는 테마 색상

```python
b.add_table([
    ["구분", "외부 환경 (시장)", "내부 환경 (자사)"],
    ...
], header_bg="#B85042")
```
테마 primary 를 그대로 사용. 헤더 배경은 본문과 구별되어야 표가 산다.

### 4. 이미지 비율 유지 + 앞뒤 빈 줄

```python
img = Image.open(IMG_PATH)
iw, ih = img.size
img_width = 42520                            # A4 전체 너비
img_height = int(img_width * ih / iw)
b.add_paragraph("")                          # 앞 빈 줄
b.add_image(str(IMG_PATH), width=img_width, height=img_height)
b.add_paragraph("[그림 1] 캡션", italic=True)
b.add_paragraph("")                          # 뒤 빈 줄
```

### 5. 수식은 소제목 직후

```python
b.add_heading("투자 회수율(ROI) 산출식", level=2)
b.add_equation(
    "ROI = {{ Σ(매출 증가 + 비용 절감) - 총 투자비 } over { 총 투자비 }} × 100"
)
b.add_paragraph("사내 기준 ROI 임계치는 120%, 핵심 임계치는 200%.")
```
수식만 단독으로 두지 말 것. 위에 무슨 수식인지 헤딩 + 아래에 의미 해설.

### 6. 결문 (deferred — 마지막에 호출)

```python
b.add_header("롯데홈쇼핑 AI 도입 전략 제안서  |  대외비")
b.add_footer("롯데홈쇼핑 ⓒ 2026  ·  작성: 전략기획팀")
b.add_page_number(pos="BOTTOM_CENTER")
b.save(str(HWPX))                            # 여기서 deferred 처리
```
header/footer/page_number 는 **save 직전에** 호출. Whale SecPr 순서 버그 회피.

## 안티패턴 (피할 것)

| 안티패턴 | 결과 | 대안 |
|----------|------|------|
| 모든 섹션이 동일한 (heading + table) 반복 | "AI 슬롭" 패턴 — 단조롭다 | 섹션별 레이아웃 다양화 (highlight·bullet·image) |
| 본문이 짧은데 표 강제 | 가독성↓ | paragraph 만 사용, 표는 비교·매트릭스에 한정 |
| highlight 페이지마다 3+ 개 | 강조 효과 없어짐 | 페이지당 1~2개로 제한 |
| 도형 (rectangle/draw_line) 본문 사이 삽입 | 흐름 끊김 | 표지·구분 페이지에만 |
| 이미지 앞뒤 빈 줄 없음 | 텍스트와 붙음 | 절대 규칙 #6 — `add_paragraph("")` 필수 |

## 전체 코드 보기

`Test/output/lotte_ai/build.py` (167 LOC). 직접 실행:

```bash
python Test/output/lotte_ai/build.py
# saved: Test/output/lotte_ai/lotte_ai_proposal.hwpx
```
