# pyhwpxlib 코드 리뷰 지적사항 정리

기준: 설치된 `pyhwpxlib 0.7.0` 로컬 소스 기준  
대상 범위: `builder.py`, `cli.py`, `themes.py`, `rhwp_bridge.py`, `mcp_server/server.py` 등

---

## 총평

`pyhwpxlib`는 **HWPX 생성 → 편집 → 검증 → 미리보기**까지 이어지는 흐름이 잘 잡혀 있는 라이브러리입니다.  
특히 `HwpxBuilder` 중심의 설계, 테마 시스템, `guide`/`validate`/`font-check`/`preview` 흐름은 매우 실용적입니다.

다만 현재 상태는 **“잘 동작하는 기능 모음”에서 “안정적인 배포형 라이브러리”로 넘어가는 과도기**에 가깝습니다.  
핵심 보완 포인트는 다음 네 가지입니다.

1. 전역 상태 오염 제거
2. 다운로드/임시파일 처리 안전성 강화
3. `validate`의 의미 강화
4. 폰트 해석 일관성 개선

---

## 주요 장점

### 1. 진입점이 명확함
- `HwpxBuilder`를 중심으로 사용 흐름이 일관적임
- XML 직접 조작을 피하게 유도하는 방향이 맞음
- HWPX처럼 렌더 민감한 포맷에 적합한 접근

### 2. 테마 시스템이 잘 분리됨
- `Palette`, `FontSet`, `SizeSet`, `Margins`, `Density`, `Theme` 구조가 깔끔함
- 확장성과 재사용성이 좋음

### 3. Preview 엔진 분리
- `rhwp_bridge`를 optional dependency로 분리한 판단이 좋음
- 기본 설치는 가볍게, preview는 extra 설치로 분리 가능

### 4. CLI가 실용적임
- `guide`, `validate`, `font-check`, `themes list/extract/delete`는 실제 사용자 관점에서 유용함
- 단순 라이브러리를 넘어 툴킷 성격을 가짐

---

## 우선 수정 권장 사항

### 1. `builder.save()`에서 전역 `sys.path`를 변경함
위치: `builder.py`

문제:
- 호출 시 전역 import 경로를 오염시킴
- 다른 패키지와 충돌 가능성이 있음
- 설치형 라이브러리 코드에서는 피해야 할 패턴임

영향:
- 예기치 않은 import shadowing 가능
- 실행 환경에 따라 불안정성 증가

권장:
- `sys.path.insert()` 제거
- 상대 import / 정상 패키지 import만 사용
- 정말 필요하면 개발용 코드와 배포용 코드를 분리

---

### 2. `add_image_from_url()`의 임시파일 처리 방식이 안전하지 않음
위치: `builder.py`

문제:
- 고정 파일명 기반 저장으로 충돌 가능
- 같은 이름이면 덮어쓰기 발생 가능
- timeout 없음
- 다운로드 크기 제한 없음
- 예외 메시지 정리가 부족함

영향:
- 동일 파일명 사용 시 이미지 덮어쓰기
- 느린 응답/대용량 파일로 인한 hang 위험
- 디버깅 불편

권장:
- `NamedTemporaryFile(delete=False)` 또는 UUID 기반 파일명 사용
- timeout 추가
- 최대 다운로드 크기 제한
- Content-Type / 확장자 검증
- 사용자 친화적 예외 메시지 제공

---

### 3. `validate`가 “렌더 안정성 검사” 수준까지는 아님
위치: `cli.py`

현재 확인 범위:
- ZIP 구조 확인
- 필수 파일 존재 여부 확인
- 일부 XML 파싱 확인

문제:
- 현재 `VALID`는 “최소 구조가 깨지지 않았다”는 의미에 가까움
- 실제 Whale/Hancom 렌더 안정성까지 보장하지 못함

놓치고 있는 위험 예:
- 텍스트 내부 `\n`
- `secPr` 위치 문제
- 렌더러가 싫어하는 문단 구조
- 폰트 fallback 충돌
- 표 셀 내부 줄바꿈 구조 문제

권장:
- `validate`와 `lint`를 분리
- `validate`: 구조적 최소 유효성 확인
- `lint`: 렌더 위험 규칙 검사

예시 lint 항목:
- 텍스트 노드 내 `\n` 존재 여부
- 첫 content paragraph 이전 빈 문단 존재 여부
- 폰트 참조/폰트맵 누락 여부
- 표 셀 내부 줄바꿈 처리 방식 검사

---

### 4. `font-check`가 출발은 좋지만 아직 정확한 해석기 수준은 아님
위치: `cli.py`

문제:
- `header.xml`의 font 정보만 보는 수준에 가까움
- 실제 preview 렌더링의 최종 fallback 결과와 다를 수 있음
- 사용자 지정 `font_map`이 반영되지 않음
- “문서에 선언된 폰트”와 “실제로 렌더된 폰트 파일”은 다를 수 있음

권장:
- `font-check --font-map config.json` 지원
- `RhwpEngine` 해상 결과 기준 리포트 제공
- 아래 항목을 함께 출력:
  - declared font
  - resolved font file
  - fallback 여부
  - missing alias 여부

---

## 중간 우려 사항

### 5. MCP 서버에서 `sys.path` 조작과 프로젝트 루트 의존이 보임
위치: `mcp_server/server.py`

문제:
- 설치형 패키지보다는 개발 환경 구조에 기대는 형태
- import 경로 오염 가능
- 외부 디렉터리 구조 변경 시 깨질 위험

권장:
- 패키지 내부 리소스만 사용하도록 정리
- 프로젝트 루트 의존 import 제거
- preview 관련 코드도 내부 모듈 기준으로 재정리

---

### 6. `except Exception` 범위가 넓은 곳이 많음
대상 예:
- `api.py`
- `html_to_hwpx.py`
- `html_converter.py`
- `hwp2hwpx.py`
- `rhwp_bridge.py`

문제:
- 실제 버그가 fallback 동작처럼 보일 수 있음
- 원인 파악이 어려워짐
- 사용자는 왜 결과가 이상한지 알기 어려움

권장:
- 예외 범위 좁히기
- `debug=True` 옵션에서 상세 원인 출력
- 사용자용 예외와 내부 예외를 분리

---

### 7. `builder.py`에 legacy / dead code가 일부 남아 있음
예:
- `_build_header_legacy`
- `_build_section` 관련 구형 흐름

문제:
- 현재 구조 이해를 방해함
- 유지보수 비용 증가
- 신규 기여자가 혼란을 겪기 쉬움

권장:
- 제거
- 또는 `legacy_builder.py`로 분리
- deprecated 주석/문서화 추가

---

## 사소하지만 개선 가치가 큰 항목

### 8. `save()` 내부 import가 많은 편
문제:
- 가독성 저하
- 에러가 늦게 터짐
- 정적 분석이 불리함

권장:
- 가능한 import는 모듈 상단 또는 별도 adapter 계층으로 이동

---

### 9. 일부 import 후 미사용 흔적 정리 필요
예:
- `api_add_styled` 같은 미사용 import

문제:
- 코드 신뢰도 하락
- 읽는 사람에게 혼란

권장:
- lint 기반 정리
- 사용하지 않는 import 제거

---

### 10. CLI에 `--json` 출력 옵션이 있으면 자동화성이 크게 좋아짐
현재:
- 사람에게는 친절한 출력
- 자동화/LLM/MCP 관점에서는 구조화된 출력이 부족함

권장 대상:
- `validate`
- `font-check`
- `themes list`
- `info`

권장:
- `--json` 옵션 추가
- 안정적인 machine-readable schema 제공

---

## 구조적으로 좋은 방향

### `RhwpEngine` 설계는 전반적으로 좋음
장점:
- wasm 위치 해석 순서가 비교적 명확함
- optional dependency 처리도 적절함
- `RhwpEngine` / `RhwpDocument` 역할 분리가 괜찮음
- `embed_fonts=True` 옵션 제공이 좋음

다만 앞으로 핵심 경쟁력이 될 부분은 다음임:
- HWPX 선언 폰트
- RHWP font_map
- SVG 렌더 폰트
- PNG rasterize 결과

이 네 단계의 **폰트 해석 일치성**을 어떻게 높일지가 중요함.

---

## 권장 로드맵

### 1순위
1. `builder.save()`의 `sys.path.insert()` 제거
2. `add_image_from_url()` 안전성 강화
3. `validate`를 `validate + lint`로 분리
4. `font-check`를 resolved font 기준으로 강화

### 2순위
5. MCP 서버의 루트 의존 제거
6. broad exception 줄이기
7. legacy 코드 정리
8. CLI `--json` 지원

---

## 한 줄 결론

`pyhwpxlib`는 **매우 가능성이 큰 라이브러리**이고 방향도 맞습니다.  
다만 지금 단계에서 한 번 더 다듬어야 할 핵심은 다음입니다.

- 전역 상태 오염 제거
- 다운로드/임시파일 처리 안전성
- validate의 의미 강화
- 폰트 해석 일관성 개선

이 네 가지를 정리하면 “잘 되는 라이브러리”를 넘어 **신뢰할 수 있는 배포형 라이브러리**로 한 단계 올라갈 수 있습니다.
