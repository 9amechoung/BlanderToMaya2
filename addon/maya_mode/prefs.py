# SPDX-License-Identifier: GPL-3.0-or-later
"""Add-on preferences and the one-shot "Apply Maya Setup" operator."""

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty


class MayaModePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    smooth_level: IntProperty(
        name="Smooth Preview Level", default=2, min=0, max=6,
        description="Subdivision level used by the 3 key")
    use_marking_menus: BoolProperty(
        name="Marking Menus on Right Mouse", default=True,
        description="RMB / Shift+RMB / Ctrl+RMB open Maya marking menus "
                    "instead of Blender context menus (re-enable the add-on to apply)")
    use_maya_menubar: BoolProperty(
        name="Maya Main Menu Bar", default=True,
        description="Replace Blender's top menus with Maya's (Blender menus stay under the logo)")
    use_maya_shelf: BoolProperty(
        name="Status Line and Shelf", default=True,
        description="Draw Maya's status line and shelf in the Info editor header")
    hotbox_style: EnumProperty(
        name="Hotbox Style", default='ROWS',
        items=(('ROWS', "Menu Rows (Maya)", "All menus of all menu sets in rows"),
               ('PIE', "Pie", "Compact pie with views, modes and main menus")))
    use_hotbox: BoolProperty(
        name="Space Hotbox", default=True,
        description="Tap Space for single/four view, hold for the hotbox "
                    "(re-enable the add-on to apply)")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "smooth_level")
        layout.prop(self, "use_maya_menubar")
        layout.prop(self, "use_maya_shelf")
        layout.prop(self, "use_marking_menus")
        layout.prop(self, "use_hotbox")
        layout.prop(self, "hotbox_style")
        layout.separator()
        layout.operator("maya.apply_setup", icon='PREFERENCES')


# Maya-like colors (approximations by eye, not taken from Maya files).
UI_BG = (0.267, 0.267, 0.267)
UI_PANEL = (0.29, 0.29, 0.29)
UI_BUTTON = (0.36, 0.36, 0.36)
UI_FIELD = (0.17, 0.17, 0.17)
UI_TEXT = (0.84, 0.84, 0.84)
UI_HILITE = (0.32, 0.52, 0.65)

WIDGETS = ("wcol_regular", "wcol_tool", "wcol_toolbar_item", "wcol_menu", "wcol_pulldown",
           "wcol_menu_item", "wcol_option", "wcol_toggle", "wcol_radio", "wcol_list_item",
           "wcol_tab", "wcol_box", "wcol_pie_menu")
FIELDS = ("wcol_text", "wcol_num", "wcol_numslider")
SPACES = ("view_3d", "outliner", "properties", "dopesheet_editor", "graph_editor",
          "image_editor", "topbar", "statusbar", "info", "node_editor", "text_editor",
          "console", "sequence_editor", "nla_editor", "preferences", "spreadsheet",
          "file_browser", "clip_editor")

THEME = {
    "view_3d.wire": (0.0, 0.016, 0.376),
    "view_3d.object_selected": (1.0, 1.0, 1.0),
    "view_3d.object_active": (0.26, 1.0, 0.64),
    "view_3d.wire_edit": (0.33, 0.65, 1.0),
    "view_3d.vertex": (0.72, 0.1, 0.72),
    "view_3d.vertex_select": (1.0, 1.0, 0.0),
    "view_3d.edge_select": (1.0, 0.55, 0.0),
    "view_3d.face_select": (1.0, 0.5, 0.0, 0.25),
    "view_3d.grid": (0.36, 0.36, 0.36, 1.0),
    "view_3d.space.gradients.high_gradient": (0.42, 0.45, 0.48),
    "view_3d.space.gradients.gradient": (0.21, 0.21, 0.21),
    "user_interface.axis_x": (0.86, 0.1, 0.1),
    "user_interface.axis_y": (0.33, 0.8, 0.1),
    "user_interface.axis_z": (0.1, 0.35, 0.9),
    "user_interface.gizmo_hi": (1.0, 1.0, 0.0),
    "dopesheet_editor.frame_current": (1.0, 0.1, 0.1),
    "graph_editor.frame_current": (1.0, 0.1, 0.1),
    "nla_editor.frame_current": (1.0, 0.1, 0.1),
}


def _set_color(owner, attr, value):
    if not hasattr(owner, attr):
        return
    current = getattr(owner, attr)
    size = len(current)
    value = tuple(value[:size]) + (1.0,) * (size - len(value))
    try:
        setattr(owner, attr, value)
    except (TypeError, ValueError, AttributeError):
        pass


def _resolve(root, path):
    *parents, attr = path.split(".")
    owner = root
    for part in parents:
        owner = getattr(owner, part, None)
        if owner is None:
            return None, attr
    return owner, attr


def apply_maya_theme(theme):
    ui = theme.user_interface
    for name in WIDGETS:
        widget = getattr(ui, name, None)
        if widget is None:
            continue
        _set_color(widget, "inner", UI_BUTTON)
        _set_color(widget, "inner_sel", UI_HILITE)
        _set_color(widget, "text", UI_TEXT)
        _set_color(widget, "text_sel", (1.0, 1.0, 1.0))
    for name in ("wcol_menu_back", "wcol_tooltip"):
        _set_color(getattr(ui, name), "inner", UI_BG)
    for name in FIELDS:
        widget = getattr(ui, name, None)
        if widget is not None:
            _set_color(widget, "inner", UI_FIELD)
            _set_color(widget, "item", UI_HILITE)
            _set_color(widget, "text", UI_TEXT)
    for name in SPACES:
        space = getattr(getattr(theme, name, None), "space", None)
        if space is None:
            continue
        for attr in ("back", "header", "button", "navigation_bar", "execution_buts"):
            _set_color(space, attr, UI_BG)
        _set_color(space, "text", UI_TEXT)
        _set_color(space, "header_text", UI_TEXT)
        panels = getattr(space, "panelcolors", None)
        if panels is not None:
            _set_color(panels, "back", UI_PANEL)
            _set_color(panels, "header", UI_BUTTON)
    gradients = getattr(theme.view_3d.space, "gradients", None)
    if gradients is not None:
        gradients.background_type = 'LINEAR'
    for path, value in THEME.items():
        owner, attr = _resolve(theme, path)
        if owner is not None:
            _set_color(owner, attr, value)


class MAYA_OT_apply_theme(bpy.types.Operator):
    """Maya-like interface colors"""
    bl_idname = "maya.apply_theme"
    bl_label = "Apply Maya Theme"

    def execute(self, context):
        apply_maya_theme(context.preferences.themes[0])
        return {'FINISHED'}


class MAYA_OT_apply_setup(bpy.types.Operator):
    """Switch Blender to a Maya-like setup: Industry Compatible keymap base,
    centimeters, 24 fps, Maya navigation and viewport defaults"""
    bl_idname = "maya.apply_setup"
    bl_label = "Apply Maya Setup"
    bl_options = {'REGISTER', 'UNDO'}

    keymap: BoolProperty(name="Industry Compatible Keymap", default=True,
                         description="Base keymap with Alt+mouse navigation and QWER tools")
    units: BoolProperty(name="Centimeters", default=True,
                        description="Maya's default working unit")
    timing: BoolProperty(name="24 fps, frames 1-120", default=True)
    navigation: BoolProperty(name="Maya Navigation", default=True,
                             description="Tumble about the center of interest, no auto-perspective")
    viewport: BoolProperty(name="Viewport Look", default=True,
                           description="Maya-like clipping planes")
    theme: BoolProperty(name="Maya Theme", default=True,
                        description="Grey interface, Maya selection and component colors")
    layout: BoolProperty(name="Maya Layout", default=True,
                         description="Status line + shelf strip on top, channel box on the right")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        done = []
        if self.keymap and self._keymap():
            done.append("keymap")
        if self.units:
            self._units(context.scene)
            done.append("units")
        if self.timing:
            scene = context.scene
            scene.render.fps = 24
            scene.render.fps_base = 1.0
            scene.frame_start = 1
            scene.frame_end = 120
            done.append("timing")
        if self.navigation:
            self._navigation(context.preferences)
            done.append("navigation")
        if self.viewport:
            self._viewport(context)
            done.append("viewport")
        if self.theme:
            apply_maya_theme(context.preferences.themes[0])
            done.append("theme")
        if self.layout and context.window is not None:
            if bpy.ops.maya.setup_layout() == {'FINISHED'}:
                done.append("layout")
        self.report({'INFO'}, "Maya setup applied: " + ", ".join(done))
        return {'FINISHED'}

    def _keymap(self):
        path = bpy.utils.preset_find("Industry_Compatible", "keyconfig")
        if not path:
            self.report({'WARNING'}, "Industry Compatible keymap preset not found")
            return False
        bpy.ops.preferences.keyconfig_activate(filepath=path)
        return True

    @staticmethod
    def _units(scene):
        units = scene.unit_settings
        units.system = 'METRIC'
        units.scale_length = 0.01
        units.length_unit = 'CENTIMETERS'

    @staticmethod
    def _navigation(prefs):
        inputs = prefs.inputs
        inputs.view_rotate_method = 'TURNTABLE'
        inputs.use_rotate_around_active = False
        inputs.use_zoom_to_mouse = False
        inputs.use_auto_perspective = False
        inputs.use_mouse_depth_navigate = False

    @staticmethod
    def _viewport(context):
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Maya defaults: near 0.1 cm, far 10000 cm.
                        space.clip_start = 0.1
                        space.clip_end = 10000.0
                        space.overlay.grid_scale = 1.0


classes = (
    MayaModePreferences,
    MAYA_OT_apply_theme,
    MAYA_OT_apply_setup,
)
