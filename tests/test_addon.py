# SPDX-License-Identifier: GPL-3.0-or-later
"""Smoke tests, run inside Blender:

    blender --background --factory-startup --python tests/test_addon.py

Registers the add-on, runs the non-interactive operators on a scene and
checks the results. Exits with status 1 on the first failure.
"""

import os
import sys
import traceback

import bmesh
import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import maya_mode  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not cond:
        FAILURES.append(name)


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    return bpy.context.active_object


def test_register_cycle():
    maya_mode.unregister()
    maya_mode.register()
    check("register / unregister / register", hasattr(bpy.ops.maya, "group"))


def test_group_and_parent():
    cube = fresh_scene()
    cube.location = (3, 0, 0)
    bpy.ops.maya.group()
    group = bpy.context.active_object
    check("group creates empty at origin", group.type == 'EMPTY' and group.location.length == 0)
    check("group keeps child world position", cube.parent == group
          and abs(cube.matrix_world.translation.x - 3) < 1e-5)
    bpy.ops.object.select_all(action='DESELECT')
    cube.select_set(True)
    bpy.context.view_layer.objects.active = cube
    bpy.ops.maya.unparent()
    check("unparent keeps transform", cube.parent is None
          and abs(cube.matrix_world.translation.x - 3) < 1e-5)


def test_duplicate_with_transform():
    cube = fresh_scene()
    bpy.ops.maya.duplicate()
    dup = bpy.context.active_object
    check("Ctrl+D duplicates in place", dup is not cube and dup.location == cube.location)
    dup.location.x += 2
    dup.rotation_euler.z += 0.5
    bpy.ops.maya.duplicate_with_transform()
    third = bpy.context.active_object
    check("Shift+D repeats offset", abs(third.location.x - 4) < 1e-4
          and abs(third.rotation_euler.z - 1.0) < 1e-4,
          f"loc={tuple(round(v, 3) for v in third.location)}")
    bpy.ops.maya.duplicate_with_transform()
    fourth = bpy.context.active_object
    check("Shift+D chains", abs(fourth.location.x - 6) < 1e-4)


def test_smooth_preview():
    cube = fresh_scene()
    bpy.ops.maya.smooth_preview(mode=3)
    mod = cube.modifiers.get("MayaSmoothPreview")
    check("3 adds smooth preview", mod is not None and mod.show_viewport)
    bpy.ops.maya.smooth_level(delta=1)
    check("Page Up raises level", mod.levels == 3)
    bpy.ops.maya.smooth_preview(mode=2)
    check("2 shows cage wire", cube.show_wire and mod.show_viewport)
    bpy.ops.maya.smooth_preview(mode=1)
    check("1 hides smooth preview", not mod.show_viewport and not cube.show_wire)


def test_modify_menu():
    cube = fresh_scene()
    cube.location = (1, 2, 3)
    cube.scale = (2, 2, 2)
    bpy.ops.maya.reset_transforms()
    check("reset transforms", cube.location.length == 0 and tuple(cube.scale) == (1, 1, 1))
    cube.scale = (2, 2, 2)
    bpy.ops.maya.freeze_transforms()
    check("freeze transforms", tuple(cube.scale) == (1, 1, 1)
          and abs(cube.dimensions.x - 2) < 1e-5)

    cube.modifiers.new("Bevel", 'BEVEL')
    cube.modifiers.new("Armature", 'ARMATURE')
    bpy.ops.maya.smooth_preview(mode=3)
    bpy.ops.maya.delete_history(keep_deformers=True)
    names = [m.name for m in cube.modifiers]
    check("non-deformer history keeps deformers + smooth preview",
          names == ["Armature", "MayaSmoothPreview"], str(names))
    check("history baked into mesh", len(cube.data.polygons) > 6)


def _select_first(cube, kind):
    bm = bmesh.from_edit_mesh(cube.data)
    seq = getattr(bm, kind)
    seq.ensure_lookup_table()
    seq[0].select = True
    bm.select_flush_mode()
    bmesh.update_edit_mesh(cube.data)


def test_components():
    cube = fresh_scene()
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.maya.component_mode(mode='FACE', target=cube.name)
    check("component mode via marking menu target", bpy.context.mode == 'EDIT_MESH'
          and tuple(bpy.context.tool_settings.mesh_select_mode) == (False, False, True))

    bpy.ops.maya.component_mode(mode='VERT')
    bpy.ops.mesh.select_all(action='DESELECT')
    _select_first(cube, "verts")
    bpy.ops.maya.convert_selection(to='FACE')
    bm = bmesh.from_edit_mesh(cube.data)
    selected_faces = sum(f.select for f in bm.faces)
    check("convert vertex -> faces touches 3 faces", selected_faces == 3, str(selected_faces))
    bpy.ops.maya.convert_selection(to='VERT')
    bm = bmesh.from_edit_mesh(cube.data)
    selected_verts = sum(v.select for v in bm.verts)
    check("convert faces -> vertices", selected_verts == 7, str(selected_verts))

    bpy.ops.maya.component_mode(mode='TOGGLE')
    check("F8 toggles back to object mode", bpy.context.mode == 'OBJECT')


def test_delete_edge():
    cube = fresh_scene()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='EDGE')
    bpy.ops.mesh.select_all(action='DESELECT')
    _select_first(cube, "edges")
    bpy.ops.maya.delete_components(clean=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    check("delete edge dissolves without hole", len(cube.data.polygons) == 5,
          f"faces={len(cube.data.polygons)} verts={len(cube.data.vertices)}")


def test_set_key():
    cube = fresh_scene()
    bpy.context.scene.frame_set(10)
    bpy.ops.maya.set_key(channels='TRANSLATE')
    anim = cube.animation_data
    check("Shift+W keys translate", anim is not None and anim.action is not None)
    bpy.ops.maya.set_key(channels='ALL')
    check("S keys all", cube.animation_data.action is not None)


def test_pickwalk_visibility():
    cube = fresh_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    child = bpy.context.active_object
    child.parent = cube
    bpy.ops.maya.pickwalk(direction='UP')
    check("pickwalk up selects parent", bpy.context.active_object == cube)
    bpy.ops.maya.pickwalk(direction='DOWN')
    check("pickwalk down selects child", bpy.context.active_object == child)
    bpy.ops.maya.visibility(action='TOGGLE')
    check("H hides selection", not child.visible_get())
    bpy.ops.maya.visibility(action='TOGGLE')
    check("H again shows last hidden", child.visible_get())


def test_setup():
    bpy.ops.maya.apply_setup(keymap=False)
    units = bpy.context.scene.unit_settings
    check("apply setup units", units.length_unit == 'CENTIMETERS'
          and abs(units.scale_length - 0.01) < 1e-9)
    check("apply setup fps", bpy.context.scene.render.fps == 24
          and bpy.context.scene.frame_end == 120)


def test_poly_smooth_separate():
    cube = fresh_scene()
    bpy.ops.maya.poly_smooth()
    check("Mesh > Smooth applies subdivision", len(cube.data.polygons) == 24,
          str(len(cube.data.polygons)))
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(5, 0, 0))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.join()
    bpy.ops.maya.separate()
    check("Separate splits shells", len(bpy.context.selected_objects) == 2)


def _op_rna(idname):
    module, name = idname.split(".")
    return getattr(getattr(bpy.ops, module), name).get_rna_type()


ICONS = set(bpy.types.UILayout.bl_rna.functions["operator"].parameters["icon"].enum_items.keys())


class _OpProps:
    """Stands in for OperatorProperties; validates names and enum values."""

    def __init__(self, idname, errors):
        object.__setattr__(self, "_rna", _op_rna(idname))
        object.__setattr__(self, "_idname", idname)
        object.__setattr__(self, "_errors", errors)

    def __setattr__(self, key, value):
        prop = self._rna.properties.get(key)
        if prop is None:
            self._errors.append(f"{self._idname}: no property '{key}'")
        elif prop.type == 'ENUM' and not prop.is_enum_flag and prop.enum_items:
            if value not in prop.enum_items.keys():
                self._errors.append(f"{self._idname}.{key}: bad enum '{value}'")


class _FakeLayout:
    """Records what a menu draws and checks every reference resolves."""

    def __init__(self, errors):
        self.errors = errors

    def _icon(self, icon):
        if icon not in ICONS:
            self.errors.append(f"unknown icon {icon}")

    def operator(self, idname, text="", icon='NONE', **_kw):
        self._icon(icon)
        try:
            return _OpProps(idname, self.errors)
        except (AttributeError, KeyError, ValueError):
            self.errors.append(f"unknown operator {idname}")
            return type("Any", (), {"__setattr__": lambda *a: None})()

    def menu(self, idname, text="", icon='NONE'):
        self._icon(icon)
        if not hasattr(bpy.types, idname):
            self.errors.append(f"unknown menu {idname}")

    def prop(self, data, path, **_kw):
        if not hasattr(data, path):
            self.errors.append(f"unknown property {path}")

    def separator(self, *a, **kw):
        pass

    def label(self, *a, **kw):
        pass

    def prop_enum(self, data, path, value, **_kw):
        prop = data.bl_rna.properties.get(path)
        if prop is None or value not in prop.enum_items.keys():
            self.errors.append(f"bad prop_enum {path}={value}")

    def menu_pie(self):
        return self

    column = row = box = split = lambda self, *a, **kw: self

    def template_ID(self, *a, **kw):
        pass


def test_menus_reference_valid_operators():
    from maya_mode import pies, menus
    errors = []
    for module in (pies, menus):
        for cls in module.classes:
            if not issubclass(cls, bpy.types.Menu):
                continue
            fake = type("Self", (), {})()
            fake.layout = _FakeLayout(errors)
            fake.slots = lambda ctx, cls=cls: cls.slots(None, ctx)
            cls.draw(fake, bpy.context)
    check("all menu/pie operators, props, enums and icons resolve", not errors,
          "; ".join(sorted(set(errors))))


def test_keymap_items_resolve():
    from maya_mode import keymap
    errors = []
    for _km, kmi in keymap._registered:
        try:
            _op_rna(kmi.idname)
        except (AttributeError, KeyError, ValueError):
            errors.append(kmi.idname)
        if kmi.idname == "wm.call_menu_pie" and not hasattr(bpy.types, kmi.properties.name):
            errors.append(kmi.properties.name)
    check(f"all {len(keymap._registered)} keymap items resolve", bool(keymap._registered)
          and not errors, str(errors))


def test_actions_resolve():
    from maya_mode.actions import ACTIONS
    errors = []
    view3d = bpy.types.SpaceView3D.bl_rna
    for name, spec in ACTIONS.items():
        for s in (spec, spec.get("edit")):
            if not s:
                continue
            if "op" in s:
                try:
                    props = _OpProps(s["op"], errors)
                except (AttributeError, KeyError, ValueError):
                    errors.append(f"{name}: unknown operator {s['op']}")
                    continue
                for key, value in s["props"].items():
                    setattr(props, key, value)
            if "toggle" in s:
                rna = view3d
                for part in s["toggle"].split("."):
                    prop = rna.properties.get(part)
                    if prop is None:
                        errors.append(f"{name}: bad toggle path {s['toggle']}")
                        break
                    rna = getattr(prop, "fixed_type", None) or rna
    check(f"all {len(ACTIONS)} Maya command mappings resolve", not errors,
          "; ".join(sorted(set(errors))[:40]))


def test_maya_menubar():
    from maya_mode import maya_menus
    from maya_mode.menu_data import MENU_SETS
    errors = []
    for cls in maya_menus._menu_classes:
        fake = type("Self", (), {})()
        fake.layout = _FakeLayout(errors)
        cls.draw(fake, bpy.context)
    maya_menus.draw_maya_menubar(_FakeLayout(errors), bpy.context)
    fake = type("Self", (), {})()
    fake.layout = _FakeLayout(errors)
    maya_menus.MAYA_PT_hotbox.draw(fake, bpy.context)
    wm = bpy.context.window_manager
    wm.maya_command = "len(D.objects) + 1"
    check("command line runs Python", wm.maya_command_result == str(len(bpy.data.objects) + 1),
          wm.maya_command_result)
    total = sum(len(menus) for menus in MENU_SETS.values())
    check(f"{len(maya_menus._menu_classes)} generated Maya menus draw ({total} top menus)",
          not errors and len(maya_menus._menu_classes) >= total, "; ".join(sorted(set(errors))[:20]))


def test_theme_status_shelf():
    from maya_mode import maya_menus, prefs
    errors = []
    prefs.apply_maya_theme(bpy.context.preferences.themes[0])
    wire = tuple(round(c, 3) for c in bpy.context.preferences.themes[0].view_3d.wire)
    check("Maya theme applied", wire == (0.0, 0.016, 0.376), str(wire))
    maya_menus.draw_status_line(_FakeLayout(errors), bpy.context)
    for name, buttons in maya_menus.SHELVES:
        bpy.context.window_manager.maya_shelf = name
        for row in (None, 0, 1):
            maya_menus.draw_shelf(_FakeLayout(errors), bpy.context, row, 400)
        top, bottom = maya_menus.shelf_rows(buttons)
        if len(top) + len(bottom) != len(buttons):
            errors.append(f"{name}: shelf rows lose buttons")
    top, bottom = maya_menus.shelf_rows(dict(maya_menus.SHELVES)["Polygons"])
    check("Polygons shelf: creation on row 1, Freeze/History/Pivot on row 2",
          all(c.startswith("Create") or c == "OpenContentBrowser" for _l, c in top)
          and {"CenterPivot", "DeleteHistory", "FreezeTransformations"} <= {c for _l, c in bottom})
    check("status line and all shelves draw", not errors, "; ".join(sorted(set(errors))[:20]))
    bpy.ops.preferences.reset_default_theme()


def test_icons_and_view_name():
    from maya_mode import maya_menus
    names = list(maya_menus.ICON_EXACT.values()) + [i for _k, i in maya_menus.ICON_KEYWORDS]
    bad = sorted({i for i in names if i not in ICONS})
    check("all command icons exist in Blender", not bad, str(bad))
    check("cube command gets cube icon", maya_menus.command_icon("CreatePolygonCube") == 'MESH_CUBE')


def test_run_command():
    from maya_mode.maya_menus import run_command
    fresh_scene()
    before = len(bpy.data.objects)
    err = run_command(bpy.context, "CreatePolygonTorus")
    check("menu command creates torus", err is None and len(bpy.data.objects) == before + 1, str(err))
    torus = bpy.context.active_object
    err = run_command(bpy.context, "Triangulate")
    check("object-mode mesh command (Triangulate)", err is None
          and all(len(p.vertices) == 3 for p in torus.data.polygons), str(err))
    err = run_command(bpy.context, "Bend")
    check("deformer command adds modifier", err is None
          and torus.modifiers and torus.modifiers[-1].type == 'SIMPLE_DEFORM', str(err))
    check("unmapped command reports", run_command(bpy.context, "NoSuchCommand") is not None)


def main():
    maya_mode.register()
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        try:
            test()
        except Exception:
            traceback.print_exc()
            FAILURES.append(test.__name__)
    maya_mode.unregister()
    print(f"\n{len(FAILURES)} failure(s): {FAILURES}" if FAILURES else "\nALL PASSED")
    sys.exit(1 if FAILURES else 0)


main()
