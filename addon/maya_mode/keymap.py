# SPDX-License-Identifier: GPL-3.0-or-later
"""Maya default hotkeys layered on top of Blender (best with the Industry
Compatible keymap as a base, which already provides Alt+mouse navigation,
QWER tools, F / A framing).

Add-on keymap items are evaluated before the active keyconfig's items of the
same keymap, so these override Blender where they collide. Mode keymaps
("Object Mode", "Mesh") run before "3D View", so view-wide keys are added to
all three.
"""

import bpy

from .utils import addon_prefs

OBJECT = ("Object Mode", 'EMPTY')
MESH = ("Mesh", 'EMPTY')
POSE = ("Pose", 'EMPTY')
VIEW = ("3D View", 'VIEW_3D')
WINDOW = ("Window", 'EMPTY')
ALL_3D = (OBJECT, MESH, VIEW)

_registered = []


def _add(keymaps, idname, key, event_value='PRESS', *, shift=False, ctrl=False, alt=False,
         key_modifier='NONE', **props):
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:  # background mode
        return
    for name, space_type in keymaps:
        km = kc.keymaps.new(name=name, space_type=space_type)
        kmi = km.keymap_items.new(idname, key, event_value, shift=int(shift), ctrl=int(ctrl),
                                  alt=int(alt), key_modifier=key_modifier)
        for prop, val in props.items():
            setattr(kmi.properties, prop, val)
        _registered.append((km, kmi))


def _pie(keymaps, menu, key, **kw):
    _add(keymaps, "wm.call_menu_pie", key, name=menu, **kw)


def register():
    prefs = addon_prefs(bpy.context)
    use_mm = prefs.use_marking_menus if prefs else True
    use_hotbox = prefs.use_hotbox if prefs else True

    # ---- display: smooth preview 1/2/3, shading 4-7 ----------------------
    for key, mode in (('ONE', 1), ('TWO', 2), ('THREE', 3)):
        _add(ALL_3D, "maya.smooth_preview", key, mode=mode)
    _add(ALL_3D, "maya.smooth_level", 'PAGE_UP', delta=1)
    _add(ALL_3D, "maya.smooth_level", 'PAGE_DOWN', delta=-1)
    for key, mode in (('FOUR', 'WIRE'), ('FIVE', 'SHADED'),
                      ('SIX', 'TEXTURED'), ('SEVEN', 'LIGHTS')):
        _add(ALL_3D, "maya.shading", key, mode=mode)
    _add(ALL_3D, "view3d.localview", 'ONE', ctrl=True, frame_selected=False)
    _add(ALL_3D, "view3d.view_selected", 'F', shift=True, use_all_regions=True)
    _add(ALL_3D, "view3d.view_all", 'A', shift=True, use_all_regions=True)

    # ---- component modes ---------------------------------------------------
    _add(ALL_3D, "maya.component_mode", 'F8', mode='TOGGLE')
    _add(ALL_3D, "maya.component_mode", 'F9', mode='VERT')
    _add(ALL_3D, "maya.component_mode", 'F10', mode='EDGE')
    _add(ALL_3D, "maya.component_mode", 'F11', mode='FACE')
    _add(ALL_3D, "maya.component_mode", 'F12', mode='UV')
    _add(ALL_3D, "maya.component_mode", 'F7', mode='MULTI')

    # ---- marking menus -----------------------------------------------------
    if use_mm:
        _add((OBJECT, MESH), "maya.marking_menu", 'RIGHTMOUSE', kind='RMB')
        _add((OBJECT, MESH), "maya.marking_menu", 'RIGHTMOUSE', shift=True, kind='SHIFT_RMB')
        _add((OBJECT, MESH), "maya.marking_menu", 'RIGHTMOUSE', ctrl=True, kind='CTRL_RMB')
    for key in ('W', 'E', 'R'):
        _pie(ALL_3D, "MAYA_MT_pie_transform", 'LEFTMOUSE', key_modifier=key)
    _pie(ALL_3D, "MAYA_MT_pie_select_tool", 'LEFTMOUSE', key_modifier='Q')
    if use_hotbox:
        _add((VIEW,), "maya.hotbox", 'SPACE')

    # ---- transform helpers -------------------------------------------------
    for key, target in (('X', 'GRID'), ('C', 'EDGE'), ('V', 'VERTEX')):
        _add(ALL_3D, "maya.snap_hold", key, target=target)
    _add(ALL_3D, "maya.pivot_hold", 'D')
    _add(ALL_3D, "maya.pivot_toggle", 'INSERT')
    _add(ALL_3D, "maya.soft_select_toggle", 'B')
    _add(ALL_3D, "maya.soft_select_radius", 'LEFTMOUSE', key_modifier='B')
    _add(ALL_3D, "maya.manip_size", 'EQUAL', delta=10)
    _add(ALL_3D, "maya.manip_size", 'NUMPAD_PLUS', delta=10)
    _add(ALL_3D, "maya.manip_size", 'MINUS', delta=-10)
    _add(ALL_3D, "maya.toggle_attribute_editor", 'A', ctrl=True)
    _add(ALL_3D, "screen.repeat_last", 'G')

    # ---- object mode -------------------------------------------------------
    _add((OBJECT,), "maya.group", 'G', ctrl=True)
    _add((OBJECT,), "maya.parent", 'P')
    _add((OBJECT,), "maya.unparent", 'P', shift=True)
    _add((OBJECT,), "maya.duplicate", 'D', ctrl=True)
    _add((OBJECT,), "maya.duplicate_with_transform", 'D', shift=True)
    for key, direction in (('UP_ARROW', 'UP'), ('DOWN_ARROW', 'DOWN'),
                           ('LEFT_ARROW', 'LEFT'), ('RIGHT_ARROW', 'RIGHT')):
        _add((OBJECT,), "maya.pickwalk", key, direction=direction)
    _add((OBJECT,), "object.delete", 'DEL', use_global=False, confirm=False)
    _add((OBJECT,), "object.delete", 'BACK_SPACE', use_global=False, confirm=False)

    # ---- visibility --------------------------------------------------------
    _add((OBJECT, MESH), "maya.visibility", 'H', action='TOGGLE')
    _add((OBJECT, MESH), "maya.visibility", 'H', ctrl=True, action='HIDE')
    _add((OBJECT, MESH), "maya.visibility", 'H', ctrl=True, shift=True, action='SHOW_LAST')
    _add((OBJECT, MESH), "maya.visibility", 'H', alt=True, action='HIDE_UNSELECTED')

    # ---- polygon modeling --------------------------------------------------
    _add((MESH,), "maya.extrude", 'E', ctrl=True)
    _add((MESH,), "maya.bevel", 'B', ctrl=True)
    _add((MESH,), "maya.delete_components", 'DEL', clean=False)
    _add((MESH,), "maya.delete_components", 'BACK_SPACE', clean=False)
    _add((MESH,), "maya.delete_components", 'DEL', ctrl=True, clean=True)
    _add((MESH,), "mesh.select_more", 'PERIOD', shift=True)
    _add((MESH,), "mesh.select_less", 'COMMA', shift=True)
    _add((MESH,), "wm.tool_set_by_id", 'X', ctrl=True, shift=True, name="builtin.knife")
    _add((MESH,), "wm.tool_set_by_id", 'Q', ctrl=True, shift=True, name="builtin.poly_build")
    _add((MESH,), "mesh.edge_rotate", 'RIGHT_ARROW', ctrl=True, alt=True, use_ccw=False)
    _add((MESH,), "mesh.edge_rotate", 'LEFT_ARROW', ctrl=True, alt=True, use_ccw=True)

    # ---- animation ---------------------------------------------------------
    anim = (OBJECT, POSE, VIEW)
    _add(anim, "maya.set_key", 'S', channels='ALL')
    _add(anim, "maya.set_key", 'W', shift=True, channels='TRANSLATE')
    _add(anim, "maya.set_key", 'E', shift=True, channels='ROTATE')
    _add(anim, "maya.set_key", 'R', shift=True, channels='SCALE')
    _add(ALL_3D, "screen.keyframe_jump", 'COMMA', next=False)
    _add(ALL_3D, "screen.keyframe_jump", 'PERIOD', next=True)
    _add(ALL_3D, "screen.frame_offset", 'COMMA', alt=True, delta=-1)
    _add(ALL_3D, "screen.frame_offset", 'PERIOD', alt=True, delta=1)
    _add(ALL_3D, "screen.animation_play", 'V', alt=True)
    _add(ALL_3D, "screen.frame_jump", 'V', alt=True, shift=True, end=False)
    _add(ALL_3D, "maya.time_scrub", 'LEFTMOUSE', key_modifier='K')

    # ---- menu sets (F2 Modeling, F3 Rigging, F4 Animation, F5 FX) ----------
    for key, menu_set in (('F2', 'Modeling'), ('F3', 'Rigging'), ('F4', 'Animation'), ('F5', 'FX')):
        _add((WINDOW,), "wm.context_set_enum", key,
             data_path="window_manager.maya_menu_set", value=menu_set)

    # ---- undo (Maya also undoes on plain Z) --------------------------------
    _add(ALL_3D, "ed.undo", 'Z')
    _add(ALL_3D, "ed.redo", 'Z', shift=True)
    _add(ALL_3D, "ed.redo", 'Y', ctrl=True)


def unregister():
    for km, kmi in _registered:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass
    _registered.clear()
