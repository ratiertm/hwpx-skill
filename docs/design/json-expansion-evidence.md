 증거: HwpxBuilder 메서드 풀 vs decoder 사용 메서드

  ┌─────────────────────────────────────┬──────────────────────────────────────────────┬──────┐
  │                구분                 │                     갯수                     │ 비율 │
  ├─────────────────────────────────────┼──────────────────────────────────────────────┼──────┤
  │ HwpxBuilder가 제공하는 add_ 메서드* │                                         19개 │ 100% │
  ├─────────────────────────────────────┼──────────────────────────────────────────────┼──────┤
  │ decoder.from_json 이 실제 호출      │ 3개 (paragraph / table / page_break) + .save │ ~16% │
  └─────────────────────────────────────┴──────────────────────────────────────────────┴──────┘

  사용 안 되는 풍부한 메서드 16개

  .add_heading()              → 헤딩 스타일 (level 1~3)
  .add_image()                → 이미지 삽입
  .add_image_from_url()       → URL 이미지
  .add_header() / .add_footer()→ 머리말/꼬리말
  .add_footnote()             → 각주
  .add_page_number()          → 페이지 번호
  .add_highlight()            → 형광펜
  .add_draw_line() / .add_line()/ .add_rectangle()  → 도형
  .add_equation()             → 수식
  .add_bullet_list() / .add_numbered_list()        → 글머리표/번호 목록
  .add_nested_bullet_list() / .add_nested_numbered_list()  → 중첩 목록

  → JSON 경로로 만들면 이 16개를 표현할 방법이 없음 → 결과 HWPX가 단조.

  HwpxJsonDocument 스키마도 빈약

  graphify가 schema에서 식별한 노드는 HwpxJsonDocument + .to_dict() 2개뿐. 풍부한 sub-field
  (image/heading/list/header 등)이 별도 노드로 분리 안 되어 있음 = JSON 구조 자체가 paragraph + table +
  page_break 수준.

  그래서 두 경로의 표현력이 극과 극

  ┌─────────────────────────────────┬────────────────────────┬──────────────────────────────────────────────┐
  │              경로               │         표현력         │                 사용 메서드                  │
  ├─────────────────────────────────┼────────────────────────┼──────────────────────────────────────────────┤
  │ HwpxBuilder 직접 호출 (Python   │ 풍부 (19개 모두)       │ heading/image/list/footnote/header/footer/등 │
  │ 코드)                           │                        │                                              │
  ├─────────────────────────────────┼────────────────────────┼──────────────────────────────────────────────┤
  │ JSON → from_json (MCP, 외부     │ 단조                   │ paragraph/table/page_break만                 │
  │ 도구)                           │                        │                                              │
  ├─────────────────────────────────┼────────────────────────┼──────────────────────────────────────────────┤
  │ overlay (기존 양식 채우기)      │ 양식 자체의 풍부함     │ 텍스트/이미지/표 셀 patch                    │
  │                                 │ 그대로                 │                                              │
  └─────────────────────────────────┴────────────────────────┴──────────────────────────────────────────────┘

  해결 방향

  옵션 A — JSON schema 확장 (정공법, 큰 작업)
  - HwpxJsonDocument 에 headings: list, images: list, header/footer, lists, footnotes 필드 추가
  - decoder.from_json 에 매핑 로직 추가 — 16개 builder 메서드 호출
  - 효과: JSON 경로도 직접 호출 수준으로 풍부

  옵션 B — overlay 패턴 우선 (실용적)
  - 풍부한 양식을 HwpxBuilder 로 한 번 만들어 templates/에 보관
  - 이후엔 overlay로 채우기 → 양식의 풍부함 그대로
  - 이미 우리가 makers_project_report 에서 한 패턴

  옵션 C — JSON 안에 raw XML/builder 스크립트 임베드 (편법)
  - {"type": "raw_builder_call", "method": "add_heading", "args": {...}} 같은 escape hatch
  - 빠르지만 schema 깨짐


 설계 — Template Workflow

  사용자 시나리오

  사용자: "이 양식.hwp 를 template으로 등록해줘"
          ↓
  [1] 자동 등록     pyhwpxlib template add my_form.hwp --name my_form
          ├─ HWP→HWPX 변환
          ├─ precise fix (한컴 보안)
          ├─ ASCII 이름 보정
          ├─ 셀 분석 → schema.json 자동 생성 (라벨/빈셀 매핑)
          ├─ skill/templates/my_form.hwpx + my_form.schema.json 저장
          ├─ skill/templates/README.md 자동 추가
          └─ PNG 프리뷰 + schema 미리보기 출력 → 사용자 검토 요청

  [2] schema 검토    schema 자동 생성은 휴리스틱 → 필드 key 이름 등 사용자가 수정 가능
          pyhwpxlib template show my_form          → schema 미리보기
          pyhwpxlib template edit my_form          → schema 편집

  [3] 양식 사용     양식 채우기
          pyhwpxlib template fill my_form -d data.json -o out.hwpx
          # 또는 Python:
          from pyhwpxlib.templates import fill
          fill("my_form", data={"team_name": "X", ...}, output="out.hwpx")

  저장 위치 — 두 계층 (권장)

  ┌────────────────────────────────────────────┬───────────────────────────────────────────┬──────────────┐
  │                    위치                    │                   용도                    │     배포     │
  ├────────────────────────────────────────────┼───────────────────────────────────────────┼──────────────┤
  │ skill/templates/ (project)                 │ 모두 공유할 표준 양식 (makers, 공문서 등) │ git/zip 배포 │
  ├────────────────────────────────────────────┼───────────────────────────────────────────┼──────────────┤
  │ ~/.local/share/pyhwpxlib/templates/ (user) │ 사용자 개인 양식                          │ 로컬 only    │
  └────────────────────────────────────────────┴───────────────────────────────────────────┴──────────────┘

  pyhwpxlib template add my_form 의 default = user dir.
  pyhwpxlib template add my_form --shared = skill/templates (commit 의도).

  자동 schema 생성 로직 (어려운 부분)

  def auto_schema(hwpx):
      schema = {"name": ..., "tables": []}
      for t_idx, table in enumerate(tables):
          cells = parse_cells(table)
          fields = []
          for cell in cells:
              text = extract_text(cell)
              row, col = cell.addr

              # 휴리스틱: 빈 셀 = value, 라벨 셀 = label
              if not text.strip():
                  # 옆/위 셀 라벨 찾기 (인접 검색)
                  label = find_label_for(row, col, table)
                  key = slugify(label)  # "팀명" → "team_name"
                  fields.append({"key": key, "cell": [row, col], "label": label})
              elif looks_like_placeholder(text):  # "xx.xx.xx", "0회차" 등
                  key = slugify(label_or_text)
                  fields.append({
                      "key": key, "cell": [row, col],
                      "label": label, "placeholder": text
                  })
          schema["tables"].append({"index": t_idx, "fields": fields})
      return schema

  핵심 휴리스틱:
  1. 빈 셀 + 인접 라벨 = value 셀
  2. placeholder 패턴 (xx.xx, 0회차, (예시)) = 채울 슬롯
  3. 모두 빈 행 다중 = 반복 항목 (참여자 1~N) — 패턴 감지 후 인덱싱

  구현 분량

  ┌───────────────────────────────────────────┬─────────────┬──────┐
  │                 컴포넌트                  │  신규/기존  │ 시간 │
  ├───────────────────────────────────────────┼─────────────┼──────┤
  │ templates/ 모듈 (add/show/edit/fill/list) │ 신규 ~250줄 │ 2h   │
  ├───────────────────────────────────────────┼─────────────┼──────┤
  │ auto_schema 휴리스틱                      │ 신규 ~120줄 │ 1.5h   │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ label slugify (한글→ASCII)                │ 신규 ~30줄  │ 20분   │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ user dir resolver (XDG)                   │ 신규 ~20줄  │ 10분   │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ CLI pyhwpxlib template ... 4개            │ 신규 ~80줄  │ 30분   │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ 테스트 + makers 마이그레이션              │ 신규 ~100줄 │ 1h     │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ skill 가이드 (templates/README.md 갱신)   │ 갱신        │ 20분   │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ PyPI 0.13.3 출시                          │ 갱신        │ 10분   │
  ├───────────────────────────────────────────┼─────────────┼────────┤
  │ 합계                                      │             │ ~6시간 │
  └───────────────────────────────────────────┴─────────────┴────────┘

  한계 (정직)

  - 자동 schema는 휴리스틱이라 ~70% 정확. 복잡한 양식(중첩 표, 동적 행)은 사용자 수정 필요.
  - 한글 라벨 → ASCII key slug는 음역 라이브러리 필요 (또는 단순 transliterate)
  - 반복 항목 감지 (참여자 1~4) — 일반 휴리스틱 어렵, 사용자 명시 권장

  진행 옵션

  ┌─────┬─────────────────────────────────────────────────────────────────┬──────┐
  │  #  │                              범위                               │ 시간 │
  ├─────┼─────────────────────────────────────────────────────────────────┼──────┤
  │ A   │ 최소 — template fill 만 (기존 makers schema 재사용, add는 수동) │ 1h   │
  ├─────┼─────────────────────────────────────────────────────────────────┼──────┤
  │ B   │ 중간 — fill + add (자동 schema 70%) + user dir 계층             │ 3h   │
  ├─────┼─────────────────────────────────────────────────────────────────┼──────┤
  │ C   │ 풀 — B + edit/list/share + PyPI + 테스트                        │ 6h   │
  └─────┴─────────────────────────────────────────────────────────────────┴──────┘

  권장: B 먼저 (실용 80%). C는 사용 늘면 확장.
