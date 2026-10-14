# SPDX-License-Identifier: GPL-3.0-or-later
"""Object-level Maya behaviours: group/parent, duplicate with transform,
hold-to-snap, hold-to-edit-pivot, soft selection, pick-walking, visibility."""

import bpy
from bpy.props import EnumProperty, IntProperty

# dup name -> source name, so Shift+D can replay the last offset.
_duplicate_history = {}
# names hidden by the last H / Ctrl+H, for "show last hidden".
_last_hidden = []


# --------------------------------------------------------------------------
# Group / parent
# --------------------------------------------------------------------------

class MAYA_OT_group(bpy.types.Operator):
    """Group selected objects under a new empty at the world origin (Ctrl+G)"""
    bl_idname = "maya.group"
    bl_label = "Group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        selected = list(context.selected_objects)
        parents = {ob.parent for ob in selected}
        common_parent = parents.pop() if len(parents) == 1 else None

        group = bpy.data.objects.new(self._unique_name("group"), None)
        group.empty_display_type = 'PLAIN_AXES'
        group.empty_display_size = 0.0  # Maya groups have no shape
        last = selected[-1]
        collection = last.users_collection[0] if last.users_collection else context.collection
        collection.objects.link(group)
        if common_parent is not None:
            group.parent = common_parent

        context.view_layer.update()
        for ob in selected:
            world = ob.matrix_world.copy()
            ob.parent = group
            ob.matrix_parent_inverse.identity()
            ob.matrix_world = world

        for ob in selected:
            ob.select_set(False)
        group.select_set(True)
        context.view_layer.objects.active = group
        return {'FINISHED'}

    @staticmethod
    def _unique_name(base):
        i = 1
        while f"{base}{i}" in bpy.data.objects:
            i += 1
        return f"{base}{i}"


class MAYA_OT_parent(bpy.types.Operator):
    """Parent selected objects to the last selected one (P)"""
    bl_idname = "maya.parent"
    bl_label = "Parent"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and context.active_object
                and len(context.selected_objects) > 1)

    def execute(self, context):
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
        return {'FINISHED'}


class MAYA_OT_unparent(bpy.types.Operator):
    """Move selected objects to the world, keeping their transforms (Shift+P)"""
    bl_idname = "maya.unparent"
    bl_label = "Unparent"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Duplicate (Ctrl+D) and Duplicate with Transform (Shift+D)
# --------------------------------------------------------------------------

class MAYA_OT_duplicate(bpy.types.Operator):
    """Duplicate in place without starting a move (Ctrl+D)"""
    bl_idname = "maya.duplicate"
    bl_label = "Duplicate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        sources = sorted(context.selected_objects, key=lambda o: o.name)
        bpy.ops.object.duplicate(linked=False)
        dups = sorted(context.selected_objects, key=lambda o: o.name)
        _duplicate_history.clear()
        for src, dup in zip(sources, dups):
            _duplicate_history[dup.name] = src.name
        return {'FINISHED'}


class MAYA_OT_duplicate_with_transform(bpy.types.Operator):
    """Duplicate again, repeating the offset applied to the last duplicate (Shift+D)"""
    bl_idname = "maya.duplicate_with_transform"
    bl_label = "Duplicate with Transform"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        # Maya replays the change per channel (translate/rotate add, scale
        # multiplies) rather than as a world matrix, so a copy rotated about
        # a moved pivot keeps stepping around that pivot.
        current = sorted(context.selected_objects, key=lambda o: o.name)
        deltas = {}
        for ob in current:
            src = bpy.data.objects.get(_duplicate_history.get(ob.name, ""))
            if src is not None:
                deltas[ob.name] = (
                    ob.location - src.location,
                    [b - a for a, b in zip(src.rotation_euler, ob.rotation_euler)],
                    [b / a if a else 1.0 for a, b in zip(src.scale, ob.scale)],
                )

        bpy.ops.object.duplicate(linked=False)
        dups = sorted(context.selected_objects, key=lambda o: o.name)
        new_history = {}
        for prev, dup in zip(current, dups):
            delta = deltas.get(prev.name)
            if delta is not None:
                d_loc, d_rot, d_scale = delta
                dup.location = prev.location + d_loc
                dup.rotation_euler = [r + d for r, d in zip(prev.rotation_euler, d_rot)]
                dup.scale = [s * d for s, d in zip(prev.scale, d_scale)]
            new_history[dup.name] = prev.name
        _duplicate_history.clear()
        _duplicate_history.update(new_history)
        if not deltas:
            self.report({'INFO'}, "No previous duplicate offset; duplicated in place")
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Hold-key modifiers (X/C/V snapping, D pivot)
# --------------------------------------------------------------------------

def _snap_set(tool_settings, elements):
    try:
        tool_settings.snap_elements = elements
    except TypeError:
        # Older builds have no absolute 'GRID' element.
        tool_settings.snap_elements = {'INCREMENT'}


class _HoldKeyOperator:
    """Base for press-and-hold keys: enable on press, restore on release.

    The operator stays modal and passes every event through, so tools and
    transforms keep working while the key is held.
    """

    def invoke(self, context, event):
        self._key = event.type
        self.begin(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == self._key and event.value == 'RELEASE':
            self.end(context)
            return {'FINISHED'}
        return {'PASS_THROUGH'}

    def cancel(self, context):
        self.end(context)


class MAYA_OT_snap_hold(_HoldKeyOperator, bpy.types.Operator):
    """Snap while held: X grid, C curve/edge, V point (Maya hold-to-snap)"""
    bl_idname = "maya.snap_hold"
    bl_label = "Hold to Snap"

    target: EnumProperty(items=(
        ('GRID', "Grid", ""),
        ('EDGE', "Curve / Edge", ""),
        ('VERTEX', "Point", ""),
    ))

    def begin(self, context):
        ts = context.tool_settings
        self._saved = (ts.use_snap, set(ts.snap_elements))
        ts.use_snap = True
        _snap_set(ts, {self.target})
        context.workspace.status_text_set(f"Snapping to {self.target.lower()} (hold)")

    def end(self, context):
        ts = context.tool_settings
        use_snap, elements = self._saved
        _snap_set(ts, elements)
        ts.use_snap = use_snap
        context.workspace.status_text_set(None)


class MAYA_OT_pivot_hold(_HoldKeyOperator, bpy.types.Operator):
    """Edit the pivot while held (D). Objects: move origins only.
    Components: place the 3D cursor, which becomes the pivot"""
    bl_idname = "maya.pivot_hold"
    bl_label = "Hold to Edit Pivot"

    def begin(self, context):
        ts = context.tool_settings
        if context.mode == 'OBJECT':
            self._saved = ('OBJECT', ts.use_transform_data_origin)
            ts.use_transform_data_origin = True
        else:
            tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
            self._saved = ('EDIT', tool.idname if tool else "builtin.move")
            ts.transform_pivot_point = 'CURSOR'
            bpy.ops.wm.tool_set_by_id(name="builtin.cursor")
        context.workspace.status_text_set("Pivot edit (hold D)")

    def end(self, context):
        kind, value = self._saved
        if kind == 'OBJECT':
            context.tool_settings.use_transform_data_origin = value
        else:
            try:
                bpy.ops.wm.tool_set_by_id(name=value)
            except RuntimeError:
                pass
        context.workspace.status_text_set(None)


class MAYA_OT_pivot_toggle(bpy.types.Operator):
    """Toggle pivot edit mode (Insert)"""
    bl_idname = "maya.pivot_toggle"
    bl_label = "Toggle Pivot Edit"

    def execute(self, context):
        ts = context.tool_settings
        ts.use_transform_data_origin = not ts.use_transform_data_origin
        self.report({'INFO'}, "Pivot edit " + ("on" if ts.use_transform_data_origin else "off"))
        return {'FINISHED'}


class MAYA_OT_pivot_reset(bpy.types.Operator):
    """Reset the manipulator pivot back to the selection center"""
    bl_idname = "maya.pivot_reset"
    bl_label = "Reset Pivot"

    def execute(self, context):
        context.tool_settings.transform_pivot_point = 'MEDIAN_POINT'
        context.tool_settings.use_transform_data_origin = False
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Soft selection (B, B+LMB drag)
# --------------------------------------------------------------------------

def _soft_prop(context):
    if context.mode == 'OBJECT':
        return "use_proportional_edit_objects"
    return "use_proportional_edit"


class MAYA_OT_soft_select_toggle(bpy.types.Operator):
    """Toggle soft selection (B)"""
    bl_idname = "maya.soft_select_toggle"
    bl_label = "Toggle Soft Select"

    def execute(self, context):
        ts = context.tool_settings
        prop = _soft_prop(context)
        setattr(ts, prop, not getattr(ts, prop))
        return {'FINISHED'}


class MAYA_OT_soft_select_radius(bpy.types.Operator):
    """Drag left/right to change the soft selection falloff radius (B+LMB drag)"""
    bl_idname = "maya.soft_select_radius"
    bl_label = "Soft Select Radius"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    def invoke(self, context, event):
        ts = context.tool_settings
        setattr(ts, _soft_prop(context), True)
        self._start_x = event.mouse_x
        self._start_size = ts.proportional_size
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        ts = context.tool_settings
        if event.type == 'MOUSEMOVE':
            factor = 1.0 + (event.mouse_x - self._start_x) * 0.005
            ts.proportional_size = max(0.0001, self._start_size * max(factor, 0.01))
            context.area.header_text_set(f"Soft select radius: {ts.proportional_size:.3f}")
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            context.area.header_text_set(None)
            return {'FINISHED'}
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            ts.proportional_size = self._start_size
            context.area.header_text_set(None)
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}


# --------------------------------------------------------------------------
# Manipulator size (+ / -)
# --------------------------------------------------------------------------

class MAYA_OT_manip_size(bpy.types.Operator):
    """Grow or shrink the transform manipulator (+ / -)"""
    bl_idname = "maya.manip_size"
    bl_label = "Manipulator Size"

    delta: IntProperty(default=10)

    def execute(self, context):
        view = context.preferences.view
        view.gizmo_size = max(10, min(200, view.gizmo_size + self.delta))
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Pick-walk (arrow keys)
# --------------------------------------------------------------------------

class MAYA_OT_pickwalk(bpy.types.Operator):
    """Walk the hierarchy from the selection (arrow keys)"""
    bl_idname = "maya.pickwalk"
    bl_label = "Pick Walk"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(items=(
        ('UP', "Up", "Select parent"),
        ('DOWN', "Down", "Select first child"),
        ('LEFT', "Left", "Select previous sibling"),
        ('RIGHT', "Right", "Select next sibling"),
    ))

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        targets = []
        for ob in context.selected_objects:
            nxt = self._walk(context, ob)
            if nxt is not None and nxt not in targets:
                targets.append(nxt)
        if not targets:
            return {'CANCELLED'}
        for ob in context.selected_objects:
            ob.select_set(False)
        for ob in targets:
            ob.select_set(True)
        context.view_layer.objects.active = targets[-1]
        return {'FINISHED'}

    def _walk(self, context, ob):
        if self.direction == 'UP':
            return ob.parent
        if self.direction == 'DOWN':
            children = sorted(ob.children, key=lambda o: o.name)
            return children[0] if children else None
        if ob.parent:
            siblings = list(ob.parent.children)
        else:
            siblings = [o for o in context.view_layer.objects if o.parent is None]
        siblings.sort(key=lambda o: o.name)
        step = -1 if self.direction == 'LEFT' else 1
        return siblings[(siblings.index(ob) + step) % len(siblings)]


# --------------------------------------------------------------------------
# Visibility (H, Ctrl+H, Ctrl+Shift+H, Alt+H)
# --------------------------------------------------------------------------

class MAYA_OT_visibility(bpy.types.Operator):
    """Maya-style hide / show"""
    bl_idname = "maya.visibility"
    bl_label = "Visibility"
    bl_options = {'REGISTER', 'UNDO'}

    action: EnumProperty(items=(
        ('TOGGLE', "Toggle", "Toggle visibility, keep selection (H)"),
        ('HIDE', "Hide Selected", "(Ctrl+H)"),
        ('SHOW_LAST', "Show Last Hidden", "(Ctrl+Shift+H)"),
        ('HIDE_UNSELECTED', "Hide Unselected", "(Alt+H)"),
        ('SHOW_ALL', "Show All", ""),
    ))

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            return self._edit_mesh()
        layer = context.view_layer
        if self.action in {'TOGGLE', 'HIDE'}:
            selected = list(context.selected_objects)
            if selected:
                for ob in selected:
                    ob.hide_set(True)
                _last_hidden[:] = [ob.name for ob in selected]
            elif self.action == 'TOGGLE':
                self._show_last(layer)
        elif self.action == 'SHOW_LAST':
            self._show_last(layer)
        elif self.action == 'HIDE_UNSELECTED':
            hidden = [ob for ob in layer.objects if ob.visible_get() and not ob.select_get()]
            for ob in hidden:
                ob.hide_set(True)
            _last_hidden[:] = [ob.name for ob in hidden]
        elif self.action == 'SHOW_ALL':
            for ob in layer.objects:
                ob.hide_set(False)
        return {'FINISHED'}

    @staticmethod
    def _show_last(layer):
        for name in _last_hidden:
            ob = layer.objects.get(name)
            if ob is not None:
                ob.hide_set(False)
                ob.select_set(True)
        _last_hidden.clear()

    def _edit_mesh(self):
        if self.action in {'TOGGLE', 'HIDE'}:
            bpy.ops.mesh.hide(unselected=False)
        elif self.action == 'HIDE_UNSELECTED':
            bpy.ops.mesh.hide(unselected=True)
        else:
            bpy.ops.mesh.reveal()
        return {'FINISHED'}


classes = (
    MAYA_OT_group,
    MAYA_OT_parent,
    MAYA_OT_unparent,
    MAYA_OT_duplicate,
    MAYA_OT_duplicate_with_transform,
    MAYA_OT_snap_hold,
    MAYA_OT_pivot_hold,
    MAYA_OT_pivot_toggle,
    MAYA_OT_pivot_reset,
    MAYA_OT_soft_select_toggle,
    MAYA_OT_soft_select_radius,
    MAYA_OT_manip_size,
    MAYA_OT_pickwalk,
    MAYA_OT_visibility,
)
