# Skill Templates

번들된 한국어 양식(.hwpx) 모음. 모두 한컴 보안 회피(precise) 적용 완료.

## 양식 목록

| 파일 | 용도 | Schema |
|------|------|--------|
| `makers_project_report.hwpx` | 대학 Makers 프로젝트 중간/최종 결과보고서 (제5호 서식, 한국어 양식) | `makers_project_report.schema.json` |

## 공통 사용 패턴

### 1) 양식 로드
```python
from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

src = "skill/templates/makers_project_report.hwpx"
arch = read_zip_archive(src)
```

### 2) Schema 로 필드 위치 확인
```python
import json
schema = json.loads(open("skill/templates/makers_project_report.schema.json").read())
for tbl in schema["tables"]:
    for f in tbl["fields"]:
        print(f["key"], "->", f"표[{tbl['index']}] cell={f['cell']}", "(", f["label"], ")")
```

### 3) 빈 셀 채우기 — 직접 정규식 교체
```python
import re

xml = arch.files["Contents/section0.xml"].decode("utf-8")

def fill_cell_text(xml, table_idx, row, col, new_text):
    """특정 표의 (row, col) 셀의 첫 paragraph 첫 hp:t를 new_text로 교체."""
    # depth-aware 표/셀 매칭은 references/form_automation.md depth-aware 함수 참조
    ...

# Schema 필드 모두 채우기 (예시)
data = {
    "team_name": "Team Alpha",
    "project_name": "WebAR 가이드",
    "member_1_name": "홍길동",
    "member_1_dept": "컴퓨터공학과",
    "member_1_id": "20240001",
    # ...
    "period": "2026.03.01. ~ 2026.06.30.",
    "report_date": "2026.06.30.",
}
# (실제 cellAddr 매칭 + 텍스트 교체는 references/form_automation.md 패턴)
```

### 4) 한컴 안전 저장 (precise default)
```python
write_zip_archive("output.hwpx", arch)
# strip_linesegs="precise" (default) — overflow lineseg만 제거
```

### 5) 검증
```bash
pyhwpxlib lint output.hwpx       # TEXTPOS_OVERFLOW 가 없어야 함
pyhwpxlib validate output.hwpx
```

## 새 양식 추가

1. `samples/` 에 `.hwp` 또는 `.hwpx` 원본 보관
2. `pyhwpxlib.hwp2hwpx.convert()` 로 hwpx 변환 (HWP인 경우)
3. `pyhwpxlib.package_ops.write_zip_archive(path, archive)` 로 한컴 보안 자동 fix 후 `skill/templates/` 에 저장
4. `references/form_automation.md` 패턴으로 셀 위치 분석 (`<hp:cellAddr>`)
5. `<양식이름>.schema.json` 작성 — fields = `{key, cell:[row,col], span?:[rs,cs], label, type?, placeholder?}`
6. 이 README에 추가
7. 사용자 skill 동기화 + zip 재생성

상세 → [../references/form_automation.md](../references/form_automation.md)
