# Editing HWPX Documents

기존 HWPX 문서를 편집하는 완전한 가이드.
pptx 스킬의 editing.md와 동일한 수준의 상세함으로 작성.

> **⚠️ 시작하기 전 — 메타 인지 단계 (생략 금지)**
>
> 어떤 편집 작업이든 시작 전에 **모든 페이지를 PNG로 렌더링하여 시각 확인**한다.
> XML 구조만 보고 작업하면 "왜 이 문서가 이렇게 만들어졌는지" 모르고 엉뚱한 결과를 낸다.
>
> 다음 5질문에 답하고 사용자에게 분석 결과를 확인 받은 뒤 진행:
>
> 1. **이 문서는 무엇인가?** — 양식·보고서·공문·계약·증빙·교재…
> 2. **누가 작성·수신하는가?** — 실무자→회계 / 발신기관→수신기관 / 강사→수강생…
> 3. **페이지 표준이 있는가?** — 지급조서/검수확인서는 "1건 1매". 공문은 "1페이지 원칙". 보고서는 자유.
> 4. **보존할 부분 vs 변경할 부분?** — (예시) 페이지·서명란·기관명·도장·미리 인쇄된 사업명은 보존. 빈 칸·placeholder만 변경.
> 5. **결과물의 사용처?** — 제출용·저장용·인쇄용·전자결재용
>
> 메타 인지를 건너뛰면: (예시) 페이지를 결과물에 남기거나, 1매 표준 양식을 2페이지로 만들거나, 보존해야 할 항목을 덮어쓰는 실수가 발생한다.
> SKILL.md 워크플로우 [2]/[3] Step 0 참조.

## Table of Contents

1. [Template-Based Workflow](#template-based-workflow)
2. [XML 편집 규칙](#xml-편집-규칙)
3. [흔한 실수](#흔한-실수)
4. [양식 채우기 패턴](#양식-채우기-패턴)
5. [고급 편집](#고급-편집)

---

## Template-Based Workflow

기존 HWPX를 템플릿으로 사용할 때:

### 1. 분석

```bash
# 텍스트 추출 — 어떤 내용이 있는지 확인
python3 -c "from pyhwpxlib.api import extract_text; print(extract_text('template.hwpx'))"

# 구조 확인
pyhwpxlib unpack template.hwpx -o unpacked/
ls unpacked/Contents/  # section0.xml, section1.xml, ...
```

section 파일이 여러 개면 다중 섹션 문서. 각 섹션의 내용을 파악한다.

### 2. 편집 계획

⚠️ **구조 변경 → 내용 변경 순서**로 진행. 순서를 바꾸면 작업이 꼬인다.

- 불필요한 섹션 제거 (section1.xml 삭제 + content.hpf 매니페스트 업데이트)
- 단락 추가/삭제 위치 결정
- 표 삽입 위치 결정
- 그 다음에 텍스트 교체

### 3. Unpack

```bash
pyhwpxlib unpack template.hwpx -o unpacked/
```

### 4. 구조 변경 (먼저)

```python
# 섹션 제거 예시
import os
os.remove('unpacked/Contents/section1.xml')

# content.hpf 매니페스트에서도 제거 (필수!)
with open('unpacked/Contents/content.hpf', 'r') as f:
    hpf = f.read()
hpf = hpf.replace('<opf:item id="section1" href="Contents/section1.xml" media-type="application/xml"/>', '')
hpf = hpf.replace('<opf:itemref idref="section1" linear="yes"/>', '')
with open('unpacked/Contents/content.hpf', 'w') as f:
    f.write(hpf)
```

### 5. 내용 편집

```python
# 원본 문자열 직접 교체 — 유일하게 안전한 방법
with open('unpacked/Contents/section0.xml', 'r') as f:
    xml = f.read()
xml = xml.replace('>원래 텍스트<', '>새 텍스트<', 1)
with open('unpacked/Contents/section0.xml', 'w') as f:
    f.write(xml)
```

### 6. Pack + Validate

```bash
pyhwpxlib pack unpacked/ -o output.hwpx
pyhwpxlib validate output.hwpx
```

### 7. Whale에서 확인

```bash
open output.hwpx
```

---

## XML 편집 규칙

### 절대 금지

| 금지 사항 | 이유 | 대안 |
|----------|------|------|
| `ET.tostring()` 재직렬화 | 네임스페이스 프리픽스 변경 → Whale 에러 | 원본 문자열 `.replace()` |
| `<hp:t>` 안에 `\n` | Whale 렌더링 에러 | 별도 `<hp:p>` 요소로 분리 |
| condense 속성 변경 | JUSTIFY 정렬 글자 벌어짐 | 건드리지 않기 |
| styleIDRef 변경 | 들여쓰기/정렬 깨짐 | 건드리지 않기 |
| 섹션 삭제 후 매니페스트 미수정 | 뷰어 오류 | content.hpf 동시 수정 |

### 안전한 교체 패턴

```python
# 패턴 1: 텍스트 교체 (첫 번째만)
xml = xml.replace('>성 명<', '>성 명  홍길동<', 1)

# 패턴 2: 체크박스 □ → ■
xml = xml.replace('□ 고용보험', '■ 고용보험', 1)

# 패턴 3: 빈 칸 채우기 (다중 run 필드)
blank_pos = xml.find('>   <', search_start)
xml = xml[:blank_pos+1] + '09' + xml[blank_pos+4:]

# 패턴 4: lineBreak 포함 필드
xml = xml.replace(
    '>사업체명 :                   (전화 :                )<hp:lineBreak/>주    소 :<',
    '>사업체명 : (주)한빛테크       (전화 : 02-555-1234   )<hp:lineBreak/>주    소 : 서울시 강남구<',
    1)
```

### 단락 경계 탐지

XML에서 특정 단락을 찾으려면:

```python
import re

# 텍스트로 단락 위치 찾기
target = '10. 기  타'
idx = xml.find(target)
p_start = xml.rfind('<hp:p ', 0, idx)   # 단락 시작
p_end = xml.find('</hp:p>', idx) + len('</hp:p>')  # 단락 끝

# 단락 삭제
xml = xml[:p_start] + xml[p_end:]

# 단락 삽입 — 기존 단락의 스타일 ID 복사
ref_para = xml[ref_start:ref_end]
para_pr = re.search(r'paraPrIDRef="(\d+)"', ref_para).group(1)
char_pr = re.search(r'charPrIDRef="(\d+)"', ref_para).group(1)

new_para = f'<hp:p id="0" paraPrIDRef="{para_pr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="{char_pr}"><hp:t>새 텍스트</hp:t></hp:run></hp:p>'
```

---

## 흔한 실수

### 1. ET.tostring 사용 / lxml 직렬화

**가장 흔한 실수.** Python의 `xml.etree.ElementTree` 또는 `lxml.etree`로 파싱 후 `tostring()`으로 재직렬화하면 다음 차이가 발생해 한컴/Whale 호환성이 깨진다:

- 네임스페이스 prefix 변경 (`hp:` → `ns0:` 등)
- attribute 순서 변경 (한컴 스펙은 일부 순서 의존)
- self-closing 형식 변환 (`<hp:t/>` ↔ `<hp:t></hp:t>`)
- 빈 element 자동 제거

```python
# ❌ WRONG — ET.ElementTree
root = ET.fromstring(xml)
new_xml = ET.tostring(root, encoding='unicode')  # 네임스페이스 깨짐!

# ❌ WRONG — lxml도 동일 위험
from lxml import etree
root = etree.fromstring(xml)
new_xml = etree.tostring(root, encoding='utf-8')  # validate ✅ 통과해도 한컴이 거부할 수 있음

# ✅ CORRECT — 정규식 + 문자열 직접 교체
xml = xml.replace('>원래<', '>새거<', 1)

# ✅ CORRECT — 복잡한 구조는 depth-aware 정규식
def find_balanced(text, open_tag, close_tag):
    """nested tag 안전 매칭"""
    # 검수확인서 셀 안 이미지 삽입 사례 참조 → references/form_automation.md
```

**실증 사례**: lxml 직렬화로 만든 검수확인서 hwpx가 validate ✅ 통과했지만 한컴에서 깨져 보임. 동일 작업을 정규식만으로 다시 작성하니 정상.

### 1.5. 한컴 보안 경고 ("문서 보안 설정을 낮춤") — linesegarray strip

**증상**: AI/스크립트로 수정한 hwpx를 한컴에서 열면 *"이 문서를 불러오려면 [문서 보안 설정]을 [낮음]으로 설정해야 합니다"* 경고.

**원인**: section*.xml의 `<hp:linesegarray>` 안 stored geometry(textpos/vertpos/vertsize 등)가 텍스트 길이/줄과 어긋나면 한컴이 "외부 수정"으로 판단. 한컴 본체는 lineseg를 자체 reflow하므로 stored 값은 사실상 캐시인데, 그 캐시가 부정확하면 마커처럼 잡힘.

**해결**: `<hp:linesegarray>...</hp:linesegarray>` 블록을 통째로 제거 → 한컴/rhwp 모두 로드 시 자체 reflow → 손실 없음.

```python
# ✅ 자동 — pyhwpxlib v0.13+ 이상은 write_zip_archive가 default로 strip
from pyhwpxlib.package_ops import write_zip_archive
write_zip_archive(out_path, archive)  # strip_linesegs=True (default)

# ✅ 수동 — 외부 hwpx 정리
# CLI:  pyhwpxlib reflow-linesegs <file>
# API:
from pyhwpxlib.postprocess import strip_linesegarrays
new_xml, n = strip_linesegarrays(section_xml, mode='remove')

# ❌ 주의 — N개 lineseg로 분할(reflow)은 회피 실패. strip만이 안전.
#   (분할값도 한컴 기준 부정확하면 동일 트리거 발동)
```

**검증**: `pyhwpxlib lint <file>` → `STALE_LINESEG_R3 warning` 표시되면 strip 필요.

### 2. replace 횟수 미지정

```python
# ❌ 위험 — 같은 텍스트가 여러 페이지에 있으면 전부 교체
xml = xml.replace('>성 명<', '>성 명  홍길동<')

# ✅ 안전 — 첫 번째만 교체
xml = xml.replace('>성 명<', '>성 명  홍길동<', 1)
```

### 3. 줄바꿈 문자 삽입

```python
# ❌ Whale 에러
'<hp:t>첫줄\n둘째줄</hp:t>'

# ✅ 별도 단락으로 분리
'<hp:p><hp:run><hp:t>첫줄</hp:t></hp:run></hp:p>'
'<hp:p><hp:run><hp:t>둘째줄</hp:t></hp:run></hp:p>'
```

### 4. 섹션 삭제 후 매니페스트 미수정

section1.xml을 삭제했는데 content.hpf에 참조가 남아있으면 뷰어 오류.
**반드시 content.hpf에서 `<opf:item>`과 `<opf:itemref>` 모두 제거.**

### 5. 표 삽입 시 borderFillIDRef 불일치

기존 문서에 표를 삽입할 때, header.xml에 정의된 borderFill ID를 사용해야 한다.
보통 `borderFillIDRef="2"`가 테두리 있는 스타일.

---

## 양식 채우기 패턴

### 단순 텍스트 교체

```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox(
    "template.hwpx",
    data={
        ">성 명<": ">성 명  홍길동<",
        ">사업체명<": ">사업체명  (주)블루오션<",
    },
    checks=["민간기업"],
    output_path="filled.hwpx",
)
```

### 체크박스 2가지 형태

```python
# [  ] → [√] 패턴 — data로 직접 교체
data = {"민간기업 [  ]": "민간기업 [√]"}

# □ → ■ 패턴 — checks 파라미터 사용
checks = ["민간기업"]    # 해당 라벨 뒤 □만 ■로
checks = ["__ALL__"]    # 전체 □ → ■
```

### 다중 run 필드

HWP→HWPX 변환 문서는 하나의 입력 필드가 여러 `<hp:run>`으로 분리됨.
빈 칸은 `>   <` (공백 3개) 패턴.

```python
# 특정 위치 이후의 빈칸을 순서대로 채우기
search_start = xml.find('소정근로시간')
for value in ['09', '00', '18', '00']:
    blank_pos = xml.find('>   <', search_start)
    if blank_pos >= 0:
        xml = xml[:blank_pos+1] + value + xml[blank_pos+4:]
        search_start = blank_pos + 10
```

### 배치 생성

```python
from pyhwpxlib.api import fill_template_batch

records = [
    {"data": {">성 명<": ">성 명  홍길동<"}, "checks": ["민간기업"], "filename": "홍길동"},
    {"data": {">성 명<": ">성 명  김영수<"}, "checks": ["공공기관"], "filename": "김영수"},
]
fill_template_batch("template.hwpx", records, output_dir="output/")
```

---

## 고급 편집

### 기존 문서에 표 삽입

```python
# 기존 단락의 charPrIDRef 재사용
char_pr = '0'

col1_w, col2_w = 14173, 28347
row_h = 1200
rows = [("구분", "내용"), ("항목1", "값1")]

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

# 삽입 위치 찾기
target = '삽입할 위치 앞 텍스트'
target_idx = xml.find(target)
p_start = xml.rfind('<hp:p ', 0, target_idx)
xml = xml[:p_start] + table_xml + xml[p_start:]
```

### 섹션 추출

다중 섹션 문서에서 특정 섹션만 추출:

```python
import re

# 1. secPr 보존하며 자르기
secpr_end = xml.find('</hp:secPr>') + len('</hp:secPr>')

# 2. 경계 텍스트로 자를 위치 찾기
cut_text = '두 번째 계약서 제목'
idx = xml.find(cut_text)
p_start = xml.rfind('<hp:p ', 0, idx)

# 3. 첫 번째 부분만 남기기
new_xml = xml[:secpr_end] + xml[secpr_end:p_start] + '</hs:sec>'
```

### pageBreak 삽입

```python
# 특정 단락에 pageBreak 속성 추가
xml = xml.replace(
    '<hp:p id="0" paraPrIDRef="6" styleIDRef="0" pageBreak="0"',
    '<hp:p id="0" paraPrIDRef="6" styleIDRef="0" pageBreak="1"',
    1)
```
