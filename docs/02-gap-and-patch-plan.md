# 02. 마야 ↔ 블렌더 갭 분석 & 패치 계획

[01-maya-anatomy.md](01-maya-anatomy.md)의 분석을 바탕으로, 마야 기능 하나하나를 **애드온으로 가능한가 / 블렌더 C++ 패치가 필요한가**로 분류했습니다.

범례: ✅ 애드온에 구현됨 · ◐ 애드온으로 근사(차이 있음) · ⏳ 애드온으로 가능, 아직 미구현 · 🔧 패치 필요

## 1. 갭 매트릭스

### 조작 / 내비게이션
| 마야 기능 | 상태 | 블렌더 구현 / 비고 |
|---|---|---|
| Alt+LMB/MMB/RMB 텀블·트랙·돌리 | ✅ | Industry Compatible 키맵 (`Apply Maya Setup`) |
| QWER 툴 | ✅ | Industry Compatible |
| F / A / Shift+F / Shift+A 프레임 | ✅ | |
| Space 탭: 단일 ⇄ 4분할 뷰 | ✅ | `screen.region_quadview` |
| Space 홀드: 핫박스 | ◐ | 파이 메뉴로 근사. 풀스크린 메뉴 행 + 5구역 마킹 메뉴는 🔧 |
| 텀블 피벗 = 카메라 Center of Interest | ◐ | 블렌더 뷰 중심과 개념 동일. 카메라별 COI 속성은 🔧 |
| 뷰 변경 언두 `[` `]` | 🔧 | 블렌더에 뷰 히스토리 스택 없음 |
| persp/top/front/side 가 실제 카메라 | ◐ | 뷰 축 전환으로 근사 (`maya.set_view`) |
| Y-up | 🔧 | 아래 P1 참고. 당장은 FBX/USD 입출력 시 축 변환으로 대응 |

### 선택 / 컴포넌트
| 마야 기능 | 상태 | 비고 |
|---|---|---|
| F8 / F9–F12 / F7 | ✅ | |
| RMB 마킹 메뉴(컴포넌트), 마우스 아래 오브젝트 대상 | ✅ | 레이캐스트로 대상 결정 |
| Shift+RMB 컴포넌트별 툴 메뉴 | ✅ | Wedge·Paint Select 등은 대체 기능 |
| Ctrl+RMB 선택 변환 | ✅ | To UVs 제외 |
| > / < 확장 축소, 루프/링 | ✅ | |
| Q+LMB 선택 방식 | ✅ | |
| 소프트 셀렉션 B / B+드래그 | ✅ | proportional editing. 마야의 Volume / Surface / Global 모드 구분은 ◐ |
| 오브젝트 여러 개 동시 컴포넌트 모드 | ✅ | 블렌더 멀티 오브젝트 편집 |
| UV 컴포넌트를 3D 뷰에서 바로 선택 | 🔧 | 블렌더 UV 선택은 UV 에디터 전용 |

### 변환 / 피벗
| 마야 기능 | 상태 | 비고 |
|---|---|---|
| X/C/V 홀드 스냅 | ✅ | 홀드 중 드래그 시 키 떼기 이벤트를 transform 모달이 먹으면 스냅이 남을 수 있음 → P6 |
| D 홀드 피벗 편집 (오브젝트) | ✅ | "Affect Only Origins" |
| D 홀드 피벗 편집 (컴포넌트) | ◐ | 3D 커서를 피벗으로 사용 |
| W+LMB 축 방향 (World/Object/Local/Normal/Gimbal) | ✅ | |
| 별도 Rotate Pivot / Scale Pivot / Rotate Axis | 🔧 | P2 |
| Freeze Transformations 후 피벗 위치 유지 | 🔧 | 블렌더는 피벗=원점이라 이동값을 굽으면 원점이 월드 0으로 감 (P2로 해결) |
| Joint Orient | 🔧 | P2 |
| Shift+D Duplicate with Transform | ✅ | 채널 단위 델타 재적용 |
| Ctrl+G 그룹 (피벗 월드 원점) | ✅ | Empty 사용 |
| 조작기 크기 +/- | ✅ | |

### 모델링
| 마야 기능 | 상태 | 비고 |
|---|---|---|
| Extrude / Bevel / Bridge / Poke / Merge / Collapse / Detach / Extract | ✅ | |
| Multi-Cut, Insert Edge Loop, Quad Draw | ✅ | knife / loop cut / poly build 툴 |
| Target Weld | ⏳ | 모달 오퍼레이터로 구현 가능 |
| Smooth Mesh Preview 1/2/3 | ✅ | `MayaSmoothPreview` Subsurf 모디파이어 |
| Construction History (나중에 Extrude 값 수정) | 🔧 | P3 |
| Delete History / Non-Deformer History | ✅ | 모디파이어 적용 |
| Soften / Harden Edge | ✅ | sharp edge |

### UI
| 마야 기능 | 상태 | 비고 |
|---|---|---|
| 채널 박스 (Translate/Rotate/Scale/Visibility, SHAPES, INPUTS) | ✅ | 사이드바 "Channels" |
| 채널 이름 MMB 드래그 가상 슬라이더 | 🔧 | P5 |
| 채널 여러 개 선택 후 한 번에 값 입력 | ◐ | 블렌더 Alt+드래그/Alt+Enter로 비슷 |
| 레이어 에디터 | ✅ | 최상위 컬렉션 = 디스플레이 레이어 |
| Attribute Editor | ✅ | Properties 에디터 (`Ctrl+A`는 사이드바 토글) |
| 쉘프 | ⏳ | 사이드바 탭 + 사용자 버튼으로 구현 가능 |
| 메뉴셋 F2–F6 | ⏳ | 상단 `Maya` 메뉴를 메뉴셋별로 교체하는 방식으로 가능 |
| 마야식 UI 테마(회색 톤, 그라데이션 배경) | ◐ | 뷰포트 그라데이션만 적용. 전체 테마는 ⏳ |

### 애니메이션
| 마야 기능 | 상태 | 비고 |
|---|---|---|
| S / Shift+W/E/R 키 | ✅ | |
| , . / Alt+, . / Alt+V | ✅ | |
| K 드래그 타임 스크럽 | ✅ | |
| 타임 슬라이더 MMB 드래그 (값 유지하며 시간 이동) | ⏳ | |
| Graph Editor 마야 키맵 | ⏳ | Graph Editor keymap에 추가하면 됨 |

---

## 2. 패치 계획 (블렌더 C++)

애드온으로는 데이터 모델과 이벤트 처리의 근본적인 차이를 메울 수 없습니다. 우선순위 순:

### P1. Y-up 월드 (난이도: 최상)
- 블렌더는 Z-up이 렌더러, 물리, 지오메트리 노드, 모든 애드온에 가정되어 있음. **전역 축 변경은 비현실적.**
- 현실적 대안: *표시 계층*만 Y-up으로 — 뷰 축 단축키(Front/Top/Side), 그리드 평면, 기즈모 축 라벨, 채널 박스 표시값을 Y-up 기준으로 매핑.
  - `source/blender/editors/space_view3d/` (뷰 축 연산자), `source/blender/draw/engines/overlay/` (그리드)
- 또는 애드온 레벨에서 "입출력 시 축 변환"만 유지 (FBX/USD 익스포터 `axis_up='Y'`). **권장: 패치하지 말고 이 방식.**

### P2. 마야 Transform 스택 (난이도: 상, 효과: 최상)
- `Object`에 `rotate_pivot`, `scale_pivot`, `rotate_axis`, `joint_orient`(본) 필드 추가.
  - DNA: `source/blender/makesdna/DNA_object_types.h`
  - 행렬 계산: `source/blender/blenkernel/intern/object.cc` (`BKE_object_to_mat4` 계열)
  - RNA: `source/blender/makesrna/intern/rna_object.cc`
  - 변환 툴이 피벗을 쓰도록: `source/blender/editors/transform/`
- 이게 들어가면 Freeze Transformations, D 피벗 편집, 피벗 기준 회전 배열 같은 마야 워크플로가 전부 정확해짐.
- 하위호환: 새 필드 기본값 0 → 기존 파일 동작 동일.

### P3. Construction History (난이도: 상)
- 블렌더 4.x+의 지오메트리 노드 위에 구현 가능: 편집 모드 연산을 직접 메시에 굽는 대신 "히스토리 GN 모디파이어"에 노드로 추가.
- 상당 부분은 **애드온(Python)으로도 가능** — extrude/bevel 등을 지오메트리 노드 그룹으로 만들어 모디파이어 스택에 쌓는 방식. 다만 컴포넌트 인덱스 추적(토폴로지가 바뀌면 선택이 깨짐)을 마야 수준으로 안정화하려면 C++ 지원이 필요.

### P4. 진짜 마킹 메뉴 / 핫박스 (난이도: 중)
- 블렌더 파이는 8방향 + 클릭/드래그-릴리즈는 되지만, 마야의 **제스처(마우스 궤적으로 서브메뉴까지 연속 선택)** 와 **핫박스 5구역**이 없음.
  - `source/blender/editors/interface/regions/interface_region_menu_pie.cc`
- 서브메뉴에 마우스를 가져가면 바로 열리는 "flick through" 동작과, 핫박스 풀스크린 메뉴 행 그리기 추가.

### P5. 채널 박스 가상 슬라이더 (난이도: 하)
- 라벨 위 MMB 드래그로 값 변경, 여러 필드 동시 드래그.
  - `source/blender/editors/interface/interface_handlers.cc`

### P6. 홀드 키와 Transform 모달 (난이도: 하)
- 트랜스폼 모달 중에도 X/C/V/D 키 떼기 이벤트를 하위 핸들러에 전달(pass-through), 혹은 트랜스폼 모달 안에서 "홀드 스냅"을 직접 지원.
  - `source/blender/editors/transform/transform.cc` (이벤트 처리), 트랜스폼 모달 키맵

### P7. 뷰 히스토리 (난이도: 하)
- `RegionView3D`에 이전 뷰 상태 링 버퍼 + 뒤로/앞으로 연산자.
  - `source/blender/editors/space_view3d/`

### 빌드 방법 (Windows)
```bat
git clone https://projects.blender.org/blender/blender.git
cd blender
make update
make
```
Visual Studio 2022 + CMake 필요. 패치는 `patches/` 폴더에 `.diff`로 관리할 예정.

---

## 3. 로드맵

1. **v0.1 (현재)** — 키맵 181개 항목, 마킹 메뉴(파이) 11종, 핫박스, 채널 박스·레이어 에디터, 마야 메뉴, 핵심 동작 30여 개. Blender 4.5 / 5.0 테스트 통과.
2. **v0.2** — Graph Editor / UV Editor / Outliner 마야 키맵, Target Weld, 쉘프, 메뉴셋, 마야 테마.
3. **v0.3** — 지오메트리 노드 기반 Construction History 프로토타입 (애드온).
4. **패치 1차** — P5, P6, P7 (작고 독립적, 업스트림 제출 가능성 있음).
5. **패치 2차** — P2 Transform 스택, P4 마킹 메뉴.
