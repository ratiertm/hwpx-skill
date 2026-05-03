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
