# 01. 마야 해부 (Maya 2025 기준)

로컬에 설치된 Maya 2025(`C:\Program Files\Autodesk\Maya2025`)를 직접 열어서 분석한 결과입니다.

> **분석 범위.** 바이너리(DLL/EXE)는 디컴파일하지 않았습니다(Autodesk EULA). 대신 설치 폴더에 평문으로 들어있는 MEL 스크립트·XML을 읽어
> "어떤 키가 무엇을 하는지, 마킹 메뉴의 어느 방향에 무엇이 있는지" 같은 **동작 사실**만 기록했습니다. 이 저장소에는 Autodesk 코드·아이콘·리소스가 한 줄도 들어있지 않습니다.

---

## 1. 설치 폴더 구조

| 폴더 | 크기 | 내용 |
|---|---|---|
| `bin/` | 989 MB | 코어 엔진 DLL 269개, 내장 플러그인 `.mll` 77개 |
| `plug-ins/` | 805 MB | 대형 플러그인 묶음 (MASH, XGen, Bonus Tools, FBX, ATF, sweep, camd) |
| `Python/` | 253 MB | 내장 Python 3 (mayapy) |
| `scripts/` | 54 MB | **UI 전체** — MEL 5,645개 + XML 213개 |
| `resources/` | — | 번역(l10n), Qt 스타일시트, 워크스페이스, 툴클립 영상 |
| `devkit/`, `include/`, `lib/` | — | C++ API (OpenMaya) SDK |

### `scripts/` 내부

| 하위 폴더 | 파일 수 | 역할 |
|---|---|---|
| `others/` | 4,111 | 각종 명령·마킹 메뉴·에디터 구현 |
| `AETemplates/` | 915 | Attribute Editor 노드별 레이아웃 |
| `startup/` | 383 | 부팅 시퀀스, 메인 메뉴, 핫키, 프리퍼런스 |
| `NETemplates/` | 184 | Node Editor 템플릿 |
| `paintEffects/` | 100 | 페인트 이펙트 브러시 |
| 나머지 | — | muscle, turtle, fur, shelves, FBX … |

**핵심 결론:** 마야의 *사용자 경험*(메뉴, 핫키, 마킹 메뉴, 에디터 레이아웃)은 거의 전부 C++이 아니라 **MEL 스크립트 층**에 있습니다.
C++ 코어는 노드 그래프·지오메트리 연산·뷰포트만 담당합니다. 그래서 "UX를 블렌더로 옮기기"는 대부분 **파이썬 애드온으로 가능**하고,
패치가 필요한 건 코어 데이터 모델이 다른 부분뿐입니다 (→ [02-gap-and-patch-plan.md](02-gap-and-patch-plan.md)).

---

## 2. 코어 엔진 계층 (DLL 이름 기준)

`bin/`의 DLL 이름이 아키텍처를 그대로 보여줍니다.

```
Foundation            ─ 기본 자료형, 메모리, 문자열
  └ DependEngine      ─ Dependency Graph (DG): 노드·어트리뷰트·연결·평가
      └ DataModel     ─ DAG(계층), 셀렉션, 언두
          ├ Poly / PolyEngine / PolySlice / PolyUISlice      ─ 폴리곤
          ├ Nurbs / NurbsEngine / NurbsSlice / NurbsUISlice  ─ NURBS
          ├ Subdiv / SubdivEngine / SubdivGeom / SubdivUI    ─ 서브디비전
          ├ AnimSlice                                        ─ 애니메이션 커브
          ├ KinSlice                                         ─ 조인트·IK (Kinematics)
          ├ RenderModel / RenderSlice / RenderUISlice        ─ 렌더 설정
          └ ModelUISlice                                     ─ 모델링 UI 컨텍스트(툴)
      └ 3dGraphics / OGSDevices   ─ Viewport 2.0 (OGS 그래픽 엔진)
  └ ExtensionLayer    ─ 플러그인 로딩
      └ OpenMaya / OpenMayaAnim / OpenMayaFX / OpenMayaRender / OpenMayaUI  ─ 공개 C++ API
```

패턴: 도메인마다 `Engine`(연산) → `Slice`(노드/명령) → `UISlice`(툴 컨텍스트·조작기) 3단으로 나뉩니다.
Modeling Toolkit(멀티컷, 쿼드 드로우, 타겟 웰드)은 코어가 아니라 `modelingToolkit.mll` 플러그인입니다.

---

## 3. 데이터 모델 — 블렌더와 가장 다른 부분

### 3.1 Transform 노드 / Shape 노드 분리
마야의 오브젝트 하나 = **transform 노드**(위치) + **shape 노드**(지오메트리). 아웃라이너에는 transform만 보이고 채널 박스 아래 `SHAPES`에 shape가 나옵니다.
블렌더의 Object + Data(Mesh)와 개념적으로 같아서 매핑이 쉽습니다.

### 3.2 Transform 행렬 구성 (블렌더에 없는 것)
마야 transform은 아래 채널들을 순서대로 곱합니다:

```
[Scale Pivot 이동] · Scale · Shear · [Scale Pivot 복귀] · [Scale Pivot Translate]
· [Rotate Pivot 이동] · Rotate Axis · Rotate(+Rotate Order) · [Rotate Pivot 복귀] · [Rotate Pivot Translate]
· Translate
```
(조인트는 여기에 **Joint Orient**가 추가)

블렌더 Object는 `location · rotation · scale` 하나뿐이고 **피벗 = 오브젝트 원점**입니다.
→ 별도 Rotate Pivot / Scale Pivot / Rotate Axis / Joint Orient가 없습니다. **애드온으로는 근사만 가능, 완전 재현은 패치 필요.**

### 3.3 Construction History (Dependency Graph)
마야에서 Extrude를 하면 `polyExtrudeFace` 노드가 생기고 원본 메시 → 노드 → 결과 메시로 연결됩니다(채널 박스 `INPUTS`). 나중에 값 수정 가능.
블렌더의 대응물은 **모디파이어 스택**(+지오메트리 노드)입니다. 하지만 블렌더 편집 모드 연산(extrude 등)은 파괴적이라 히스토리가 남지 않습니다.

### 3.4 기본 환경값
| 항목 | 마야 | 블렌더 |
|---|---|---|
| 업 축 | **Y-up** | Z-up |
| 단위 | **cm** | m |
| 프레임 | 24 fps, 1–120 | 24 fps, 1–250 |
| 카메라 | persp/top/front/side **카메라 노드** | 뷰 상태(카메라 아님) |

---

## 4. 부팅 시퀀스 (`scripts/startup`)

파일명으로 확인되는 초기화 흐름:

1. `initialStartup` → `createGlobalOptVars` / `createPreferencesOptVars` (optionVar = 프리퍼런스 저장소)
2. `initialPlugins` / `initialPluginLoad` / `autoLoadPlugin`
3. `initialLayout` → `initMainWindow` → `initMainMenuBar` (`FileMenu`, `EditMenu`, `ModObjectsMenu`, `PolygonsMeshMenu` …)
4. `initStatusLine`, `initShelf`, `initToolSettings`, `initChannelBox`, `initAttributeEditor`, `initTimeSlider`, `initCommandLine`, `initHelpLine`
5. `initContexts`, `initManipulators` (툴/조작기)
6. `defaultRunTimeCommands` → `namedCommandSetup` → **`hotkeySetup`**
7. `HotboxMenus` (`HotboxNorth/South/East/West/CenterMenu`)

---

## 5. 핫키 시스템 (3층 구조)

```
runTimeCommand  (실제 동작 코드, defaultRunTimeCommands.mel 에 2,714개)
   └ nameCommand (이름 붙은 래퍼, press / release 각각)
        └ hotkey  (키 → nameCommand, -name = 눌림, -releaseName = 뗌)
```

- **press/release 분리**가 핵심입니다. `x`를 누르는 동안만 그리드 스냅, `d`를 누르는 동안만 피벗 편집, `Space`를 누르는 동안만 핫박스 — 전부 release 이름이 따로 있습니다.
- **hotkeyCtx**: 같은 키가 에디터마다 다른 일을 합니다. 확인된 컨텍스트: `hyperShadePanel`, `nodeEditorPanel`, `graphEditor`, `polyTexturePlacementPanel`(UV), `hyperGraphPanel`, `timeEditorPanel`, `dopeSheetPanel`, `outlinerPanel`, `shapePanel`, `posePanel`.
  블렌더의 "에디터별 keymap"과 정확히 같은 개념입니다.

### 5.1 기본 핫키 표 (뷰포트, `hotkeySetup.mel` 기준) → 애드온 대응

| 키 | 마야 동작 | Maya Mode 구현 |
|---|---|---|
| Q / W / E / R | 선택 / 이동 / 회전 / 스케일 툴 | Industry Compatible 키맵 기본 |
| T | Show Manipulator | (Blender 툴 기즈모) |
| Y | 마지막 툴 | — |
| **Q/W/E/R + LMB(홀드)** | 해당 툴 마킹 메뉴 (축 방향/피벗) | `MAYA_MT_pie_transform`, `MAYA_MT_pie_select_tool` |
| **Space (탭 / 홀드)** | 패널 최대화 토글 / **핫박스** | `maya.hotbox` |
| F / Shift+F | 선택 프레임 / 모든 패널 | `view3d.view_selected` |
| A / Shift+A | 전체 프레임 / 모든 패널 | `view3d.view_all` |
| **1 / 2 / 3** | Smooth Mesh Preview 끔 / 케이지+스무스 / 스무스 | `maya.smooth_preview` (Subsurf 모디파이어) |
| Page Up / Down | 스무스 레벨 ± | `maya.smooth_level` |
| **4 / 5 / 6 / 7** | 와이어 / 셰이디드 / 텍스처 / 모든 라이트 | `maya.shading` |
| Ctrl+1 | Isolate Select | `view3d.localview` |
| **F8** | 오브젝트 ⇄ 컴포넌트 | `maya.component_mode TOGGLE` |
| F9 / F10 / F11 / F12 | 버텍스 / 엣지 / 페이스 / UV | `maya.component_mode` |
| F7 | 멀티 컴포넌트 | `MULTI` |
| **X / C / V (홀드)** | 그리드 / 커브 / 포인트 스냅 | `maya.snap_hold` |
| **D (홀드)**, Insert | 피벗 편집 | `maya.pivot_hold`, `maya.pivot_toggle` |
| J (홀드) | 스냅 회전/이동 토글 | — |
| **B / B+LMB 드래그** | 소프트 셀렉션 / 반경 조절 | `maya.soft_select_toggle`, `maya.soft_select_radius` |
| + / - | 조작기 크기 | `maya.manip_size` |
| Ctrl+G | 그룹 | `maya.group` |
| P / Shift+P | 페어런트 / 언페어런트 | `maya.parent`, `maya.unparent` |
| Ctrl+D | 복제(제자리) | `maya.duplicate` |
| **Shift+D** | Duplicate with Transform | `maya.duplicate_with_transform` |
| H | 가시성 토글(선택 유지) | `maya.visibility TOGGLE` |
| Ctrl+H / Alt+H / Ctrl+Shift+H | 숨기기 / 비선택 숨기기 / 마지막 숨긴 것 보이기 | `maya.visibility` |
| ↑ ↓ ← → | Pick-walk (계층 이동) | `maya.pickwalk` |
| G / Shift+G | 마지막 동작 반복 | `screen.repeat_last` |
| Z / Ctrl+Z / Shift+Z / Ctrl+Y | 언두 / 리두 | `ed.undo`, `ed.redo` |
| [ / ] , Alt+Z / Alt+Y | **뷰 변경 언두/리두** | ✗ (블렌더에 뷰 히스토리 없음 → 패치) |
| S | 키 설정 | `maya.set_key ALL` |
| Shift+W / E / R | 이동/회전/스케일만 키 | `maya.set_key` |
| , / . | 이전 / 다음 키 | `screen.keyframe_jump` |
| Alt+, / Alt+. | 1프레임 이동 | `screen.frame_offset` |
| Alt+V / Alt+Shift+V | 재생 / 처음으로 | `screen.animation_play`, `frame_jump` |
| K + LMB 드래그 | 가상 타임 슬라이더 | `maya.time_scrub` |
| Ctrl+A | Attribute Editor ⇄ Channel Box | `maya.toggle_attribute_editor` |
| Ctrl+E / Ctrl+B | Extrude / Bevel | `maya.extrude`, `maya.bevel` |
| Ctrl+Shift+X | Multi-Cut | `builtin.knife` |
| Ctrl+Shift+Q | Quad Draw | `builtin.poly_build` |
| Delete / Ctrl+Delete | 컴포넌트 삭제 / 버텍스까지 정리 | `maya.delete_components` |
| > / < | 선택 확장 / 축소 | `mesh.select_more/less` |
| Ctrl+Alt+← / → | 엣지 회전(Spin) | `mesh.edge_rotate` |

UV 에디터(`polyTexturePlacementPanel`)에서는 Q/W/E/R이 UV 툴, Ctrl+L 레이아웃, Ctrl+U 언폴드, Shift+X 컷, Shift+S 소우 — 블렌더 UV 에디터 키맵으로 추후 이식 대상.

---

## 6. 마킹 메뉴 (방향 = 근육 기억)

마킹 메뉴는 `menuItem -radialPosition N|NE|E|SE|S|SW|W|NW`로 8방향에 배치됩니다.
아래 배치를 스크립트에서 직접 추출했고, 애드온의 파이 메뉴가 같은 방향을 씁니다.

### 6.1 RMB (오브젝트 위) — `dagMenuProc`
폴리곤 메시의 컴포넌트 마스크 순서 `edge, vertex, facet, puv, pvf, meshComponents`가 방향 배열 `N, W, S, E, SW, SE …`에 대응:

```
            Edge (N)
  (NW)                Object Mode (NE)
Vertex (W)    ●       UV (E)
  Vertex Face (SW)    Multi (SE)
            Face (S)
```
→ `MAYA_MT_pie_components`. 마우스 아래 오브젝트를 레이캐스트로 찾아 그 오브젝트로 진입(마야처럼 선택되지 않은 오브젝트도 바로 컴포넌트 모드).

### 6.2 Shift+RMB — `contextPolyTools*MM` (컴포넌트별로 다른 메뉴)
| 방향 | 빈 공간(Default) | 오브젝트 | 버텍스 | 엣지 | 페이스 |
|---|---|---|---|---|---|
| S | Cube | Extrude | Extrude Vertex | Extrude Edge | Extrude Face |
| E | Sphere | (Soften/Harden) | Chamfer Vertex | Bevel Edge | Bevel Face |
| W | Cylinder | Multi-Cut | Multi-Cut | Multi-Cut | Multi-Cut |
| N | (Create Poly) | Merge Vertex Tool | Merge 서브메뉴 | Merge/Collapse 서브메뉴 | Merge to Center |
| SW | Cone | Insert Edge Loop | Delete Vertex | Delete Edge | Wedge |
| NE | Disc | Fill Hole | Average/Merge | Flip/Spin 서브메뉴 | Poke |
| NW | Plane | Sculpt | Paint Select | Merge Edge Tool | Paint Select |
| SE | Torus | Soften/Harden 서브메뉴 | Vertex Normals 서브메뉴 | Soften/Harden 서브메뉴 | Face Normals 서브메뉴 |

→ `MAYA_MT_pie_create / mesh_tools / vertex_tools / edge_tools / face_tools`. 블렌더에 없는 기능(Wedge, Paint Select)은 가장 가까운 것(Extract, Duplicate Face)으로 대체.

### 6.3 Ctrl+RMB — `polyConvertMM` (선택 변환)
W: To Vertices · N: To Edges · S: To Faces · E: To UVs · NE: Grow · NW: Shrink · SE: Edge Loop · SW: Edge Ring
→ `MAYA_MT_pie_convert` (E는 블렌더에서 UV 선택이 메시 선택과 분리돼 있어 "To Edge Perimeter"로 대체)

### 6.4 툴 키 + LMB
- `translateMarkingMenuImpl` (W+LMB): World / Object / Local(=부모 공간) / Normal / Live Object / Custom Axis / 스냅 서브메뉴 / Keep Spacing
- `selectMarkingMenuImpl` (Q+LMB): NW Marquee · NE Drag · W Paint · SW Lasso · E Channel Box Select · SE Clear
- `buildShadingMM`: N Points · NE Smooth Active · E Smooth · SE Flat · S Flat Active · SW Bounding Box · W Wireframe

> 용어 주의: 마야 "Object" 축 = 블렌더 `LOCAL`, 마야 "Local" 축(부모 공간) = 블렌더 `PARENT`.

### 6.5 핫박스 (`HotboxMenus`, `HotboxNorth/South/East/West/Center`)
Space를 누르고 있으면 화면 중앙에 모든 메뉴셋이 행으로 펼쳐지고, 중앙을 기준으로 4개 구역(N/S/E/W)+중앙에 각각 별도 마킹 메뉴가 있습니다
(뷰 전환, 패널 타입, UI 토글, 선택 마스크 등 — 사용자 커스터마이즈 가능).
→ 애드온은 파이 메뉴 하나로 근사 (`MAYA_MT_pie_hotbox`). 진짜 풀스크린 핫박스는 패치 대상.

---

## 7. 메인 메뉴 (메뉴셋)

메뉴셋(F2 Modeling · F3 Rigging · F4 Animation · F5 FX · F6 Rendering)에 따라 메인 메뉴바가 바뀝니다.
모델링 메뉴셋의 핵심 메뉴와 애드온의 `Maya` 상단 메뉴 대응:

- **Modify**: Freeze / Reset Transformations, Center Pivot, Match Transform, Group, Parent
- **Mesh** (`PolygonsMeshMenu`): Combine, Separate, Smooth, Reduce, Triangulate, Quadrangulate, Fill Hole, Mirror, Booleans
- **Edit Mesh**: Extrude, Bevel, Bridge, Poke, Wedge, Merge, Collapse, Detach, Extract, Duplicate, Spin Edge
- **Mesh Tools** (`PolygonsBuildToolsMenu`): Multi-Cut, Insert Edge Loop, Offset Edge Loop, Quad Draw, Slide Edge, Target Weld
- **Edit > Delete by Type > History / Non-Deformer History** → 모디파이어 적용(`maya.delete_history`)

---

## 8. 채널 박스 구성

```
pCube1                 ← 오브젝트(transform) 이름
  Translate X/Y/Z
  Rotate X/Y/Z
  Scale X/Y/Z
  Visibility
SHAPES
  pCubeShape1          ← shape 노드
INPUTS
  polyExtrudeFace1     ← 히스토리 노드들(값 수정 가능)
  polyCube1
```
키가 있으면 빨간색, 애니메이션 커브 연결은 주황, 잠금은 회색. 채널 이름 위에서 **MMB 드래그 = 가상 슬라이더**.
→ `VIEW3D_PT_maya_channel_box` (사이드바 "Channels" 탭). 키 색상은 블렌더 기본 키 프레임 색이 그대로 적용됨. MMB 가상 슬라이더는 패치 대상.
