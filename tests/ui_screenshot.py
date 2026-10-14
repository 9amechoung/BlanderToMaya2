# SPDX-License-Identifier: GPL-3.0-or-later
"""Visual check: start Blender with UI, apply the Maya setup, screenshot, quit.

    blender --factory-startup scene.blend --python tests/ui_screenshot.py -- out.png [menu_set] [shelf]

(Passing a .blend file skips the splash screen.)
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
import maya_mode  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(args[0] if args else "maya_mode_ui.png")
MENU_SET = args[1] if len(args) > 1 else "Modeling"
SHELF = args[2] if len(args) > 2 else "Polygons"
POPUP = args[3] if len(args) > 3 else ""


def window_override():
    win = bpy.context.window_manager.windows[0]
    area = max(win.screen.areas, key=lambda a: a.width * a.height)
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return {"window": win, "screen": win.screen, "area": area, "region": region}


def setup():
    maya_mode.register()
    with bpy.context.temp_override(**window_override()):
        bpy.ops.maya.apply_setup(keymap=True, units=True, timing=True, navigation=True,
                                 viewport=True, theme=True, layout=True)
        bpy.context.window_manager.maya_menu_set = MENU_SET
        bpy.context.window_manager.maya_shelf = SHELF
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(2.0, 0.0, 0.0))
        bpy.ops.maya.smooth_preview(mode=3)


def popup():
    with bpy.context.temp_override(**window_override()):
        if POPUP.startswith("MAYA_PT"):
            bpy.ops.wm.call_panel(name=POPUP, keep_open=True)
        elif POPUP:
            bpy.ops.wm.call_menu(name=POPUP)
    return None


def shoot():
    with bpy.context.temp_override(**window_override()):
        bpy.ops.screen.screenshot(filepath=OUT)
    print("SCREENSHOT", OUT)
    bpy.ops.wm.quit_blender()
    return None


def step():
    setup()
    if POPUP:
        bpy.app.timers.register(popup, first_interval=1.0)
    bpy.app.timers.register(shoot, first_interval=2.5)
    return None


bpy.app.timers.register(step, first_interval=1.0)
