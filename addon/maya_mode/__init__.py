# SPDX-License-Identifier: GPL-3.0-or-later
"""Maya Mode: make Blender work like Autodesk Maya.

Hotkeys, marking menus (as pies), the hotbox, channel box, Maya menus and
Maya behaviours (group, duplicate with transform, hold-to-snap, pivot edit,
smooth preview, set key ...). See docs/ in the repository for the analysis.
"""

import bpy
from bpy.props import StringProperty

from . import (
    prefs,
    ops_transform,
    ops_tools,
    pies,
    channel_box,
    menus,
    keymap,
)

_class_modules = (prefs, ops_transform, ops_tools, pies, channel_box, menus)


def register():
    for module in _class_modules:
        for cls in module.classes:
            bpy.utils.register_class(cls)
    bpy.types.WindowManager.maya_mm_target = StringProperty(
        description="Object under the mouse when the last marking menu opened",
        options={'SKIP_SAVE'})
    menus.register()
    keymap.register()


def unregister():
    keymap.unregister()
    menus.unregister()
    del bpy.types.WindowManager.maya_mm_target
    for module in reversed(_class_modules):
        for cls in reversed(module.classes):
            bpy.utils.unregister_class(cls)
