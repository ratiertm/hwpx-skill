# Requirements — pyhwpxlib v0.5

## Table Stakes (없으면 출시 불가)

### TS-1: 테마 시스템 기본 구조
- `HwpxBuilder(theme='name')` API
- 테마 = 팔레트(색상) + 폰트 세트 + 사이즈 세트 + 여백
- 기존 `DS` dict, `TABLE_PRESETS` 를 테마 시스템으로 통합
- 기본 테마 10종 (design_guide.md 팔레트 기반)
- `theme='default'` → 현재 동작과 하위 호환

### TS-2: 폰트 시스템
- header.xml `fontfaces`에 복수 폰트 등록
- 제목/본문/캡션 폰트 분리
- `charPr`에서 올바른 `fontRef` 참조
- 한글/라틴 폰트 분리 가능 (예: 나눔명조 + Arial)

### TS-3: JSON Overlay `<hp:t>` 단위 교체
- `extract_overlay`에서 개별 `<hp:t>` 원본 보존
- `apply_overlay`에서 `<hp:t>` 단위로 정밀 매칭/교체
- 분리된 텍스트 (`울산중부` + `소방서`) 정확히 교체

### TS-4: BinData 에러 핸들링
- `hwp2hwpx.convert()` — BinData 압축 해제 실패 시 스킵 + warning
- 이미지 없는 HWPX는 정상 생성 (텍스트/레이아웃 보존)
- 크래시 방지

## Core Features

### CF-1: 동적 테마 추출
- `extract_theme(hwpx_path)` → 커스텀 테마 JSON
- header.xml에서 charPr/paraPr → 폰트, 크기, 색상 추출
- 표 헤더 배경색, 셀 스타일 추출
- 추출된 테마를 `~/.pyhwpxlib/themes/` 또는 프로젝트 내 저장
- 저장된 커스텀 테마를 `HwpxBuilder(theme='custom/my-form')` 로 사용

### CF-2: JSON Overlay 이미지 교체
- overlay JSON에서 `new_data_b64` 필드로 이미지 교체
- BinData 파일 교체 + XML 참조 유지

### CF-3: Overlay 중첩 표 지원
- 셀 내부 중첩 표의 텍스트도 overlay에 포함
- 중첩 표 셀 교체 동작

## Nice-to-have

### NH-1: 테마 프리뷰
- `preview_theme('forest')` → 샘플 문서 생성 + PNG 프리뷰
- 테마 선택 전 시각 비교 가능

### NH-2: CSS-like 스타일 문법
- `HwpxBuilder(css="h1 { font: 나눔스퀘어Bold 24pt; color: #2C5F2D }")`
- LLM이 이해하기 쉬운 스타일 지정

### NH-3: 테마 마켓플레이스 연동
- 커뮤니티 테마 공유/다운로드
