---
description: hwpx 스킬을 GitHub에서 최신 버전으로 업그레이드 (백업 + diff 프리뷰 포함)
---

# /hwpx-update — hwpx 스킬 GitHub 업그레이드

사용자가 `/hwpx-update`를 입력했을 때 다음을 수행한다.

## 동작

1. `~/.claude/skills/hwpx/scripts/update_skill.py upgrade` 실행
   - GitHub `ratiertm/hwpx-skill@main`에서 SYNC_FILES 다운로드
   - 자동 백업 → `~/.claude/skill_backups/hwpx/{TIMESTAMP}/`
   - diff 프리뷰 출력
   - `--yes` 플래그가 인자로 전달되면 확인 없이 즉시 적용
2. 결과 보고:
   - 업데이트된 파일 목록
   - 백업 위치
   - 롤백 명령 (필요 시)

## 인자 처리

`$ARGUMENTS`에 다음 옵션이 올 수 있다:
- `--yes` / `-y` — 확인 프롬프트 건너뛰기
- `--ref TAG` — 특정 태그/브랜치 (예: `--ref v0.10.0`)
- `--repo USER/REPO` — fork에서 가져오기

기본값: `main` 브랜치, 대화형 확인.

## 실행

```bash
python3 ~/.claude/skills/hwpx/scripts/update_skill.py upgrade $ARGUMENTS
```

## 예시 사용

| 입력 | 의미 |
|---|---|
| `/hwpx-update` | main 브랜치 최신, 대화형 확인 |
| `/hwpx-update --yes` | 확인 없이 즉시 적용 |
| `/hwpx-update --ref v0.10.0` | v0.10.0 태그 |
| `/hwpx-update --repo myuser/fork` | fork 레포 |

## 주의

- 사용자 수정사항은 백업으로 보존됨
- 백업 위치는 `~/.claude/skill_backups/hwpx/` (스킬 디렉토리 밖, 자동 등록 방지)
- 실패 시 백업에서 복원 명령을 출력
