# pyhwpxlib License

이 프로젝트는 **파일별로 다른 라이선스**가 적용됩니다.

---

## 1. Apache License 2.0 적용 파일

다음 파일은 원본 오픈소스의 파생 저작물이므로 Apache License 2.0이 적용됩니다.
상업적 사용을 포함한 모든 사용이 자유롭습니다.

| 파일 | 원본 |
|------|------|
| `pyhwpxlib/hwp2hwpx.py` | [neolord0/hwp2hwpx](https://github.com/neolord0/hwp2hwpx) |
| `pyhwpxlib/hwp_reader.py` | [neolord0/hwplib](https://github.com/neolord0/hwplib) |
| `pyhwpxlib/value_convertor.py` | [neolord0/hwp2hwpx](https://github.com/neolord0/hwp2hwpx) |

전체 라이선스 텍스트: [LICENSE-APACHE](LICENSE-APACHE)

---

## 2. Business Source License 1.1 적용 파일

위에 명시된 파일을 **제외한 모든 파일**에 BSL 1.1이 적용됩니다.

**Licensor:** Eunmi Lee (ratiertm)
**Licensed Work:** pyhwpxlib
**Copyright:** (c) 2026 Eunmi Lee

**Change License:** Apache License, Version 2.0

### Rolling Change Date

각 릴리스 버전은 **자체 Change Date** 를 가지며, 그 값은 **해당 버전의 릴리스일 + 4년** 으로
설정됩니다. 즉 새 버전이 나올 때마다 Change Date 가 자동으로 4년 뒤로 갱신됩니다 (HashiCorp,
Sentry 와 동일한 Rolling 패턴). 이전 버전은 자신의 Change Date 가 도래하면 자동으로
Apache 2.0 으로 전환됩니다.

<!-- ROLLING_TABLE_START -->
| 버전 | 릴리스일 | Change Date |
|------|---------|------------|
| 0.15.0 | 2026-04-29 | 2030-04-29 |
| 0.16.0 | 2026-05-01 | 2030-05-01 |
| 0.16.1 (current) | 2026-05-01 | 2030-05-01 |
<!-- ROLLING_TABLE_END -->

> 매 릴리스 시 `python scripts/update_license_date.py` 로 위 표가 자동 갱신됩니다.

### Permitted Uses (무료)

1. 개인, 비상업적 사용
2. 사내 5인 이하 사용
3. OSI 인증 오픈소스 프로젝트에서의 사용
4. 학술, 교육 목적 사용
5. 평가 및 테스트

### Commercial License Required (유료)

1. 제3자에게 제공하는 제품/서비스의 핵심 구성요소로 사용 (SaaS, API 등)
2. 상업 제품에 포함하여 배포
3. 사내 6인 이상 사용
4. 라이선스 검증 메커니즘 제거 또는 우회

Commercial licenses: https://lchfkorea.com

### General

각 릴리스 버전의 Change Date 가 도래하면 해당 버전의 BSL 적용 파일은 자동으로 Apache
License 2.0 으로 전환됩니다. 새 버전은 항상 자신의 새로운 Change Date 를 갖습니다.

본 라이선스를 준수하지 않는 사용은 라이선서, 계열사, 또는 공인 대리점으로부터
상업 라이선스를 구매하거나 사용을 중단해야 합니다.

본 라이선스를 위반하는 사용은 현재 및 모든 버전에 대한 권리를 자동으로 종료시킵니다.

TO THE EXTENT PERMITTED BY APPLICABLE LAW, THE LICENSED WORK IS
PROVIDED ON AN "AS IS" BASIS. LICENSOR HEREBY DISCLAIMS ALL
WARRANTIES AND CONDITIONS, EXPRESS OR IMPLIED, INCLUDING (WITHOUT
LIMITATION) WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, NON-INFRINGEMENT, AND TITLE.
