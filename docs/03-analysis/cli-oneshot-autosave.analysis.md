# Analysis: cli-oneshot-autosave

> Gap Analysis — Design vs Implementation
> Date: 2026-03-26

## Match Rate: 93%

```
+---------------------------------------------+
|  Overall Match Rate: 93%                     |
+---------------------------------------------+
|  Functional Match:    5/5 requirements (100%)|
|  Mechanism Match:     3/5 items (60%)        |
|  Mutation Coverage:   10/10 commands (100%)  |
|  Read-only Protected: 9/9 commands (100%)    |
+---------------------------------------------+
```

## Gap 상세

### 구현 방식 차이 (기능 동일, 메커니즘 변경)

| Design | Implementation | 영향도 |
|--------|----------------|--------|
| Click Context (`ctx.obj`) | Module global (`_auto_save_path`) | Low |
| `click.get_current_context()` + `ctx.find_root()` 6줄 | global 변수 직접 참조 2줄 | Low |
| `ctx.ensure_object(dict)` 호출 | 불필요하여 생략 | None |

**판정**: 기존 코드베이스가 이미 global 패턴(`_json_output`, `_repl_mode`, `_session`)을 사용하므로, 구현이 더 일관적이고 단순함. Design 문서를 구현에 맞게 업데이트 권장.

### 완전 일치 항목

- 10/10 mutation 명령에 `_auto_save_if_needed()` 호출 삽입
- 9/9 읽기 전용 명령에 auto_save 호출 없음
- REPL 모드 보호 (`not _repl_mode` 조건)
- `sess.save(path)` 호출로 파일 저장

## 테스트 결과

| # | 시나리오 | 결과 |
|---|---------|------|
| T1 | text add 1회 후 extract | PASS |
| T2 | text add 3회 연속 누적 | PASS |
| T3 | text replace 후 extract | PASS |
| T5 | 읽기 전용 명령 mtime 미변경 | PASS |

## 결론

Match Rate 93% >= 90% 기준 충족. 완료 보고서 생성 가능.
