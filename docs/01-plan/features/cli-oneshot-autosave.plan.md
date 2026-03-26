# Plan: cli-oneshot-autosave

## 1. 문제 정의

**현상**: `cli-anything-hwpx --file doc.hwpx text add "내용"` 실행 시 "Added paragraph" 메시지는 출력되지만, 실제 파일에 변경사항이 저장되지 않음.

**원인**: CLI가 one-shot 모드(매 호출마다 새 프로세스)로 실행될 때:
1. `--file`로 문서를 열고 → 메모리에 텍스트 추가
2. 하지만 **변경된 문서를 파일에 다시 저장하지 않고** 프로세스가 종료됨
3. 다음 호출에서 다시 원본 파일을 열기 때문에 이전 변경이 모두 유실

**REPL 모드에서는 정상**: 세션이 유지되므로 메모리 내 문서 객체가 살아있음.

## 2. 영향 범위

`--file` 모드에서 문서를 변경(mutation)하는 모든 명령어:

| 명령어 | 변경 여부 |
|--------|:---------:|
| `text add` | O |
| `text replace` | O |
| `table add` | O |
| `image add` | O |
| `image remove` | O |
| `structure add-section` | O |
| `structure set-header` | O |
| `structure set-footer` | O |
| `structure bookmark` | O |
| `structure hyperlink` | O |
| `text extract` | X (읽기 전용) |
| `text find` | X (읽기 전용) |
| `document info` | X (읽기 전용) |
| `export *` | X (별도 파일 출력) |
| `validate *` | X (읽기 전용) |

## 3. 해결 방안

### 방안 A: 변경 명령어 실행 후 자동 저장 (채택)

`--file`로 열었을 때, mutation 명령 완료 후 원본 파일에 자동으로 `save_to_path()` 호출.

- 장점: 기존 CLI 사용법 변경 없음, 직관적
- 단점: 의도치 않은 덮어쓰기 가능 (undo 불가)
- 대응: `--dry-run` 옵션으로 미리보기 가능하게 (향후)

### 방안 B: 명시적 save 필요 (기각)

매번 `cli-anything-hwpx --file doc.hwpx document save` 호출 요구.

- 기각 사유: one-shot 모드에서 세션이 유지 안 되므로 의미 없음

## 4. 구현 계획

### 4.1 `hwpx_cli.py` 수정

1. `cli()` 함수에서 `--file`로 열린 경로를 Click context에 저장
2. 변경 명령어들에 자동 저장 로직 추가 (공통 데코레이터 or 직접)

### 4.2 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `hwpx/agent-harness/cli_anything/hwpx/hwpx_cli.py` | `--file` 경로를 ctx.obj에 저장, mutation 명령 후 auto-save |

### 4.3 테스트 계획

```bash
# 1. python-hwpx 직접 (기존 정상 — baseline)
python3 -c "from hwpx import HwpxDocument; ..."

# 2. cli-anything-hwpx one-shot 모드 (수정 후)
cli-anything-hwpx document new --output test.hwpx
cli-anything-hwpx --file test.hwpx text add "첫 번째 문단"
cli-anything-hwpx --file test.hwpx text add "두 번째 문단"
cli-anything-hwpx --file test.hwpx text extract
# 기대: "첫 번째 문단\n두 번째 문단" 출력

# 3. 읽기 전용 명령은 저장 안 함 확인
cli-anything-hwpx --file test.hwpx text find "문단"
# 기대: 파일 수정 시간 변경 없음
```

## 5. 완료 기준

- [ ] `--file` 모드에서 `text add` 후 파일에 내용이 저장됨
- [ ] 연속 `text add` 호출 시 내용이 누적됨
- [ ] 읽기 전용 명령은 파일을 수정하지 않음
- [ ] REPL 모드 동작에 영향 없음
