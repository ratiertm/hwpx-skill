---
name: hwpx-form
description: "기존 HWPX 양식(.hwpx)에 데이터를 채울 때 트리거. '양식 채우기', '빈칸 채워줘', '서식에 입력', 등록된 양식 이름(검수확인서·지급조서·의견제출서 등) 언급, 또는 사용자가 .hwpx 양식 파일을 첨부하고 데이터 입력을 요청할 때. 새 문서 생성(hwpx 메인 스킬 워크플로우 [1])이나 단순 편집(워크플로우 [2])과 구별 — 양식은 페이지 표준·1매 강제·구조 A/B 판정 같은 고유 절차를 가진다. .docx/PDF/스프레드시트는 사용 금지."
---

# HWPX Form Fill Workflow

> 부모 스킬: **hwpx** (절대 규칙·디자인 규칙·Critical Rules·Versions 표는 거기에 있음).
> 이 파일은 *양식 채우기 워크플로우* 한 가지에만 집중.

## 적용 조건

- 입력: 기존 `.hwpx` 양식 파일 (사용자 제공 또는 워크스페이스 등록 양식)
- 출력: 데이터가 채워진 `.hwpx` 결과물 (1매 표준이면 정확히 1페이지)
- 결정사항: 다음 채팅에서 자동 복원되도록 워크스페이스에 저장

## 절대 전제

1. **모든 채우기 후 SVG/PNG 프리뷰 시각 확인 필수** (생략 금지 — 부모 스킬 절대 규칙 #7)
2. **page-guard 통과 게이트** (v0.16.0+) — exit 0 일 때만 완료 처리 (Critical Rule #12·#13)
3. **워크스페이스 박제** (v0.17.0+) — 최초 등록 시 메타·결정사항을 박제, 매 세션 종료 시 `save_session` 으로 누적

---

## Step 0: 컨텍스트 자동 로드 (등록 양식이면 우선)

```python
from pyhwpxlib.templates.context import load_context
ctx = load_context(name)   # 결정사항·이전 채우기 값·구조 타입·페이지 표준 자동 복원
print(ctx.to_markdown())
```
또는 CLI: `pyhwpxlib template context <name>`.

**이전 채팅의 합의가 살아 있다 → 사용자가 양식을 다시 업로드하거나 설명할 필요 없음.**

미등록이면 → Step 0' 메타 인지로.

## Step 0': 메타 인지 (미등록 양식만)

양식은 페이지 표준이 강하므로 5질문 필수 (`references/form_automation.md` 상단 참조):

1. 이 양식은 무엇인가? (지급조서·검수확인서·신청서·동의서·증빙·계약서…)
2. 누가 채우고 누가 받는가?
3. 페이지 표준이 있는가? (1매 강제 / 자유)
4. (예시) 페이지가 있나? — 결과물에선 보통 제거
5. 미리 인쇄된 항목? — 사업명·기관명·도장 자리는 보존

확인 후 **워크스페이스 등록** (다음 채팅에서 자동 복원되도록):
```bash
pyhwpxlib template add <source.hwpx> --name <key>
pyhwpxlib template annotate <key> --description "<무엇>" --structure-type A|B --page-standard 1page|free
```

## Step A: 프리뷰 렌더링 → 시각 분석

PNG/SVG 로 양식 페이지 전체 렌더링 → Read tool 로 직접 확인.

## Step B: 필드 입력 요청

`ctx.recent_data` 가 있으면 보여주고 재사용/일부 수정 옵션 제안.

## Step C: 구조 판정 — 인접 셀(A) vs 같은 셀(B)

- **구조 A** (label 셀과 값 셀이 분리): `pyhwpxlib.api.fill_by_labels()` 또는 `fill_template()`
- **구조 B** (label + 값이 같은 셀, "성 명: ___" 형태): `unpack → 원본 문자열 교체 → pack`
- 판정 결과는 **반드시 워크스페이스에 박제** (Step G):
  ```
  template annotate <key> --structure-type A|B
  ```

## Step D: 프리뷰 검증

채우기 후 PNG 재렌더링 → 시각 확인 → 사용자에게 Whale 확인 요청.

## Step E: 1페이지 fit 검증 (1매 표준 양식)

- `page_count == 1` 인지 확인
- 넘치면 `GongmunBuilder(autofit=True)` 로 코드 위임 (폰트/줄간격/셀 높이 조정 알고리즘은 결정론 영역 — LLM이 mm 단위 임의 결정 금지)
- autofit 후에도 실패 → 사용자에게 보고하고 수동 조정 요청

## Step F: page-guard 통과 (필수 게이트)

```bash
pyhwpxlib page-guard --reference original_form.hwpx --output filled.hwpx
# exit 0 (PASS) 일 때만 완료 처리. exit 1 (FAIL) 시 텍스트 압축 / autofit 재시도
```

## Step G: 세션 종료 — 결정사항·이력 한 번에 박제 (생략 금지)

다이어리제이션 루프의 마지막 자동 잠금장치. **단일 MCP 호출** 로 끝.

```
hwpx_template_save_session(
  name="<key>",
  data='<채운 데이터 JSON>',
  decision="이번 채팅에서 새로 합의한 규칙 (예: '프로젝트명 필드는 줄바꿈 금지')"
)
```

내부 동작:
- `data` 가 있으면 → `history.json` 에 FIFO 10건으로 누적, `outputs/YYYY-MM-DD_<key>.hwpx` 자동 명명
- `decision` 이 있으면 → `decisions.md` 최상단에 오늘 날짜 블록으로 추기
- 둘 다 비어 있으면 → no-op (`{"saved": false}` 반환)

CLI 대안 (MCP 미사용 시):
```bash
pyhwpxlib template log-fill <key> --data '<json>'
pyhwpxlib template annotate <key> --decision "<note>"
```

> **다음 세션에 이 판단이 자동 복원됩니다** — 이게 컨텍스트 지속성의 본질.

---

## 안티 패턴

- ❌ Step F (page-guard) 건너뛰고 "완료" 보고 → Critical Rule #13 위반
- ❌ Step E 에서 LLM 이 폰트 size 를 mm 단위로 임의 결정 → 결정론 영역 침범
- ❌ Step G 누락 → 다음 채팅에서 같은 양식을 처음부터 재판정해야 함 (다이어리제이션 깨짐)
- ❌ 구조 B 양식에 `fill_by_labels()` 사용 → 빈 칸이 채워지지 않음 (label+값 한 셀이라서)
- ❌ "(예시)" 페이지를 결과물에서 제거하지 않음 → 1매가 2매로 부풀음

## 관련 문서

- `references/form_automation.md` — fill_template / batch_generate / schema_extraction 상세
- `references/HWPX_RULEBOOK.md` — Critical Rules #10~#13 (의도 룰)
- 부모 `SKILL.md` — 절대 규칙, 디자인 규칙, Versions 표
