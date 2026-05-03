# Stage 4 설계 보강 — 샌드박스 환경 워크플로

> **배경**: ChatGPT Code Interpreter, Gemini Code Execution 등 샌드박스 환경에서도
> pyhwpxlib의 핵심 기능은 동작한다. 단, 로컬 파일 접근과 세션 간 상태 유지가 없다.
> 이 제약을 전제로 한 워크플로가 필요하다.

---

## 실제 동작 검증 결과

```
pip install pyhwpxlib       → 새 문서, 양식 채우기, 공문 생성, HWP변환: ✅
pip install pyhwpxlib[preview] → rhwp SVG 렌더링: ⚠️ (wasmtime 환경 의존)

불가: 로컬 파일 직접 접근, 세션 간 상태 유지
```

---

## 기능 가용성 매트릭스

| 기능 | Claude Code/Desktop | ChatGPT CI | Gemini |
|------|-------------------|-----------|--------|
| 새 문서 생성 | ✅ | ✅ | ⚠️ |
| 양식 채우기 | ✅ | ✅ 업로드 필요 | ⚠️ |
| 공문(기안문) 생성 | ✅ | ✅ | ⚠️ |
| HWP→HWPX 변환 | ✅ | ✅ 업로드 필요 | ⚠️ |
| 텍스트 추출 | ✅ | ✅ 업로드 필요 | ⚠️ |
| rhwp 프리뷰 | ✅ | ⚠️ [preview] 필요 | ❌ |
| template context | ✅ 자동 | ❌ 수동 붙여넣기 | ❌ 수동 |
| 로컬 파일 접근 | ✅ | ❌ 업로드/다운로드 | ❌ |
| 세션 간 상태 | ✅ 유지 | ❌ 매번 초기화 | ❌ |

**Claude Code/Desktop과의 본질적 차이 2가지**:
1. 파일을 매번 업로드/다운로드해야 한다
2. 매 세션 pip install + 컨텍스트 재주입이 필요하다

---

## 4-F: 샌드박스 환경 워크플로

### 세션 시작 스크립트 (매 세션 첫 셀에서 실행)

```python
# ① 설치 (매번 필요)
!pip install pyhwpxlib --quiet
# 프리뷰 필요 시: !pip install "pyhwpxlib[preview]" --quiet

# ② 확인
import pyhwpxlib
print(f"pyhwpxlib {pyhwpxlib.__version__} 준비됨")
```

> **GPT Builder Knowledge 활용**: `chatgpt_hwpx_guide.md`를 Knowledge에 업로드하면
> ①은 자동으로 안내되고 ②만 실행하면 된다.

---

### 워크플로 A: 새 문서 생성

**Claude Code/Desktop**:
```
컨텍스트 자동 로드 → 코드 실행 → 로컬 파일 저장
```

**ChatGPT Code Interpreter**:
```
세션 시작 스크립트
  ↓
(선택) template context --brief 출력 붙여넣기
  ↓
코드 실행 → HWPX 생성
  ↓
파일 다운로드 → 로컬에서 Whale로 확인
```

코드 패턴:
```python
from pyhwpxlib import HwpxBuilder

doc = HwpxBuilder(theme='charcoal_minimal')
doc.add_heading("제목", level=1)
doc.add_paragraph("본문")
doc.save("/tmp/output.hwpx")

# 다운로드 (ChatGPT Code Interpreter)
from IPython.display import FileLink
FileLink('/tmp/output.hwpx')
```

---

### 워크플로 B: 기존 문서 편집

**Claude Code/Desktop**:
```
로컬 경로 직접 참조 → 편집 → 저장
```

**ChatGPT Code Interpreter**:
```
HWPX 파일 업로드 (ChatGPT 파일 첨부)
  ↓
세션 시작 스크립트
  ↓
업로드 경로 확인 → 편집 → 저장
  ↓
파일 다운로드
```

코드 패턴:
```python
import os
from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

# 업로드된 파일 경로 확인
uploaded = "/tmp/myform.hwpx"  # ChatGPT가 /tmp에 저장

arch = read_zip_archive(uploaded)
xml = arch.files["Contents/section0.xml"].decode("utf-8")

# 텍스트 교체
xml = xml.replace("홍길동", "김철수")
arch.files["Contents/section0.xml"] = xml.encode("utf-8")

output = "/tmp/output.hwpx"
write_zip_archive(output, arch)

from IPython.display import FileLink
FileLink(output)
```

---

### 워크플로 C: 양식 채우기

**Claude Code/Desktop**:
```
template context 자동 로드 → 필드 확인 → 채우기 → 저장
```

**ChatGPT Code Interpreter**:
```
양식 HWPX 파일 업로드
  ↓
세션 시작 스크립트
  ↓
[중요] template context --brief 출력을 첫 메시지에 붙여넣기
  ↓  (로컬에서: pyhwpxlib template context 검수확인서 --brief)
LLM이 필드 구조 파악 → 채우기 코드 실행
  ↓
결과 파일 다운로드
```

코드 패턴:
```python
from pyhwpxlib.api import fill_template_checkbox

# 업로드된 양식 파일
source = "/tmp/검수확인서.hwpx"
output = "/tmp/검수확인서_완성.hwpx"

fill_template_checkbox(
    source,
    data={
        "geomsu_ja": "홍길동",
        "geomsu_il": "2026. 5. 1.",
        "geomsu_hang": "소프트웨어 모듈 A"
    },
    checks=[],
    output_path=output
)

from IPython.display import FileLink
FileLink(output)
```

---

### 워크플로 D: 공문(기안문) 생성

공문은 양식 파일 없이 코드만으로 생성되므로 **업로드 불필요** — 샌드박스에서 가장 쾌적한 워크플로다.

```python
from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer

doc = Gongmun(
    기관명="MindBuild",
    수신="내부결재",
    제목="pyhwpxlib 도입 계획 안내",
    본문=["도입 배경: ...", ("세부 계획", ["1단계: ...", "2단계: ..."])],
    붙임=["도입 계획서 1부."],
    기안자=signer("개발팀장", "김OO"),
    결재권자=signer("대표", "이OO", 전결=True),
    시행일="2026. 5. 1.",
    공개구분="대국민공개",
)
GongmunBuilder(doc).save("/tmp/공문.hwpx")

from IPython.display import FileLink
FileLink('/tmp/공문.hwpx')
```

---

## 4-G: 컨텍스트 주입 — 샌드박스 전용 패턴

샌드박스에서 가장 중요한 것은 **매 세션 LLM에게 양식 컨텍스트를 알려주는 것**이다.

### 방법 1: 첫 메시지에 직접 붙여넣기

```bash
# 로컬 터미널에서 실행
pyhwpxlib template context 검수확인서 --brief | pbcopy  # macOS
```

ChatGPT 첫 메시지:
```
다음 양식 컨텍스트를 기억해줘:

# hwpx 양식: 검수확인서 (B형·1매)
필드: geomsu_ja(검수자), geomsu_il(검수일자), geomsu_hang(검수항목)
주의: 서명란은 이미지 삽입. 구조 B → patch 방식.
최근값: {"geomsu_ja":"홍길동","geomsu_il":"2026. 5. 1."}

그리고 세션 시작 스크립트를 실행해줘:
!pip install pyhwpxlib --quiet
```

### 방법 2: Custom Instructions에 저장 (ChatGPT, 반영구적)

```bash
pyhwpxlib template context 검수확인서 --brief
# 출력을 ChatGPT Custom Instructions에 붙여넣기
# → 이후 모든 세션에서 자동 참조
```

> 1,500자 제한 → `--brief` 필수. 여러 양식 등록 시 중요한 것만 선택.

### 방법 3: GPT Builder Knowledge (가장 강력)

```bash
# 모든 양식 컨텍스트를 파일로 내보내기
pyhwpxlib template list --names | while read name; do
  pyhwpxlib template context "$name" >> hwpx_all_contexts.md
  echo "\n---\n" >> hwpx_all_contexts.md
done

# + chatgpt_hwpx_guide.md 함께 Knowledge에 업로드
```

GPT Builder Knowledge에 올리면:
- 세션 시작마다 자동 참조
- 양식 필드 구조 자동 파악
- 사용자가 컨텍스트를 매번 붙여넣지 않아도 됨

---

## chatgpt_hwpx_guide.md 추가 섹션

### 맨 앞에 추가: "세션 시작 시 항상 먼저 실행"

```markdown
## 필수: 세션 시작 스크립트

이 환경(Code Interpreter)에서는 매 세션 시작 시 아래를 먼저 실행해야 합니다.

**기본 설치** (새 문서 생성, 양식 채우기, 공문 생성):
\`\`\`python
!pip install pyhwpxlib --quiet
import pyhwpxlib
print(f"pyhwpxlib {pyhwpxlib.__version__} 준비됨")
\`\`\`

**프리뷰 포함** (SVG 미리보기 필요 시):
\`\`\`python
!pip install "pyhwpxlib[preview]" --quiet
\`\`\`

> 설치 완료까지 약 10~30초 소요. 이후 모든 기능 사용 가능.
```

### 기존 워크플로 [3] 수정: 파일 업로드 단계 추가

```markdown
### 워크플로 [3] 양식 채우기 (Code Interpreter)

0. 세션 시작 스크립트 실행
1. **양식 HWPX 파일 업로드** (채팅창 파일 첨부)
2. (권장) 양식 컨텍스트 붙여넣기 — 로컬에서 `pyhwpxlib template context <이름> --brief`
3. SVG 프리뷰로 양식 분석
4. 필드 입력값 사용자에게 요청
5. fill_template 실행
6. **결과 파일 다운로드 링크 생성**
7. "다운로드 후 Whale에서 확인해주세요"
```

### 새 섹션: "파일 다운로드"

```markdown
## 파일 다운로드 (Code Interpreter 전용)

HWPX 파일을 생성/편집 후 다운로드:

\`\`\`python
from IPython.display import FileLink
FileLink('/tmp/output.hwpx')
\`\`\`

또는 ChatGPT가 자동으로 다운로드 링크를 제공합니다.
```

---

## Claude Code/Desktop vs 샌드박스 — 사용자 경험 차이

```
Claude Code/Desktop:
  "검수확인서 홍길동으로 채워줘"
    ↓ 자동: template list → context 로드 → 채우기 → 저장
  "완료. /Users/.../검수확인서_완성.hwpx"

ChatGPT Code Interpreter:
  [세션 시작] !pip install pyhwpxlib
  [파일 첨부] 검수확인서.hwpx 업로드
  [메시지] "컨텍스트: (--brief 출력 붙여넣기). 홍길동으로 채워줘"
    ↓ 코드 실행 → 결과 파일
  [다운로드] output.hwpx 클릭 → 로컬에 저장 → Whale에서 확인
```

**세션당 추가 작업**: pip install (~30초) + 파일 업로드 + 컨텍스트 붙여넣기 + 다운로드

---

## 구현 우선순위

| 항목 | 대상 | 우선순위 |
|------|------|---------|
| `--brief` 플래그 | Stage 1 범위 | 🔴 필수 |
| `chatgpt_hwpx_guide.md` 세션 시작 섹션 추가 | 문서 수정 | 🔴 필수 |
| `chatgpt_hwpx_guide.md` 파일 업로드/다운로드 섹션 | 문서 수정 | 🔴 필수 |
| Custom Instructions 예시 | 문서 추가 | 🟡 권장 |
| GPT Builder Knowledge 패키지 스크립트 | Stage 4 신규 | 🟡 권장 |
| Gemini 전용 가이드 | 문서 추가 | 🟢 선택 |
