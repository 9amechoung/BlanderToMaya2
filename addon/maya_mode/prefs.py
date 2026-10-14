# SPDX-License-Identifier: GPL-3.0-or-later
"""Add-on preferences and the one-shot "Apply Maya Setup" operator."""

import bpy
from bpy.props import BoolProperty, IntProperty


class MayaModePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    smooth_level: IntProperty(
        name="Smooth Preview Level", default=2, min=0, max=6,
        description="Subdivision level used by the 3 key")
    use_marking_menus: BoolProperty(
        name="Marking Menus on Right Mouse", default=True,
        description="RMB / Shift+RMB / Ctrl+RMB open Maya marking menus "
                    "instead of Blender context menus (re-enable the add-on to apply)")
    use_hotbox: BoolProperty(
        name="Space Hotbox", default=True,
        description="Tap Space for single/four view, hold for the hotbox "
                    "(re-enable the add-on to apply)")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "smooth_level")
        layout.prop(self, "use_marking_menus")
        layout.prop(self, "use_hotbox")
        layout.separator()
        layout.operator("maya.apply_setup", icon='PREFERENCES')


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
                           description="Gradient background and Maya-like clipping planes")

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
        try:
            gradients = context.preferences.themes[0].view_3d.space.gradients
            gradients.background_type = 'LINEAR'
            gradients.high_gradient = (0.36, 0.42, 0.48)
            gradients.gradient = (0.08, 0.08, 0.08)
        except (AttributeError, TypeError):
            pass


classes = (
    MayaModePreferences,
    MAYA_OT_apply_setup,
)
