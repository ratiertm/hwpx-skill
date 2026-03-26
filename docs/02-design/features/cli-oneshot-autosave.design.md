# Design: cli-oneshot-autosave

> Plan 참조: `docs/01-plan/features/cli-oneshot-autosave.plan.md`

## 1. 현재 코드 흐름 (Before)

```
사용자: cli-anything-hwpx --file doc.hwpx text add "내용"
  │
  ▼
cli() — --file로 문서 열기 → Session에 doc 저장
  │
  ▼
text_add() — sess.snapshot() → doc.add_paragraph("내용") → output()
  │
  ▼
프로세스 종료 — 파일에 저장 안 됨 ❌
```

## 2. 수정 후 코드 흐름 (After)

```
사용자: cli-anything-hwpx --file doc.hwpx text add "내용"
  │
  ▼
cli() — --file로 문서 열기 → Session에 doc 저장
      → ctx.obj["auto_save_path"] = file_path  ← 추가
  │
  ▼
text_add() — sess.snapshot() → doc.add_paragraph("내용")
           → auto_save(sess, ctx)  ← 추가
           → output()
  │
  ▼
프로세스 종료 — 파일에 저장됨 ✅
```

## 3. 상세 설계

### 3.1 수정 파일

`hwpx/agent-harness/cli_anything/hwpx/hwpx_cli.py` — 1개 파일만 수정

### 3.2 변경사항 A: cli() 함수 — auto_save_path 저장

```python
# 변경 전 (line 106-121)
def cli(ctx, use_json, file_path):
    global _json_output
    _json_output = use_json

    if file_path:
        sess = get_session()
        if not sess.has_project():
            doc = doc_mod.open_document(file_path)
            sess.set_doc(doc, file_path)

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)

# 변경 후
def cli(ctx, use_json, file_path):
    global _json_output
    _json_output = use_json
    ctx.ensure_object(dict)
    ctx.obj["auto_save_path"] = None          # ← 추가

    if file_path:
        sess = get_session()
        if not sess.has_project():
            doc = doc_mod.open_document(file_path)
            sess.set_doc(doc, file_path)
        ctx.obj["auto_save_path"] = file_path  # ← 추가

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)
```

### 3.3 변경사항 B: auto_save 헬퍼 함수 추가

```python
def _auto_save_if_needed():
    """--file 모드에서 mutation 후 자동 저장."""
    ctx = click.get_current_context(silent=True)
    if ctx is None:
        return
    # 부모 context에서 auto_save_path 탐색
    root = ctx.find_root()
    path = root.obj.get("auto_save_path") if root.obj else None
    if path and not _repl_mode:
        sess = get_session()
        sess.save(path)
```

### 3.4 변경사항 C: mutation 명령어에 auto_save 호출 추가

10개 mutation 명령에 `_auto_save_if_needed()` 한 줄 추가:

| 명령어 | 함수명 | 삽입 위치 |
|--------|--------|-----------|
| `text add` | `text_add()` | output() 호출 직전 |
| `text replace` | `text_replace()` | output() 호출 직전 |
| `table add` | `table_add()` | output() 호출 직전 |
| `image add` | `image_add()` | output() 호출 직전 |
| `image remove` | `image_remove()` | output() 호출 직전 |
| `structure add-section` | `structure_add_section()` | output() 호출 직전 |
| `structure set-header` | `structure_set_header()` | output() 호출 직전 |
| `structure set-footer` | `structure_set_footer()` | output() 호출 직전 |
| `structure bookmark` | `structure_bookmark()` | output() 호출 직전 |
| `structure hyperlink` | `structure_hyperlink()` | output() 호출 직전 |

예시 (text_add):
```python
# 변경 전
def text_add(content):
    sess = get_session()
    sess.snapshot()
    result = text_mod.add_paragraph(sess.get_doc(), content)
    globals()["output"](result, f"Added paragraph: {content[:50]}...")

# 변경 후
def text_add(content):
    sess = get_session()
    sess.snapshot()
    result = text_mod.add_paragraph(sess.get_doc(), content)
    _auto_save_if_needed()                    # ← 추가
    globals()["output"](result, f"Added paragraph: {content[:50]}...")
```

## 4. REPL 모드 보호

`_auto_save_if_needed()`에 `not _repl_mode` 조건이 있으므로:
- **one-shot 모드**: `--file` + mutation → 자동 저장
- **REPL 모드**: 기존대로 명시적 `document save`만 저장

## 5. 구현 순서

1. `_auto_save_if_needed()` 함수 추가
2. `cli()` 함수에 `ctx.ensure_object(dict)` + `auto_save_path` 저장
3. 10개 mutation 명령에 `_auto_save_if_needed()` 호출 추가
4. 테스트 실행

## 6. 테스트 시나리오

| # | 시나리오 | 기대 결과 |
|---|---------|-----------|
| T1 | `text add` 1회 후 `text extract` | 추가한 텍스트 출력 |
| T2 | `text add` 3회 연속 후 `text extract` | 3개 문단 모두 출력 |
| T3 | `text replace` 후 `text extract` | 치환된 텍스트 출력 |
| T4 | `table add` 후 `table list` | 표 1개 출력 |
| T5 | `text find` 실행 후 파일 mtime 확인 | mtime 변경 없음 |
| T6 | REPL 모드에서 `text add` 후 `text extract` | 기존대로 동작 (save 전에는 파일 변경 없음) |
