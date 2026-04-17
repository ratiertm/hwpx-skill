# pyhwpxlib v0.5 — 테마 시스템 + JSON 라운드트립 + 동적 테마 추출

## Vision

pyhwpxlib을 "모든 한글 문서가 같은 느낌" 상태에서 "주제·양식에 맞는 다양한 문서" 생성이 가능한 라이브러리로 업그레이드한다.

## Problem Statement

현재 pyhwpxlib은:
- **색상**: Administrative Slate(파란색) 1개 하드코딩. design_guide.md에 10종 팔레트 정의했으나 코드 미연결
- **폰트**: 함초롬돋움 1개 하드코딩. 제목/본문/캡션 구분 없음
- **사이즈**: 제목 24/18/16/14pt, 본문 10pt 고정
- **JSON 라운드트립**: encoder가 이미지/중첩표/스타일 무시, decoder가 서식 전부 소실
- **BinData**: HWP→HWPX 변환 시 일부 파일의 이미지 압축 해제 실패 → 크래시

## Goals

1. **테마 시스템**: `HwpxBuilder(theme='forest')` 한 줄로 팔레트+폰트+사이즈+여백 통합 적용
2. **동적 테마 추출**: 사용자가 양식을 업로드하면 해당 문서의 색상/폰트/사이즈를 분석하여 커스텀 테마로 저장
3. **JSON Overlay 완성**: 원본 서식 100% 보존하면서 텍스트만 교체. `<hp:t>` 단위 정밀 매칭
4. **BinData 에러 핸들링**: 압축 해제 실패 시 스킵 + 경고 (크래시 방지)
5. **기술 부채 해소**: 과대표현된 기능(JSON round-trip "완성" 등) 실제 수준으로 정비

## Target Users

- Claude Desktop/AI 사용자 (pip install pyhwpxlib로 사용)
- 한국 공무원/변호사/회계사 (양식 자동화)
- LLM 기반 문서 생성 시스템 개발자

## Technical Context

- Python 3.8+ / PyPI 배포 (v0.4.0 현재)
- rhwp WASM → SVG 프리뷰 (wasmtime + resvg_py)
- FastMCP 기반 MCP 서버 (stdio + HTTP/SSE)
- Oracle Cloud VM에 Remote MCP 배포 완료

## Success Criteria

- [ ] `HwpxBuilder(theme='forest')` 동작 — 10종 내장 테마
- [ ] `extract_theme(hwpx_path)` → 커스텀 테마 JSON 생성
- [ ] `extract_overlay` + `apply_overlay` → `<hp:t>` 단위 정밀 교체
- [ ] HWP→HWPX 변환 시 BinData 실패해도 크래시 없음
- [ ] 기존 테스트 전부 통과 + 새 테스트 추가
