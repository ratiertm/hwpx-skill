# 프로젝트 보고서

## 1. 개요

이 문서는 **python-hwpx** 라이브러리의 기능을 테스트하기 위한 마크다운 파일입니다.
*이탈릭체*와 **볼드체**가 올바르게 변환되는지 확인합니다.

자세한 내용은 [공식 문서](https://github.com/niceguy61/python-hwpx)를 참고하세요.

## 2. 주요 기능

### 2.1 텍스트 처리

- 일반 텍스트 추가
- **볼드** 텍스트
- *이탈릭* 텍스트
- `인라인 코드` 처리

### 2.2 구조 요소

- 표 생성 및 편집
  - 셀 병합
  - 배경색 지정
  - 그라데이션 채우기
- 이미지 삽입
- 도형 (사각형, 원, 선)

## 3. 개발 로드맵

1. Phase 1: 기본 텍스트
2. Phase 2: 표와 이미지
   1. 표 생성
   2. 이미지 삽입
3. Phase 3: 도형과 수식
4. Phase 4: 필드와 폼
5. Phase 5: OLE와 차트

## 4. 코드 예시

```python
from hwpx import HwpxDocument

doc = HwpxDocument.new()
doc.add_heading("보고서", level=1)
doc.add_paragraph("본문 내용입니다.")

# 표 추가
tbl = doc.add_table(3, 2)
tbl.set_cell_text(0, 0, "항목")
tbl.set_cell_text(0, 1, "값")

doc.save_to_path("report.hwpx")
```

```javascript
// 프론트엔드 예시
const response = await fetch('/api/convert', {
  method: 'POST',
  body: formData
});
const result = await response.json();
console.log(result.output);
```

## 5. 성능 비교표

| 항목 | python-hwpx | 한컴오피스 | 비고 |
|------|------------|-----------|------|
| 문서 생성 | 0.1초 | 2초 | CLI 기준 |
| 표 추가 | 0.05초 | 1초 | 10x3 표 |
| 이미지 삽입 | 0.2초 | 1.5초 | PNG 1MB |
| 내보내기 | 0.3초 | 3초 | Markdown |

## 6. 참고 링크

프로젝트 홈: [python-hwpx GitHub](https://github.com/niceguy61/python-hwpx)

한컴 공식: [한컴오피스 OWPML](https://www.hancom.com)

## 7. 참고사항

> 이 줄은 인용문입니다. blockquote 스타일이 적용됩니다.

---

**문서 끝** — 작성일: 2026-03-28
