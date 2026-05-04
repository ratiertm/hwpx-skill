## Skill RULE

너는 일회성 작업을 할 권한이 없다. 내가 시킨 일이 다시 일어날 종류의 일이라면 다음을 해야 한다:
- 처음에는 3~10개 항목에 대해 수동으로 한다
- 결과를 나에게 보여준다
- 내가 승인하면 → 스킬 파일로 코드화한다
- 자동 실행이어야 하면 → 크론에 올린다
- 테스트: 내가 같은 걸 두 번 시켜야 한다면, 너는 실패한 것이다.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## Release checklist (every PyPI publish)

The project ships a built-in LLM guide string (`pyhwpxlib.llm_guide.GUIDE`)
that the MCP `hwpx_guide()` tool returns. Past releases (0.10.0 → 0.16.x)
let this string drift 6 versions behind reality, leaving every Claude
Code / external orchestration client with stale instructions until the
0.17.2 catch-up. Don't repeat that.

For every PyPI release, in this order, check:

1. **`pyproject.toml` and `pyhwpxlib/__init__.py` versions match** (rule
   from memory `feedback_version_sync.md`).
2. **`CHANGELOG.md`** has an entry for the new version.
3. **`pyhwpxlib/llm_guide.py`**:
   - Header `# pyhwpxlib vX.Y.Z — LLM Quick Reference Guide` line bumped.
   - Version-history table at the bottom has the new row.
   - **If the release adds / changes a public API, CLI subcommand, or
     MCP tool, update the relevant section in the GUIDE body too.**
     This is the rule that 0.10.0 → 0.16.x violated; one line in the
     version-history row is not enough when behavior changed.
4. **`skill/SKILL.md`** Versions table has the new row (resolver-side
   discoverability).
5. **`skill/hwpx-skill-X.Y.Z.zip`** rebuilt with current sources, and
   contains exactly **one** `SKILL.md` file (Claude Code packager
   constraint — sub-skill workflow docs must be `WORKFLOW.md` /
   `references/*.md`, never `SKILL.md`).
6. `python -m build` + `twine check dist/*` + `twine upload`.
7. `git tag vX.Y.Z` + `git push origin main vX.Y.Z`.
8. `update_skill.py push` → `~/.claude/skills/hwpx/` is in sync.

Default `update_skill.py` SYNC_FILES list: keep `skill/hwpx-form/WORKFLOW.md`
and `skill/references/rich_document_example.md` in it (these were
silently missing for several releases — see commits `2cf3997`, `7b540c6`).
