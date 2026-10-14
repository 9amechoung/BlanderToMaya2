# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared helpers: hit testing under the mouse, mode queries, pie layout."""

import bpy
from bpy_extras import view3d_utils

# Blender fills pie slots in this fixed order.
PIE_ORDER = ("W", "E", "S", "N", "NW", "NE", "SW", "SE")


def fill_pie(pie, slots):
    """Fill a pie layout from a {direction: callable(layout)} mapping.

    Maya marking menus are authored by compass direction; Blender pies are
    filled positionally, so empty directions need a placeholder separator.
    """
    for direction in PIE_ORDER:
        draw = slots.get(direction)
        if draw is None:
            pie.separator()
        else:
            draw(pie)


def object_under_mouse(context, event):
    """Return the original object under the mouse cursor, or None."""
    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None or region.type != 'WINDOW':
        return None
    coord = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    depsgraph = context.evaluated_depsgraph_get()
    hit, _loc, _nor, _idx, obj, _mat = context.scene.ray_cast(depsgraph, origin, direction)
    if not hit or obj is None:
        return None
    return obj.original


def mesh_select_mode(context):
    """'VERT' | 'EDGE' | 'FACE' for the current edit-mesh selection mode."""
    vert, edge, face = context.tool_settings.mesh_select_mode
    if face and not (vert or edge):
        return 'FACE'
    if edge and not vert:
        return 'EDGE'
    return 'VERT'


def tag_redraw_all(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def addon_prefs(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None
