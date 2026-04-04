# hwpx-skill 코드 리뷰 보고서

**프로젝트**: hwpx-skill
**날짜**: 2026-04-05
**분석 범위**: pyhwpxlib (10개 모듈, 8,260줄) + templates (2개 모듈, 1,571줄)

---

## 1. 프로젝트 현황 요약

| 모듈 | 파일 | 줄 수 | 역할 |
|------|------|-------|------|
| pyhwpxlib/api.py | 핵심 API | 2,112 | 54개 API 함수 (텍스트/이미지/표/도형 등) |
| pyhwpxlib/style_manager.py | 스타일 관리 | 986 | charPr/borderFill/paraPr 생성 |
| pyhwpxlib/html_to_hwpx.py | HTML→HWPX | 941 | HTML 파서 기반 변환기 |
| pyhwpxlib/html_converter.py | HWPX→HTML | 797 | XML→HTML 변환기 |
| pyhwpxlib/converter.py | MD→HWPX | 588 | 마크다운 변환기 |
| pyhwpxlib/reader.py | HWPX 리더 | 432 | 구조적 읽기 (dataclass 기반) |
| pyhwpxlib/object_type.py | 타입 정의 | 370 | ObjectType 열거형 |
| pyhwpxlib/cli.py | CLI | 202 | 명령행 인터페이스 |
| pyhwpxlib/hwpx_file.py | 파일 컨테이너 | 128 | HWPX 파일 구조 |
| pyhwpxlib/base.py | 기반 클래스 | 127 | ObjectList, SwitchableObject 등 |
| templates/form_pipeline.py | 서식 파이프라인 | 1,307 | extract→generate→clone |
| templates/hwpx_generator.py | HWPX 생성기 | 264 | ZIP 기반 라운드트립 |

---

## 2. 심각도별 이슈 요약

| 심각도 | 건수 | 핵심 이슈 |
|--------|------|----------|
| **HIGH** | 6건 | 광범위 예외 무시, 중복 코드, 듀얼 데이터 모델, None 체크 누락 |
| **MEDIUM** | 10건 | 장함수, 매직 넘버, 취약한 XML regex, 상태 머신 복잡도 |
| **LOW** | 8건 | 독스트링 누락, 타입 힌트 부족, 에러 메시지 모호 |

---

## 3. HIGH 이슈 상세

### 3-1. `except Exception: pass` 남용 (api.py, html_to_hwpx.py, form_pipeline.py)

**현황**: html_to_hwpx.py에 11건, html_converter.py에 3건, form_pipeline.py에 7건의 광범위 예외 무시가 있음

```python
# html_to_hwpx.py — 현재
except Exception:
    pass  # 이미지 변환 실패도 조용히 무시

# 권장
except (ValueError, IOError) as e:
    logger.warning(f"Image conversion failed: {e}")
```

**위험**: 변환 실패 시 데이터가 조용히 누락되고, 디버깅이 사실상 불가능

### 3-2. api.py 초기화 코드 12회 반복

**현황**: 동일한 paragraph 초기화 블록(6줄)이 12곳 이상에서 복사-붙여넣기됨

```python
# 12곳에서 반복되는 패턴
para.id = str(_random.randint(1000000000, 4294967295))
para.para_pr_id_ref = "0"
para.style_id_ref = "0"
para.page_break = False
para.column_break = False
para.merged = False
```

**권장**: `_init_para(para)` 헬퍼 함수 추출 → 78줄+ 감소

### 3-3. form_pipeline.py 듀얼 데이터 모델

**현황**: 추출 단계에서 `paragraphs` (신규 모델)과 `tables` + `before_table_text` (구 모델)을 동시에 추출. 생성 시 `if paragraphs:`로 분기하지만, 두 모델의 일관성이 보장되지 않음.

**위험**: 구 모델은 단일 표만 지원하므로 다중 페이지에서 데이터 손실 가능. 구 모델 제거 시 하위 호환성 고려 필요.

### 3-4. form_pipeline.py `.find()` 후 None 체크 누락

**현황**: 12곳 이상에서 `.find()` 결과를 검증 없이 `.set()` 호출

```python
# line 1103 — 현재
nsz = temp_tbl.element.find(f"{_HP}sz")
nsz.set("width", str(ntbl_w))  # nsz가 None이면 AttributeError

# 권장
nsz = temp_tbl.element.find(f"{_HP}sz")
if nsz is not None:
    nsz.set("width", str(ntbl_w))
```

### 3-5. form_pipeline.py XML regex 조작

**현황**: header.xml에서 fontfaces/charProperties/borderFills를 regex로 추출/교체하는 패턴이 취약

```python
# line 718 — 현재: regex로 XML 블록 교체
pattern = r'<[^>]*?' + tag_name + r'[^>]*>.*?</[^>]*?' + tag_name + r'>'
```

**위험**: 네임스페이스 변경, 속성 순서 변경, 주석 포함 시 실패 가능. ElementTree API 사용 권장.

### 3-6. 장함수 (50줄 초과)

| 파일 | 함수 | 줄 수 |
|------|------|-------|
| form_pipeline.py | `_generate_form()` | 215줄 |
| form_pipeline.py | `_generate_table()` | 220줄 |
| form_pipeline.py | `_generate_from_paragraphs()` | 112줄 |
| api.py | `add_nested_numbered_list()` | 92줄 |
| style_manager.py | `ensure_para_style()` | 99줄 |

---

## 4. MEDIUM 이슈

### 4-1. 매직 넘버 (form_pipeline.py, api.py, converter.py)

```python
# 문서화 안 된 상수들
59528   # 페이지 너비 (1/20mm 단위)
84188   # 페이지 높이
141     # 셀 마진 기본값 — 5곳에서 반복
3600    # 행 높이 기본값 — 3곳에서 반복
283     # 중첩 표 바깥 마진
510     # 중첩 표 안쪽 마진
42520   # converter.py 페이지 너비
```

**권장**: 모듈 상단에 `Defaults` 클래스나 상수로 정의

### 4-2. html_to_hwpx.py 상태 머신 복잡도

파서가 18개 인스턴스 변수로 상태를 관리. `_in_td`, `_in_li`, `_list_stack`, `_list_items` 등 겹치는 컨텍스트가 있어 예외 발생 시 상태 불일치 가능.

### 4-3. style_manager.py 코드 중복

`ensure_char_style()`, `ensure_border_fill()`, `ensure_gradient_border_fill()`, `ensure_para_style()` 간 유사한 패턴 반복. "base object not found" 에러 처리가 3곳에서 동일하게 반복.

### 4-4. reader.py XML 파싱 edge case

- `int()` 변환 시 ValueError 미처리 (cellAddr 속성)
- `_find_sections_from_manifest()`에서 KeyError를 조용히 무시하고 빈 리스트 반환
- ET.fromstring() 파싱 에러 미처리

---

## 5. 강점

### 잘 된 부분

- **api.py**: 61개 함수 중 97%에 return 타입 힌트. 모듈 독스트링과 사용 예제 우수
- **reader.py**: dataclass 기반 깔끔한 설계. 2011/2016/2024 HWPML 네임스페이스 호환
- **style_manager.py**: 상세한 파라미터/리턴 문서화. 100% return 타입 커버리지
- **converter.py**: 깔끔한 regex 패턴 기반 마크다운 파싱. 100% return 타입 커버리지
- **form_pipeline.py**: p 단위 구조 설계로 다중 페이지/중첩 표 지원 달성. 22커밋 누적 버그 수정으로 실전 검증됨
- **HWPX_RULEBOOK.md**: 리버스 엔지니어링에서 발견한 23개 규칙을 체계적으로 문서화

---

## 6. 리팩토링 우선순위 제안

### Phase 1: 안정성 (1-2일)

1. **`except Exception: pass` → 구체적 예외 + 로깅** (21건)
2. **`.find()` 후 None 체크 추가** (12건)
3. **임시 파일을 `TemporaryDirectory`로 교체** (form_pipeline.py)

### Phase 2: 구조 개선 (2-3일)

4. **api.py `_init_para()` 헬퍼 추출** — 78줄 감소
5. **form_pipeline.py `_generate_table()` 5개 함수로 분리**
   - `_setup_table_structure()` / `_populate_cells()` / `_apply_merges()` / `_apply_styles()` / `_generate_nested_tables()`
6. **form_pipeline.py 구 데이터 모델 제거** — paragraphs 모델로 통합
7. **매직 넘버 → 명명 상수** (모듈 상단 Defaults 클래스)

### Phase 3: 품질 향상 (2-3일)

8. **XML regex → ElementTree API** (form_pipeline.py header 교체 로직)
9. **html_to_hwpx.py 파서 상태 머신 리팩토링** — 작은 핸들러 클래스로 분리
10. **독스트링 추가** — 미문서화 함수 19개
11. **타입 힌트 보강** — html_to_hwpx.py (현재 74% → 100%)

### Phase 4: 테스트 (2일)

12. **`_reverse_grid()` 단위 테스트** — colspan/rowspan 엣지 케이스
13. **form_pipeline 라운드트립 통합 테스트** — extract→generate→verify
14. **html 변환기 엣지 케이스 테스트** — 빈 테이블, 중첩 목록, 깨진 HTML

---

## 7. 코드 메트릭

| 메트릭 | 값 | 평가 |
|--------|-----|------|
| 총 줄 수 | 9,831줄 | 중간 규모 |
| 함수 수 | ~150개 | 적절 |
| return 타입 커버리지 | ~92% | 양호 |
| 독스트링 커버리지 | ~75% | 개선 필요 |
| 광범위 예외 처리 | 21건 | 위험 — 최우선 수정 |
| 장함수 (>50줄) | 9개 | 분할 필요 |
| 매직 넘버 | 15+개 | 상수화 필요 |

---

*AI가 생성한 분석 보고서입니다. 구체적인 리팩토링 시 실제 동작 확인이 필요합니다.*
