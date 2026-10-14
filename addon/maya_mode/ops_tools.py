# SPDX-License-Identifier: GPL-3.0-or-later
"""Display (1/2/3, 4-7), component modes (F8-F12), modeling commands,
Modify menu commands, keyframing, time scrub and the Space hotbox."""

import time

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty, BoolProperty

from .utils import mesh_select_mode, object_under_mouse, addon_prefs

SMOOTH_MOD = "MayaSmoothPreview"

# Modifiers Maya would treat as deformers (kept by "Delete Non-Deformer History").
DEFORMER_TYPES = {
    'ARMATURE', 'LATTICE', 'MESH_DEFORM', 'SURFACE_DEFORM', 'HOOK', 'CURVE',
    'SIMPLE_DEFORM', 'CAST', 'WAVE', 'DISPLACE', 'SMOOTH', 'CORRECTIVE_SMOOTH',
    'LAPLACIANSMOOTH', 'SHRINKWRAP', 'WARP', 'MESH_CACHE', 'MESH_SEQUENCE_CACHE',
}


def _mesh_targets(context):
    if context.mode == 'EDIT_MESH':
        return [ob for ob in context.objects_in_mode if ob.type == 'MESH']
    return [ob for ob in context.selected_objects if ob.type == 'MESH']


# --------------------------------------------------------------------------
# Smooth mesh preview (1 / 2 / 3, Page Up / Page Down)
# --------------------------------------------------------------------------

class MAYA_OT_smooth_preview(bpy.types.Operator):
    """Maya smooth mesh preview: 1 off, 2 cage + smooth, 3 smooth"""
    bl_idname = "maya.smooth_preview"
    bl_label = "Smooth Mesh Preview"
    bl_options = {'REGISTER', 'UNDO'}

    mode: IntProperty(min=1, max=3, default=3)

    def execute(self, context):
        prefs = addon_prefs(context)
        level = prefs.smooth_level if prefs else 2
        for ob in _mesh_targets(context):
            mod = ob.modifiers.get(SMOOTH_MOD)
            if self.mode == 1:
                if mod:
                    mod.show_viewport = False
                ob.show_wire = False
                continue
            if mod is None:
                mod = ob.modifiers.new(SMOOTH_MOD, 'SUBSURF')
                mod.levels = level
                mod.render_levels = level
            mod.show_viewport = True
            mod.show_in_editmode = True
            mod.show_on_cage = False
            ob.show_wire = self.mode == 2
        return {'FINISHED'}


class MAYA_OT_smooth_level(bpy.types.Operator):
    """Change the smooth preview level (Page Up / Page Down)"""
    bl_idname = "maya.smooth_level"
    bl_label = "Smooth Preview Level"
    bl_options = {'REGISTER', 'UNDO'}

    delta: IntProperty(default=1)

    def execute(self, context):
        for ob in _mesh_targets(context):
            mod = ob.modifiers.get(SMOOTH_MOD)
            if mod:
                mod.levels = max(0, min(6, mod.levels + self.delta))
                mod.render_levels = mod.levels
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Shading (4 / 5 / 6 / 7)
# --------------------------------------------------------------------------

class MAYA_OT_shading(bpy.types.Operator):
    """4 wireframe, 5 shaded, 6 textured, 7 scene lights"""
    bl_idname = "maya.shading"
    bl_label = "Viewport Shading"

    mode: EnumProperty(items=(
        ('WIRE', "Wireframe", ""),
        ('SHADED', "Shaded", ""),
        ('TEXTURED', "Textured", ""),
        ('LIGHTS', "Use All Lights", ""),
    ))

    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        shading = context.space_data.shading
        if self.mode == 'WIRE':
            shading.type = 'WIREFRAME'
        elif self.mode == 'SHADED':
            shading.type = 'SOLID'
            shading.color_type = 'MATERIAL'
        elif self.mode == 'TEXTURED':
            shading.type = 'SOLID'
            shading.color_type = 'TEXTURE'
        else:
            shading.type = 'MATERIAL'
            shading.use_scene_lights = True
            shading.use_scene_world = False
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Component modes (F8-F12 and the RMB marking menu)
# --------------------------------------------------------------------------

class MAYA_OT_component_mode(bpy.types.Operator):
    """Switch between object mode and vertex / edge / face / UV components"""
    bl_idname = "maya.component_mode"
    bl_label = "Component Mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(items=(
        ('OBJECT', "Object Mode", ""),
        ('VERT', "Vertex", ""),
        ('EDGE', "Edge", ""),
        ('FACE', "Face", ""),
        ('MULTI', "Multi", ""),
        ('UV', "UV", ""),
        ('TOGGLE', "Toggle Object / Component", ""),
    ))
    target: StringProperty(description="Object to enter component mode on")

    def execute(self, context):
        mode = self.mode
        if mode == 'TOGGLE':
            mode = 'OBJECT' if context.mode == 'EDIT_MESH' else 'KEEP'
        if mode == 'OBJECT':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        target = bpy.data.objects.get(self.target) if self.target else None
        if target is not None and context.mode == 'OBJECT' and target.type == 'MESH':
            for ob in context.selected_objects:
                if ob is not target:
                    ob.select_set(False)
            target.select_set(True)
            context.view_layer.objects.active = target

        active = context.view_layer.objects.active
        if active is None or active.type != 'MESH':
            self.report({'WARNING'}, "Select a polygon object first")
            return {'CANCELLED'}
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        ts = context.tool_settings
        if mode in {'VERT', 'EDGE', 'FACE'}:
            bpy.ops.mesh.select_mode(type=mode)
        elif mode == 'MULTI':
            ts.mesh_select_mode = (True, True, True)
        elif mode == 'UV':
            ts.use_uv_select_sync = False
            uv_space = bpy.data.workspaces.get("UV Editing")
            if uv_space is not None:
                context.window.workspace = uv_space
        return {'FINISHED'}


class MAYA_OT_convert_selection(bpy.types.Operator):
    """Convert the component selection (Ctrl+RMB marking menu)"""
    bl_idname = "maya.convert_selection"
    bl_label = "Convert Selection"
    bl_options = {'REGISTER', 'UNDO'}

    to: EnumProperty(items=(
        ('VERT', "To Vertices", ""),
        ('EDGE', "To Edges", ""),
        ('FACE', "To Faces", ""),
        ('EDGE_PERIMETER', "To Edge Perimeter", ""),
    ))

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        if self.to == 'EDGE_PERIMETER':
            bpy.ops.mesh.region_to_loop()
            return {'FINISHED'}
        current = mesh_select_mode(context)
        order = ('VERT', 'EDGE', 'FACE')
        # Maya converts to every touching component, so growing to a higher
        # order uses Blender's "expand" switch.
        expand = order.index(self.to) > order.index(current)
        bpy.ops.mesh.select_mode(type=self.to, use_expand=expand)
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Modeling commands
# --------------------------------------------------------------------------

class MAYA_OT_extrude(bpy.types.Operator):
    """Extrude the current component selection (Ctrl+E)"""
    bl_idname = "maya.extrude"
    bl_label = "Extrude"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        mode = mesh_select_mode(context)
        if mode == 'FACE':
            bpy.ops.view3d.edit_mesh_extrude_move_normal('INVOKE_DEFAULT')
        elif mode == 'EDGE':
            bpy.ops.mesh.extrude_edges_move('INVOKE_DEFAULT')
        else:
            bpy.ops.mesh.extrude_vertices_move('INVOKE_DEFAULT')
        return {'FINISHED'}


class MAYA_OT_bevel(bpy.types.Operator):
    """Bevel edges, or chamfer vertices in vertex mode (Ctrl+B)"""
    bl_idname = "maya.bevel"
    bl_label = "Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        affect = 'VERTICES' if mesh_select_mode(context) == 'VERT' else 'EDGES'
        bpy.ops.mesh.bevel('INVOKE_DEFAULT', affect=affect)
        return {'FINISHED'}


class MAYA_OT_delete_components(bpy.types.Operator):
    """Maya Delete: removes components without leaving holes where possible"""
    bl_idname = "maya.delete_components"
    bl_label = "Delete Components"
    bl_options = {'REGISTER', 'UNDO'}

    clean: BoolProperty(name="Clean Vertices", default=False,
                        description="Also remove vertices left behind (Ctrl+Delete)")

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        mode = mesh_select_mode(context)
        if mode == 'VERT':
            bpy.ops.mesh.dissolve_verts()
        elif mode == 'EDGE':
            bpy.ops.mesh.dissolve_edges(use_verts=self.clean)
        else:
            bpy.ops.mesh.delete(type='FACE')
        return {'FINISHED'}


class MAYA_OT_poly_smooth(bpy.types.Operator):
    """Mesh > Smooth: subdivide and smooth (destructive, unlike 3)"""
    bl_idname = "maya.poly_smooth"
    bl_label = "Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    divisions: IntProperty(name="Divisions", default=1, min=1, max=4)

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            for _ in range(self.divisions):
                bpy.ops.mesh.subdivide(number_cuts=1, smoothness=1.0)
            return {'FINISHED'}
        for ob in _mesh_targets(context):
            mod = ob.modifiers.new("MayaSmooth", 'SUBSURF')
            mod.levels = self.divisions
            with context.temp_override(object=ob, active_object=ob):
                bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
                bpy.ops.object.modifier_apply(modifier=mod.name)
        return {'FINISHED'}


class MAYA_OT_separate(bpy.types.Operator):
    """Mesh > Separate: split each mesh into its disconnected shells"""
    bl_idname = "maya.separate"
    bl_label = "Separate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        was_object = context.mode == 'OBJECT'
        if was_object:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        if was_object:
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Modify menu
# --------------------------------------------------------------------------

class MAYA_OT_freeze_transforms(bpy.types.Operator):
    """Modify > Freeze Transformations"""
    bl_idname = "maya.freeze_transforms"
    bl_label = "Freeze Transformations"
    bl_options = {'REGISTER', 'UNDO'}

    translate: BoolProperty(name="Translate", default=True)
    rotate: BoolProperty(name="Rotate", default=True)
    scale: BoolProperty(name="Scale", default=True)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        bpy.ops.object.transform_apply(location=self.translate, rotation=self.rotate,
                                       scale=self.scale)
        return {'FINISHED'}


class MAYA_OT_reset_transforms(bpy.types.Operator):
    """Modify > Reset Transformations"""
    bl_idname = "maya.reset_transforms"
    bl_label = "Reset Transformations"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        for ob in context.selected_objects:
            ob.location = (0.0, 0.0, 0.0)
            ob.rotation_euler = (0.0, 0.0, 0.0)
            ob.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            ob.scale = (1.0, 1.0, 1.0)
        return {'FINISHED'}


class MAYA_OT_center_pivot(bpy.types.Operator):
    """Modify > Center Pivot (bounding-box center)"""
    bl_idname = "maya.center_pivot"
    bl_label = "Center Pivot"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        return {'FINISHED'}


class MAYA_OT_delete_history(bpy.types.Operator):
    """Edit > Delete by Type > History: bake the modifier stack into the mesh"""
    bl_idname = "maya.delete_history"
    bl_label = "Delete History"
    bl_options = {'REGISTER', 'UNDO'}

    keep_deformers: BoolProperty(name="Non-Deformer Only", default=False,
                                 description="Keep deformers such as skin (Armature)")
    all_objects: BoolProperty(name="All Objects", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        applied = 0
        objects = context.scene.objects if self.all_objects else context.selected_objects
        for ob in objects:
            if ob.type != 'MESH':
                continue
            for mod in list(ob.modifiers):
                if mod.name == SMOOTH_MOD:
                    continue  # display only, like Maya's smooth preview
                if self.keep_deformers and mod.type in DEFORMER_TYPES:
                    continue
                with context.temp_override(object=ob, active_object=ob):
                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                        applied += 1
                    except RuntimeError as err:
                        self.report({'WARNING'}, f"{ob.name}: {mod.name}: {err}")
        self.report({'INFO'}, f"Baked {applied} history node(s)")
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Animation (S, Shift+W/E/R, K-drag)
# --------------------------------------------------------------------------

def _rotation_path(owner):
    mode = owner.rotation_mode
    if mode == 'QUATERNION':
        return "rotation_quaternion"
    if mode == 'AXIS_ANGLE':
        return "rotation_axis_angle"
    return "rotation_euler"


class MAYA_OT_set_key(bpy.types.Operator):
    """Set a keyframe on transform channels (S, Shift+W/E/R)"""
    bl_idname = "maya.set_key"
    bl_label = "Set Key"
    bl_options = {'REGISTER', 'UNDO'}

    channels: EnumProperty(items=(
        ('ALL', "All", ""),
        ('TRANSLATE', "Translate", ""),
        ('ROTATE', "Rotate", ""),
        ('SCALE', "Scale", ""),
    ))
    breakdown: BoolProperty(name="Breakdown", default=False)

    def execute(self, context):
        if context.mode == 'POSE':
            owners = list(context.selected_pose_bones or [])
        else:
            owners = list(context.selected_objects)
        if not owners:
            return {'CANCELLED'}
        frame = context.scene.frame_current
        for owner in owners:
            paths = []
            if self.channels in {'ALL', 'TRANSLATE'}:
                paths.append("location")
            if self.channels in {'ALL', 'ROTATE'}:
                paths.append(_rotation_path(owner))
            if self.channels in {'ALL', 'SCALE'}:
                paths.append("scale")
            for path in paths:
                owner.keyframe_insert(data_path=path, frame=frame,
                                      keytype='BREAKDOWN' if self.breakdown else 'KEYFRAME')
        return {'FINISHED'}


class MAYA_OT_time_scrub(bpy.types.Operator):
    """Scrub time by dragging in the viewport (K + LMB drag)"""
    bl_idname = "maya.time_scrub"
    bl_label = "Virtual Time Slider"
    bl_options = {'BLOCKING', 'GRAB_CURSOR'}

    pixels_per_frame = 8

    def invoke(self, context, event):
        self._start_x = event.mouse_x
        self._start_frame = context.scene.frame_current
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            offset = int((event.mouse_x - self._start_x) / self.pixels_per_frame)
            context.scene.frame_set(self._start_frame + offset)
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            return {'FINISHED'}
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            context.scene.frame_set(self._start_frame)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


# --------------------------------------------------------------------------
# Marking menu dispatcher (RMB, Shift+RMB, Ctrl+RMB)
# --------------------------------------------------------------------------

class MAYA_OT_marking_menu(bpy.types.Operator):
    """Open the Maya marking menu for what is under the mouse"""
    bl_idname = "maya.marking_menu"
    bl_label = "Marking Menu"

    kind: EnumProperty(items=(
        ('RMB', "Right Mouse", ""),
        ('SHIFT_RMB', "Shift + Right Mouse", ""),
        ('CTRL_RMB', "Ctrl + Right Mouse", ""),
    ))

    def invoke(self, context, event):
        wm = context.window_manager
        hit = object_under_mouse(context, event)
        wm.maya_mm_target = hit.name if hit is not None else ""
        bpy.ops.wm.call_menu_pie(name=self.pick_menu(context, hit))
        return {'FINISHED'}

    def pick_menu(self, context, hit):
        in_edit = context.mode == 'EDIT_MESH'
        hit_mesh = hit is not None and hit.type == 'MESH'
        if self.kind == 'RMB':
            return "MAYA_MT_pie_components" if (in_edit or hit_mesh) else "MAYA_MT_pie_object"
        if self.kind == 'SHIFT_RMB':
            if in_edit:
                return {
                    'VERT': "MAYA_MT_pie_vertex_tools",
                    'EDGE': "MAYA_MT_pie_edge_tools",
                    'FACE': "MAYA_MT_pie_face_tools",
                }[mesh_select_mode(context)]
            return "MAYA_MT_pie_mesh_tools" if hit_mesh else "MAYA_MT_pie_create"
        return "MAYA_MT_pie_convert" if in_edit else "MAYA_MT_pie_object"


# --------------------------------------------------------------------------
# Hotbox (Space: tap = single/four view, hold = hotbox)
# --------------------------------------------------------------------------

class MAYA_OT_hotbox(bpy.types.Operator):
    """Tap Space to toggle single / four views, hold for the hotbox"""
    bl_idname = "maya.hotbox"
    bl_label = "Hotbox"

    hold_time = 0.2

    @classmethod
    def poll(cls, context):
        return context.area is not None

    def invoke(self, context, event):
        self._start = time.monotonic()
        self._key = event.type
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.02, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        held = time.monotonic() - self._start
        if event.type == self._key and event.value == 'RELEASE':
            self._finish(context)
            if held < self.hold_time:
                self._tap(context)
            return {'FINISHED'}
        if event.type == 'TIMER' and held >= self.hold_time:
            self._finish(context)
            bpy.ops.wm.call_menu_pie(name="MAYA_MT_pie_hotbox")
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def _finish(self, context):
        context.window_manager.event_timer_remove(self._timer)

    @staticmethod
    def _tap(context):
        if context.area.type == 'VIEW_3D':
            bpy.ops.screen.region_quadview()
        else:
            bpy.ops.screen.screen_full_area()


class MAYA_OT_set_view(bpy.types.Operator):
    """Switch the panel to a Maya view (persp / top / front / side)"""
    bl_idname = "maya.set_view"
    bl_label = "Set View"

    view: EnumProperty(items=(
        ('PERSP', "Perspective", ""),
        ('TOP', "Top", ""),
        ('FRONT', "Front", ""),
        ('RIGHT', "Side", ""),
        ('BOTTOM', "Bottom", ""),
        ('BACK', "Back", ""),
        ('LEFT', "Left", ""),
    ))

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def execute(self, context):
        rv3d = context.region_data
        if self.view == 'PERSP':
            if rv3d.view_perspective != 'PERSP':
                bpy.ops.view3d.view_persportho()
            return {'FINISHED'}
        bpy.ops.view3d.view_axis(type=self.view)
        return {'FINISHED'}


class MAYA_OT_toggle_attribute_editor(bpy.types.Operator):
    """Show / hide the Channel Box side panel (Ctrl+A)"""
    bl_idname = "maya.toggle_attribute_editor"
    bl_label = "Toggle Attribute Editor"

    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        space = context.space_data
        space.show_region_ui = not space.show_region_ui
        return {'FINISHED'}


classes = (
    MAYA_OT_smooth_preview,
    MAYA_OT_smooth_level,
    MAYA_OT_shading,
    MAYA_OT_component_mode,
    MAYA_OT_convert_selection,
    MAYA_OT_extrude,
    MAYA_OT_bevel,
    MAYA_OT_delete_components,
    MAYA_OT_poly_smooth,
    MAYA_OT_separate,
    MAYA_OT_freeze_transforms,
    MAYA_OT_reset_transforms,
    MAYA_OT_center_pivot,
    MAYA_OT_delete_history,
    MAYA_OT_set_key,
    MAYA_OT_time_scrub,
    MAYA_OT_marking_menu,
    MAYA_OT_hotbox,
    MAYA_OT_set_view,
    MAYA_OT_toggle_attribute_editor,
)
