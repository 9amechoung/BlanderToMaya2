# BlenderToMaya — Maya Mode for Blender

블렌더를 **거의 마야처럼** 쓰게 만드는 프로젝트입니다.

1. **분석** — 설치된 Maya 2025의 구조, 핫키, 마킹 메뉴, 메뉴, 채널 박스를 해부 → [docs/01-maya-anatomy.md](docs/01-maya-anatomy.md)
2. **애드온** — 분석 결과를 블렌더 애드온 `Maya Mode`로 구현 → [`addon/maya_mode`](addon/maya_mode)
3. **패치 계획** — 애드온으로 불가능한 부분(Transform 피벗 스택, Construction History, Y-up 등)의 블렌더 C++ 패치 로드맵 → [docs/02-gap-and-patch-plan.md](docs/02-gap-and-patch-plan.md)

지원: Blender **4.2 이상** (4.5, 5.0에서 테스트)

## 설치

1. 직접 빌드:
   ```
   blender --command extension build --source-dir addon/maya_mode --output-dir dist
   ```
2. Blender → Edit → Preferences → Get Extensions → 우측 상단 ▾ → **Install from Disk…** → `dist/maya_mode-0.1.0.zip` 선택
3. 상단 메뉴바의 **Maya → Apply Maya Setup** 실행
   - Industry Compatible 키맵(Alt+마우스 내비게이션, QWER) 활성화
   - 단위 cm, 24 fps / 1–120 프레임, 마야식 내비게이션·뷰포트

## 무엇이 마야처럼 바뀌나

### 마킹 메뉴 (파이 메뉴, 방향은 마야 기본값과 동일)
| 입력 | 메뉴 |
|---|---|
| RMB (오브젝트 위) | ↑Edge ←Vertex ↓Face →UV ↗Object Mode ↘Multi |
| RMB (빈 곳) | 선택 명령 |
| Shift+RMB (빈 곳) | 프리미티브 생성 (↓Cube →Sphere ←Cylinder ↙Cone ↖Plane ↗Disc ↘Torus) |
| Shift+RMB (오브젝트 / 버텍스 / 엣지 / 페이스) | 컴포넌트별 모델링 툴 (↓Extrude →Bevel/Chamfer ←Multi-Cut …) |
| Ctrl+RMB (컴포넌트) | 선택 변환 (To Vertices / Edges / Faces, Grow, Shrink, Loop, Ring) |
| W / E / R + LMB | 축 방향 (World / Object / Local / Normal / Gimbal), 피벗 |
| Q + LMB | 선택 방식 (Marquee / Drag / Paint / Lasso) |
| Space 홀드 | 핫박스 (Views, Selection Mode, Display, Panels, File, Edit, Mesh, Edit Mesh) |

### 핫키 요약
| 키 | 동작 |
|---|---|
| Space 탭 | 단일 ⇄ 4분할 뷰 |
| 1 / 2 / 3, PgUp / PgDn | Smooth Mesh Preview |
| 4 / 5 / 6 / 7 | 와이어 / 셰이디드 / 텍스처 / 라이트 |
| F8, F9–F12, F7 | 오브젝트⇄컴포넌트, 버텍스/엣지/페이스/UV, 멀티 |
| X / C / V (홀드) | 그리드 / 엣지 / 포인트 스냅 |
| D (홀드), Insert | 피벗 편집 |
| B, B+LMB 드래그 | 소프트 셀렉션, 반경 |
| Ctrl+G, P, Shift+P | 그룹, 페어런트, 언페어런트 |
| Ctrl+D, Shift+D | 복제, Duplicate with Transform |
| H, Ctrl+H, Alt+H, Ctrl+Shift+H | 가시성 |
| ↑ ↓ ← → | Pick-walk |
| Ctrl+E, Ctrl+B, Delete, Ctrl+Delete | Extrude, Bevel, 컴포넌트 삭제 |
| Ctrl+Shift+X, Ctrl+Shift+Q | Multi-Cut, Quad Draw |
| > / < | 선택 확장 / 축소 |
| S, Shift+W/E/R | 키 설정 |
| , . / Alt+, . / Alt+V / K+드래그 | 키 이동 / 프레임 이동 / 재생 / 스크럽 |
| + / - | 조작기 크기 |
| Ctrl+A | 채널 박스 토글 |
| G | 마지막 동작 반복 |

전체 표와 마야 원본 동작 비교는 [docs/01-maya-anatomy.md](docs/01-maya-anatomy.md) 5장 참고.

### 패널 / 메뉴
- **Channel Box / Layer Editor** — 3D 뷰 사이드바 `Channels` 탭 (Translate/Rotate/Scale, SHAPES, INPUTS=모디파이어 스택)
- **Maya 메뉴** — 상단 바: Modify(Freeze/Reset/Center Pivot/Delete History), Display, Mesh, Edit Mesh, Mesh Tools

마킹 메뉴(RMB)와 핫박스(Space)는 애드온 환경설정에서 끌 수 있습니다.

## 프로젝트 구조

```
addon/maya_mode/
  __init__.py        등록
  keymap.py          마야 기본 핫키 → 블렌더 키맵 (181개 항목)
  pies.py            마킹 메뉴 / 핫박스 (파이 메뉴)
  ops_transform.py   그룹, 복제, 홀드 스냅·피벗, 소프트 셀렉션, pick-walk, 가시성
  ops_tools.py       스무스 프리뷰, 셰이딩, 컴포넌트 모드, 모델링·Modify 명령, 키프레임, 핫박스
  channel_box.py     채널 박스 / 레이어 에디터
  menus.py           Maya 상단 메뉴
  prefs.py           환경설정, Apply Maya Setup
docs/                분석 · 갭 · 패치 계획
tests/test_addon.py  블렌더 백그라운드 테스트
```

## 테스트

```
blender --background --factory-startup --python tests/test_addon.py
```
오퍼레이터 동작(그룹, Shift+D, 스무스 프리뷰, 선택 변환, 히스토리 삭제 등)과, 모든 메뉴·파이·키맵이 참조하는 오퍼레이터/속성/열거값/아이콘이 실제로 존재하는지 검증합니다.

## 법적 고지

- 이 저장소에는 Autodesk의 코드, 스크립트, 아이콘, 리소스가 포함되어 있지 않습니다. 분석 문서는 설치된 Maya의 동작을 관찰해 직접 작성한 설명이며, 바이너리는 디컴파일하지 않았습니다.
- Maya는 Autodesk, Inc.의 상표입니다. 이 프로젝트는 Autodesk와 관련이 없습니다.
- 라이선스: GPL-3.0-or-later (블렌더 애드온 요구사항)
