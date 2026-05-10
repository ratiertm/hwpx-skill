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

## 2. PolyForm Noncommercial License 1.0.0 적용 파일

위에 명시된 파일을 **제외한 모든 파일**에 PolyForm Noncommercial 1.0.0이 적용됩니다.

**Licensor:** Eunmi Lee (ratiertm)
**Licensed Work:** pyhwpxlib
**Copyright:** (c) 2026 Eunmi Lee

### 한 줄 요약

- **개인·비상업 용도: 무료** (소스 자유 열람, 수정, 재배포 가능)
- **상업 용도: 별도 라이선스 필요** — 한 명이든 백 명이든 영리 활동에 쓰면 유료
- 상업 라이선스 문의: https://lchfkorea.com

### Permitted Uses (무료)

다음 용도는 **noncommercial use** 로 간주되어 무료입니다.

1. 개인 사용 (자기 양식·문서 작성)
2. 학술·교육 목적 (수업, 연구, 논문)
3. 비영리 단체 활동 (자선, 시민사회, 종교)
4. 오픈소스 프로젝트의 의존성 (그 프로젝트 자체가 noncommercial 일 때)
5. 평가·테스트 (도입 검토 단계)

### Commercial License Required (유료)

다음 중 **하나라도 해당**하면 상업 라이선스가 필요합니다.

1. 영리 회사·법인의 업무 자동화 (인원 수 무관)
2. 프리랜서·자영업자가 고객 작업물에 사용
3. 제3자 제공 서비스의 구성요소 (SaaS, API, 플러그인)
4. 상업 제품에 포함 배포
5. 컨설팅·용역 결과물 생성에 사용
6. 라이선스 검증 메커니즘 제거 또는 우회

### Source Visibility

소스 공개는 라이선스 의무가 아닌 **저작권자의 자발적 결정**입니다. 이 저장소의 모든 코드는 누구나
열람·복제·수정 가능하지만, 위 "Commercial License Required" 조건에 해당하면 별도 라이선스 계약
체결 후에만 사용·재배포할 수 있습니다.

### Inheritance & Continuity

본 라이선스는 저작권자의 자연인 사망 후에도 유효하며, 저작권은 한국 민법에 따라 상속됩니다.
상속인은 동일한 조건으로 상업 라이선스 grant 권한을 가집니다. 저작권을 법인에 양도한 경우
법인의 자산으로 처리됩니다.

### Full License Text

전체 라이선스 본문: https://polyformproject.org/licenses/noncommercial/1.0.0/

> 본 README 의 한국어 요약과 영문 본문이 충돌할 경우 영문 본문이 우선합니다.

### General

본 라이선스를 위반하는 사용은 현재 및 모든 버전에 대한 권리를 자동으로 종료시킵니다.
종료 후 사용을 계속하려면 라이선서로부터 상업 라이선스를 구매해야 합니다.

TO THE EXTENT PERMITTED BY APPLICABLE LAW, THE LICENSED WORK IS
PROVIDED ON AN "AS IS" BASIS. LICENSOR HEREBY DISCLAIMS ALL
WARRANTIES AND CONDITIONS, EXPRESS OR IMPLIED, INCLUDING (WITHOUT
LIMITATION) WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE, NON-INFRINGEMENT, AND TITLE.

---

## 3. License Migration Note (2026-05)

본 저장소는 **0.18.1 까지 BSL 1.1 (Business Source License) 로 배포**되었으며,
**0.19.0 부터 PolyForm Noncommercial 1.0.0 으로 전환**되었습니다.

PyPI 에 이미 배포된 0.18.1 이하 버전은 배포 시점의 BSL 1.1 조건이 그대로 유지됩니다
(소급 변경 불가). 신규 다운로드 / 신규 사용은 본 LICENSE.md 의 PolyForm Noncommercial
조건을 따릅니다.

기존 BSL 1.1 의 "Rolling Change Date 4년 후 Apache 2.0 자동 전환" 조항은 PolyForm
전환 후 폐기되었습니다. PolyForm Noncommercial 은 Change Date 를 두지 않으며 영구적으로
noncommercial 라이선스로 유지됩니다.
