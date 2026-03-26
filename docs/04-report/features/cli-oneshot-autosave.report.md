# Completion Report: cli-oneshot-autosave

> PDCA Cycle Complete
> Date: 2026-03-26

## Summary

| 항목 | 내용 |
|------|------|
| Feature | cli-oneshot-autosave |
| 문제 | `--file` 모드에서 mutation 명령 후 변경사항이 파일에 저장되지 않음 |
| 해결 | `_auto_save_if_needed()` 헬퍼 + 10개 mutation 명령에 자동 저장 적용 |
| Match Rate | **93%** |
| 수정 파일 | 1개 (`hwpx_cli.py`) |
| 반복 횟수 | 0회 (첫 구현에서 통과) |

## PDCA 흐름

```
[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ (93%) → [Report] ✅
```

## 1. Plan

**문제**: `cli-anything-hwpx --file doc.hwpx text add "내용"` 실행 시 메모리에만 추가되고 파일에 저장되지 않음. CLI가 one-shot 모드(매 호출마다 새 프로세스)로 실행되기 때문.

**채택 방안**: mutation 명령 실행 후 `--file`로 열린 파일에 자동 저장.

**문서**: `docs/01-plan/features/cli-oneshot-autosave.plan.md`

## 2. Design

3가지 변경 설계:

| 변경 | 내용 |
|------|------|
| A | `cli()` 함수에 `_auto_save_path` 저장 |
| B | `_auto_save_if_needed()` 헬퍼 함수 추가 |
| C | 10개 mutation 명령에 auto_save 호출 1줄씩 추가 |

REPL 모드 보호: `not _repl_mode` 조건으로 REPL에서는 자동 저장 차단.

**문서**: `docs/02-design/features/cli-oneshot-autosave.design.md`

## 3. Do (구현)

수정 파일: `hwpx/agent-harness/cli_anything/hwpx/hwpx_cli.py`

추가된 코드:

```python
# Global 변수
_auto_save_path: Optional[str] = None

# 헬퍼 함수
def _auto_save_if_needed():
    """One-shot 모드(--file)에서 mutation 후 자동 저장."""
    if _auto_save_path and not _repl_mode:
        sess = get_session()
        sess.save(_auto_save_path)

# cli() 함수에 추가
global _json_output, _auto_save_path
# ...
_auto_save_path = file_path

# 10개 mutation 명령에 각각 1줄 추가
_auto_save_if_needed()
```

적용 명령어: `text add`, `text replace`, `table add`, `image add`, `image remove`, `structure add-section`, `structure set-header`, `structure set-footer`, `structure bookmark`, `structure hyperlink`

## 4. Check (Gap 분석)

| 항목 | 점수 |
|------|:----:|
| 기능적 일치 | 5/5 (100%) |
| Mutation 커버리지 | 10/10 (100%) |
| 읽기 전용 보호 | 9/9 (100%) |
| 구현 방식 일치 | 3/5 (60%) |
| **전체 Match Rate** | **93%** |

**차이점**: Design은 Click Context(`ctx.obj`)를, 구현은 global 변수를 사용. 기존 코드 패턴(`_json_output`, `_repl_mode`)과 일관성을 유지한 의도적 단순화.

**문서**: `docs/03-analysis/cli-oneshot-autosave.analysis.md`

## 5. 테스트 결과

| # | 시나리오 | 결과 |
|---|---------|:----:|
| T1 | `text add` 1회 후 `text extract` | PASS |
| T2 | `text add` 3회 연속 누적 확인 | PASS |
| T3 | `text replace` 후 치환 확인 | PASS |
| T5 | `text find` 후 파일 mtime 미변경 | PASS |

### Before / After

**Before**:
```bash
cli-anything-hwpx --file doc.hwpx text add "내용"
cli-anything-hwpx --file doc.hwpx text extract
# 출력: (비어있음)
```

**After**:
```bash
cli-anything-hwpx --file doc.hwpx text add "내용"
cli-anything-hwpx --file doc.hwpx text extract
# 출력: 내용
```

## 6. PDCA 문서 목록

| Phase | 문서 |
|-------|------|
| Plan | `docs/01-plan/features/cli-oneshot-autosave.plan.md` |
| Design | `docs/02-design/features/cli-oneshot-autosave.design.md` |
| Analysis | `docs/03-analysis/cli-oneshot-autosave.analysis.md` |
| Report | `docs/04-report/features/cli-oneshot-autosave.report.md` |
