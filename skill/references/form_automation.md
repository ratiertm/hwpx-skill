# Form Automation Reference

> **⚠️ 시작하기 전 — 메타 인지 단계 (생략 금지)**
>
> 양식 자동화는 페이지 표준이 강한 작업. **모든 페이지를 PNG로 렌더링하여 시각 확인** 후 다음 5질문에 답하고 사용자 의도 확인:
>
> 1. **이 양식은 무엇인가?** — 지급조서·검수확인서·신청서·동의서·증빙·계약서…
> 2. **누가 채우고 누가 받는가?** — 실무자→회계 / 신청자→기관 / 계약 양당사자…
> 3. **페이지 표준이 있는가?** — 지급조서/검수확인서는 **"1건 1매" 강제 표준**
> 4. **(예시) 페이지가 있나?** — 작성 가이드용. **결과물에서는 보통 제거** (그대로 두면 회계팀이 가이드까지 제출본으로 오해)
> 5. **미리 인쇄된 항목?** — 사업명·기관명·발신명의·도장 자리는 보존, 빈 칸만 채움
>
> 메타 인지를 건너뛴 결과 사례:
> - "(예시)" 가이드 페이지가 결과물에 남아 1매 양식이 2매가 됨
> - 1매 표준을 무시하고 폰트만 줄이려다 끝없이 페이지 늘어남
> - 미리 인쇄된 사업명을 변경하여 양식 무효화
>
> SKILL.md 워크플로우 [3] Step 0 참조.

## Table of Contents

1. [Fill Template (텍스트 교체 방식)](#fill-template)
2. [Batch Generate (다건 생성)](#batch-generate)
3. [Schema Extraction (필드 자동 탐지)](#schema-extraction)
4. [Template Builder UI](#template-builder-ui)
5. [Checkbox Patterns](#checkbox-patterns)
6. [Critical Rules for Form Automation](#critical-rules-for-form-automation)

---

## Fill Template

텍스트 교체 방식 — 서식 100% 보존

```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox(
    "template.hwpx",
    data={
        ">성 명<": ">성 명  홍길동<",
        ">사업체명<": ">사업체명  (주)블루오션<",
    },
    checks=["민간기업"],    # [  ] → [√] 또는 □ → ■
    output_path="filled.hwpx",
)
```

---

## Batch Generate

다건 생성

```python
from pyhwpxlib.api import fill_template_batch

records = [
    {"data": {">성 명<": ">성 명  홍길동<"}, "checks": ["민간기업"], "filename": "홍길동"},
    {"data": {">성 명<": ">성 명  김영수<"}, "checks": ["공공기관(공기업)"], "filename": "김영수"},
]
fill_template_batch("template.hwpx", records, output_dir="output/")
```

---

## Schema Extraction

필드 자동 탐지

```python
from pyhwpxlib.api import extract_schema, analyze_schema_with_llm

schema = extract_schema("template.hwpx")
analyzed = analyze_schema_with_llm(schema)
# analyzed['input_fields'] — 사용자 입력 필드
# analyzed['fixed_fields'] — 고정 텍스트
# analyzed['checkboxes'] — 체크박스
```

---

## Template Builder UI

```bash
python template_builder.py template.hwpx --port 8081
# 브라우저에서 필드 입력/고정/제목 토글 → schema.json 저장
```

---

## Checkbox Patterns

**주의: 체크박스에 2가지 형태가 있음**
- `[  ]` 패턴 — data로 직접 교체 (checks 파라미터 미지원)
- `□` 패턴 — checks 파라미터 사용

```python
# [  ] → [√] 패턴 — data로 직접 교체해야 함
data = {"공공기관(공기업) [  ]": "공공기관(공기업) [√]"}

# □ → ■ 패턴 — checks 파라미터 사용
checks = ["__ALL__"]  # 전체 □ → ■
checks = ["민간기업"]  # 해당 라벨 뒤 □만 ■로

# 혼합 사용 예시
fill_template_checkbox(
    "template.hwpx",
    data={
        ">성 명<": ">성 명  홍길동<",
        "민간기업 [  ]": "민간기업 [√]",      # [  ] → [√]
    },
    checks=["동의함"],                         # □ → ■
    output_path="filled.hwpx",
)
```

---

## Advanced XML Editing (고급 XML 편집)

### Section Management (섹션 추출/제거)

다중 섹션 문서(section0.xml + section1.xml + ...)에서 특정 섹션만 남기거나 제거할 때:

```python
import zipfile, re

# 1. 어떤 섹션이 있는지 확인
with zipfile.ZipFile('document.hwpx') as z:
    sections = [n for n in z.namelist() if re.match(r'Contents/section\d+\.xml', n)]
    print(sections)  # ['Contents/section0.xml', 'Contents/section1.xml']

# 2. 불필요한 섹션 파일 삭제
import os
os.remove('unpacked/Contents/section1.xml')

# 3. content.hpf 매니페스트에서 참조 제거 (필수!)
with open('unpacked/Contents/content.hpf', 'r') as f:
    hpf = f.read()
hpf = hpf.replace('<opf:item id="section1" href="Contents/section1.xml" media-type="application/xml"/>', '')
hpf = hpf.replace('<opf:itemref idref="section1" linear="yes"/>', '')
with open('unpacked/Contents/content.hpf', 'w') as f:
    f.write(hpf)
```

섹션 내에서 특정 범위만 추출할 때 (예: 첫 번째 계약서만):

```python
# 1. 텍스트 노드로 경계 탐지
texts = re.findall(r'<hp:t>(.*?)</hp:t>', xml)

# 2. 경계 텍스트의 XML 위치 찾기
cut_text = '두 번째 계약서 제목'
idx = xml.find(cut_text)
p_start = xml.rfind('<hp:p ', 0, idx)  # 해당 텍스트의 단락 시작

# 3. secPr 보존하며 자르기
secpr_end = xml.find('</hp:secPr>') + len('</hp:secPr>')
new_xml = xml[:secpr_end] + xml[secpr_end:p_start] + '</hs:sec>'
```

### Paragraph Manipulation (단락 삽입/삭제)

```python
# 단락 삭제 — 텍스트로 단락 경계 찾기
target = '10. 기  타'
idx = xml.find(target)
p_start = xml.rfind('<hp:p ', 0, idx)
p_end = xml.find('</hp:p>', idx) + len('</hp:p>')
xml = xml[:p_start] + xml[p_end:]  # 단락 제거

# 단락 삽입 — 기존 단락의 스타일 복사
ref_text = '9. 근로계약서 교부'
ref_idx = xml.find(ref_text)
ref_start = xml.rfind('<hp:p ', 0, ref_idx)
ref_end = xml.find('</hp:p>', ref_idx) + len('</hp:p>')
ref_para = xml[ref_start:ref_end]

# 스타일 ID 추출
para_pr = re.search(r'paraPrIDRef="(\d+)"', ref_para).group(1)
char_pr = re.search(r'charPrIDRef="(\d+)"', ref_para).group(1)

# 새 단락 생성 (기존 스타일 재사용)
new_para = f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{char_pr}"><hp:t>새 텍스트</hp:t></hp:run></hp:p>'

# 삽입 위치 (날짜 줄 앞)
insert_before = '년      월      일'
insert_idx = xml.find(insert_before)
insert_p = xml.rfind('<hp:p ', 0, insert_idx)
xml = xml[:insert_p] + new_para + xml[insert_p:]
```

### Multi-run Field Filling (다중 run 필드 채우기)

HWP 변환 문서는 하나의 입력 필드가 여러 `<hp:run>`으로 분리되어 있음.
빈 칸은 `>   <` (공백 3개) 패턴으로 나타남.

```python
# 패턴: >   <hp:t>시</hp:t>...<hp:t>   </hp:t>...<hp:t>분</hp:t>
# 의미: [빈칸]시 [빈칸]분

# 특정 위치 이후의 빈칸을 순서대로 채우기
search_start = xml.find('소정근로시간')
for value in ['09', '00', '18', '00']:
    blank_pos = xml.find('>   <', search_start)
    if blank_pos >= 0:
        xml = xml[:blank_pos+1] + value + xml[blank_pos+4:]
        search_start = blank_pos + 10

# lineBreak 포함 필드 (서명란 등)
# <hp:t>텍스트<hp:lineBreak/>다음줄</hp:t>
xml = xml.replace(
    '>(사업주) 사업체명 :                   (전화 :                )'
    '<hp:lineBreak/>주    소 :<',
    '>(사업주) 사업체명 : (주)한빛테크       (전화 : 02-555-1234   )'
    '<hp:lineBreak/>주    소 : 서울시 강남구<', 1)
```

### Table Insertion (기존 문서에 표 삽입)

unpack한 XML에 새 표를 삽입할 때:

```python
# 기존 단락의 charPrIDRef를 재사용
char_pr = '0'  # 또는 기존 단락에서 추출

# 표 XML 생성
col1_w, col2_w = 14173, 28347
row_h = 1200
rows = [("구분", "내용"), ("기본급", "3,500,000원")]

table_xml = f'<hp:tbl rowCnt="{len(rows)}" colCnt="2" cellSpacing="0" borderFillIDRef="2">'
table_xml += '<hp:inMargin left="141" right="141" top="70" bottom="70"/>'
table_xml += '<hp:outMargin left="0" right="0" top="141" bottom="141"/>'
table_xml += '<hp:cellzonelist><hp:cellzone startRowAddr="0" startColAddr="0" endRowAddr="0" endColAddr="0" borderFillIDRef="2"/></hp:cellzonelist>'

for r, (label, value) in enumerate(rows):
    table_xml += '<hp:tr>'
    for c, (text, w) in enumerate([(label, col1_w), (value, col2_w)]):
        table_xml += (
            f'<hp:tc borderFillIDRef="2">'
            f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/>'
            f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="{w}" height="{row_h}"/>'
            f'<hp:cellMargin left="141" right="141" top="70" bottom="70"/>'
            f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" '
            f'linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            f'<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char_pr}"><hp:t>{text}</hp:t></hp:run></hp:p>'
            f'</hp:subList></hp:tc>'
        )
    table_xml += '</hp:tr>'
table_xml += '</hp:tbl>'

# 삽입 위치 찾기 (특정 단락 앞에 삽입)
target = '7. 연차유급휴가'
target_idx = xml.find(target)
p_start = xml.rfind('<hp:p ', 0, target_idx)
xml = xml[:p_start] + table_xml + xml[p_start:]
```

---

## Critical Rules for Form Automation

- **원본 ZIP 복사 + XML 텍스트 교체** — pyhwpxlib 재생성 금지 (header 깨짐)
- **`.replace(old, new, 1)`** — 첫 번째만 교체 (다른 페이지 보호)
- **condense/styleIDRef/breakSetting** — 원본 paraPr을 건드리면 JUSTIFY 글자 벌어짐
- **ET.tostring 금지** — 반드시 원본 문자열 직접 교체
- **섹션 제거 �� content.hpf 매니페스트도 반드시 업데이트** — 누락 시 뷰어 오류
- **다중 run 필드** — `>   <` 빈칸 패턴으로 위치 특정 후 교체
- **표 삽입** — borderFillIDRef는 기존 문서의 ID 재사용 (보통 "2"가 테두리 있는 스타일)
