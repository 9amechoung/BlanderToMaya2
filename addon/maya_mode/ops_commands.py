# SPDX-License-Identifier: GPL-3.0-or-later
"""Operators behind Maya main-menu commands that have no single Blender
operator: type filters, deformer/constraint creation, skinning helpers,
curve-to-surface tools, scene clean-up commands."""

import ast
import math
import os
import re

import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from mathutils import Vector

from .ops_tools import SMOOTH_MOD


def _types(spec):
    return {t.strip() for t in spec.split(",") if t.strip()}


def _object_filter(spec):
    """Predicate for "MESH,CURVE", "ALL", "IMAGE" or "MOD:CLOTH,FLUID" specs."""
    if spec.startswith("MOD:"):
        mods = _types(spec[4:])
        return lambda ob: any(m.type in mods for m in getattr(ob, "modifiers", ()))
    types = _types(spec)
    if "ALL" in types:
        return lambda ob: True
    if "IMAGE" in types:
        return lambda ob: ob.type == 'EMPTY' and ob.empty_display_type == 'IMAGE'
    return lambda ob: ob.type in types


def _unique(base, collection):
    i = 1
    while f"{base}{i}" in collection:
        i += 1
    return f"{base}{i}"


def _make_only_active(context, ob):
    for other in context.selected_objects:
        other.select_set(False)
    ob.select_set(True)
    context.view_layer.objects.active = ob


# --------------------------------------------------------------------------
# Select / show / hide / delete by type
# --------------------------------------------------------------------------

class MAYA_OT_select_by_type(bpy.types.Operator):
    """Select All by Type"""
    bl_idname = "maya.select_by_type"
    bl_label = "Select All by Type"
    bl_options = {'REGISTER', 'UNDO'}

    types: StringProperty()

    def execute(self, context):
        match = _object_filter(self.types)
        found = [ob for ob in context.view_layer.objects if ob.visible_get() and match(ob)]
        for ob in context.view_layer.objects:
            ob.select_set(ob in found)
        if found:
            context.view_layer.objects.active = found[0]
        return {'FINISHED'}


class MAYA_OT_select_by_modifier(bpy.types.Operator):
    """Select objects that carry a given simulation / deformer"""
    bl_idname = "maya.select_by_modifier"
    bl_label = "Select All by Node Type"
    bl_options = {'REGISTER', 'UNDO'}

    types: StringProperty()

    def execute(self, context):
        return bpy.ops.maya.select_by_type(types="MOD:" + self.types)


class MAYA_OT_show_hide(bpy.types.Operator):
    """Display > Show / Hide by type"""
    bl_idname = "maya.show_hide"
    bl_label = "Show / Hide by Type"
    bl_options = {'REGISTER', 'UNDO'}

    types: StringProperty()
    show: BoolProperty()

    def execute(self, context):
        match = _object_filter(self.types)
        for ob in context.view_layer.objects:
            if match(ob):
                ob.hide_set(not self.show)
        return {'FINISHED'}


class MAYA_OT_delete_by_type(bpy.types.Operator):
    """Edit > Delete All by Type"""
    bl_idname = "maya.delete_by_type"
    bl_label = "Delete All by Type"
    bl_options = {'REGISTER', 'UNDO'}

    types: StringProperty()

    def execute(self, context):
        match = _object_filter(self.types)
        doomed = [ob for ob in context.scene.objects if match(ob)]
        for ob in doomed:
            bpy.data.objects.remove(ob, do_unlink=True)
        self.report({'INFO'}, f"Deleted {len(doomed)} object(s)")
        return {'FINISHED'}


class MAYA_OT_delete_modifiers(bpy.types.Operator):
    """Remove simulation / deformer nodes of the given types"""
    bl_idname = "maya.delete_modifiers"
    bl_label = "Delete Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    types: StringProperty()
    all_objects: BoolProperty(default=False)

    def execute(self, context):
        types = _types(self.types)
        objects = context.scene.objects if self.all_objects else context.selected_objects
        removed = 0
        for ob in objects:
            for mod in [m for m in getattr(ob, "modifiers", ()) if m.type in types]:
                ob.modifiers.remove(mod)
                removed += 1
        self.report({'INFO'}, f"Removed {removed} node(s)")
        return {'FINISHED'}


class MAYA_OT_delete_constraints(bpy.types.Operator):
    """Remove constraints (object and bone)"""
    bl_idname = "maya.delete_constraints"
    bl_label = "Delete Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    all_objects: BoolProperty(default=False)
    types: StringProperty(description="Only these constraint types (empty = all)")

    def execute(self, context):
        types = _types(self.types)
        objects = context.scene.objects if self.all_objects else context.selected_objects
        for ob in objects:
            owners = [ob] + (list(ob.pose.bones) if ob.pose else [])
            for owner in owners:
                for con in list(owner.constraints):
                    if not types or con.type in types:
                        owner.constraints.remove(con)
        return {'FINISHED'}


class MAYA_OT_delete_all_channels(bpy.types.Operator):
    """Edit > Delete All by Type > Channels: remove all animation"""
    bl_idname = "maya.delete_all_channels"
    bl_label = "Delete All Channels"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for ob in context.scene.objects:
            if ob.animation_data:
                ob.animation_data.action = None
        return {'FINISHED'}


class MAYA_OT_delete_drivers(bpy.types.Operator):
    """Edit > Delete All by Type > Expressions: remove drivers"""
    bl_idname = "maya.delete_drivers"
    bl_label = "Delete All Expressions"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for ob in context.scene.objects:
            ad = ob.animation_data
            if ad:
                for fc in list(ad.drivers):
                    ad.drivers.remove(fc)
        return {'FINISHED'}


class MAYA_OT_delete_rigid_bodies(bpy.types.Operator):
    """Remove rigid bodies (or rigid body constraints) from the scene"""
    bl_idname = "maya.delete_rigid_bodies"
    bl_label = "Delete Rigid Bodies"
    bl_options = {'REGISTER', 'UNDO'}

    constraints: BoolProperty(default=False)

    def execute(self, context):
        attr = "rigid_body_constraint" if self.constraints else "rigid_body"
        remove = bpy.ops.rigidbody.constraint_remove if self.constraints else bpy.ops.rigidbody.object_remove
        for ob in [ob for ob in context.scene.objects if getattr(ob, attr, None)]:
            with context.temp_override(object=ob, active_object=ob):
                remove()
        return {'FINISHED'}


# --------------------------------------------------------------------------
# File / Edit helpers
# --------------------------------------------------------------------------

class MAYA_OT_increment_save(bpy.types.Operator):
    """File > Increment and Save: save as name.0001.blend, name.0002.blend ..."""
    bl_idname = "maya.increment_save"
    bl_label = "Increment and Save"

    def execute(self, context):
        path = bpy.data.filepath
        if not path:
            return bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
        stem, ext = os.path.splitext(path)
        m = re.search(r"(\d+)$", stem)
        if m:
            stem = stem[:m.start()] + str(int(m.group(1)) + 1).zfill(len(m.group(1)))
        else:
            stem += ".0001"
        bpy.ops.wm.save_as_mainfile(filepath=stem + ext)
        return {'FINISHED'}


class MAYA_OT_cut_selected(bpy.types.Operator):
    """Edit > Cut: copy selected objects to the buffer and delete them"""
    bl_idname = "maya.cut_selected"
    bl_label = "Cut"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.view3d.copybuffer()
        bpy.ops.object.delete(use_global=False, confirm=False)
        return {'FINISHED'}


class MAYA_OT_ungroup(bpy.types.Operator):
    """Edit > Ungroup: dissolve the selected group, keeping children in place"""
    bl_idname = "maya.ungroup"
    bl_label = "Ungroup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for group in list(context.selected_objects):
            if group.type != 'EMPTY':
                continue
            for child in list(group.children):
                world = child.matrix_world.copy()
                child.parent = group.parent
                child.matrix_world = world
                child.select_set(True)
            bpy.data.objects.remove(group, do_unlink=True)
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Create helpers
# --------------------------------------------------------------------------

class MAYA_OT_create_empty_group(bpy.types.Operator):
    """Create > Empty Group"""
    bl_idname = "maya.create_empty_group"
    bl_label = "Empty Group"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ob = bpy.data.objects.new(_unique("null", bpy.data.objects), None)
        ob.empty_display_size = 0.0
        context.collection.objects.link(ob)
        _make_only_active(context, ob)
        return {'FINISHED'}


class MAYA_OT_create_set(bpy.types.Operator):
    """Create > Sets > Set: a collection holding the selection"""
    bl_idname = "maya.create_set"
    bl_label = "Create Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        coll = bpy.data.collections.new(_unique("set", bpy.data.collections))
        context.scene.collection.children.link(coll)
        for ob in context.selected_objects:
            coll.objects.link(ob)
        return {'FINISHED'}


class MAYA_OT_create_camera(bpy.types.Operator):
    """Create > Cameras > Camera and Aim"""
    bl_idname = "maya.create_camera"
    bl_label = "Camera and Aim"
    bl_options = {'REGISTER', 'UNDO'}

    aim: BoolProperty(default=True)

    def execute(self, context):
        bpy.ops.object.camera_add(location=(0.0, -10.0, 0.0), rotation=(math.pi / 2, 0.0, 0.0))
        cam = context.active_object
        if self.aim:
            aim = bpy.data.objects.new(cam.name + "_aim", None)
            aim.empty_display_size = 0.5
            context.collection.objects.link(aim)
            con = cam.constraints.new('TRACK_TO')
            con.target = aim
            con.track_axis = 'TRACK_NEGATIVE_Z'
            con.up_axis = 'UP_Y'
        return {'FINISHED'}


class MAYA_OT_create_subdiv(bpy.types.Operator):
    """Create > Subdiv Primitives: low-poly primitive with smooth preview on"""
    bl_idname = "maya.create_subdiv"
    bl_label = "Subdiv Primitive"
    bl_options = {'REGISTER', 'UNDO'}

    primitive: EnumProperty(items=[(k, k.title(), "") for k in
                                   ('SPHERE', 'CUBE', 'CYLINDER', 'CONE', 'PLANE', 'TORUS')])

    def execute(self, context):
        if self.primitive == 'SPHERE':
            bpy.ops.mesh.primitive_cube_add(size=1.4)
        elif self.primitive == 'CUBE':
            bpy.ops.mesh.primitive_cube_add(size=1.0)
        elif self.primitive == 'CYLINDER':
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=1.0, depth=2.0)
        elif self.primitive == 'CONE':
            bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=1.0, depth=2.0)
        elif self.primitive == 'PLANE':
            bpy.ops.mesh.primitive_plane_add(size=1.0)
        else:
            bpy.ops.mesh.primitive_torus_add(major_segments=8, minor_segments=4)
        bpy.ops.maya.smooth_preview(mode=3)
        return {'FINISHED'}


class MAYA_OT_create_pipe(bpy.types.Operator):
    """Create > Polygon Primitives > Pipe"""
    bl_idname = "maya.create_pipe"
    bl_label = "Pipe"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=1.0, depth=2.0,
                                            end_fill_type='NOTHING')
        mod = context.active_object.modifiers.new("Thickness", 'SOLIDIFY')
        mod.thickness = 0.5
        mod.offset = -1.0
        return {'FINISHED'}


class MAYA_OT_create_helix(bpy.types.Operator):
    """Create > Polygon Primitives > Helix"""
    bl_idname = "maya.create_helix"
    bl_label = "Helix"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        mesh = bpy.data.meshes.new("helix")
        bm = bmesh.new()
        ring = []
        for i in range(8):
            a = 2 * math.pi * i / 8
            ring.append(bm.verts.new((1.0 + 0.25 * math.cos(a), 0.0, 0.25 * math.sin(a))))
        for i in range(8):
            bm.edges.new((ring[i], ring[(i + 1) % 8]))
        bm.to_mesh(mesh)
        bm.free()
        ob = bpy.data.objects.new(_unique("pHelix", bpy.data.objects), mesh)
        context.collection.objects.link(ob)
        _make_only_active(context, ob)
        screw = ob.modifiers.new("Helix", 'SCREW')
        screw.screw_offset = 0.8
        screw.iterations = 3
        screw.steps = 20
        screw.use_normal_calculate = True
        return {'FINISHED'}


class MAYA_OT_draw_curve(bpy.types.Operator):
    """Create > Curve Tools > Pencil Curve Tool"""
    bl_idname = "maya.draw_curve"
    bl_label = "Pencil Curve Tool"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.curve.primitive_bezier_curve_add()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.curve.delete(type='VERT')
        bpy.ops.wm.tool_set_by_id(name="builtin.draw")
        return {'FINISHED'}


class MAYA_OT_create_ocean(bpy.types.Operator):
    """Fluids > Ocean"""
    bl_idname = "maya.create_ocean"
    bl_label = "Ocean"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.mesh.primitive_plane_add(size=10.0)
        context.active_object.modifiers.new("Ocean", 'OCEAN')
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Modify / Display helpers
# --------------------------------------------------------------------------

class MAYA_OT_smooth_preview_to_polys(bpy.types.Operator):
    """Modify > Convert > Smooth Mesh Preview to Polygons"""
    bl_idname = "maya.smooth_preview_to_polys"
    bl_label = "Smooth Mesh Preview to Polygons"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for ob in context.selected_objects:
            mod = ob.modifiers.get(SMOOTH_MOD) if ob.type == 'MESH' else None
            if mod and mod.show_viewport:
                with context.temp_override(object=ob, active_object=ob):
                    bpy.ops.object.modifier_apply(modifier=mod.name)
        return {'FINISHED'}


class MAYA_OT_display_type(bpy.types.Operator):
    """Show selected objects as bounding box / geometry"""
    bl_idname = "maya.display_type"
    bl_label = "Display Type"
    bl_options = {'REGISTER', 'UNDO'}

    display: EnumProperty(items=[(k, k.title(), "") for k in ('BOUNDS', 'WIRE', 'SOLID', 'TEXTURED')])

    def execute(self, context):
        for ob in context.selected_objects:
            ob.display_type = self.display
        return {'FINISHED'}


class MAYA_OT_template(bpy.types.Operator):
    """Display > Object Display > Template / Untemplate"""
    bl_idname = "maya.template"
    bl_label = "Template"
    bl_options = {'REGISTER', 'UNDO'}

    state: BoolProperty(default=True)

    def execute(self, context):
        if self.state:
            objects = list(context.selected_objects)
        else:
            objects = [ob for ob in context.view_layer.objects if ob.hide_select]
        for ob in objects:
            ob.display_type = 'WIRE' if self.state else 'TEXTURED'
            ob.hide_select = self.state
            if self.state:
                ob.select_set(False)
        return {'FINISHED'}


class MAYA_OT_toggle_object_prop(bpy.types.Operator):
    """Toggle a display flag on the selected objects"""
    bl_idname = "maya.toggle_object_prop"
    bl_label = "Toggle Object Display"
    bl_options = {'REGISTER', 'UNDO'}

    prop: StringProperty()

    def execute(self, context):
        objects = context.selected_objects
        if not objects:
            return {'CANCELLED'}
        value = not getattr(objects[0], self.prop)
        for ob in objects:
            setattr(ob, self.prop, value)
        return {'FINISHED'}


class MAYA_OT_toggle_armature_names(bpy.types.Operator):
    """Show / hide joint labels"""
    bl_idname = "maya.toggle_armature_names"
    bl_label = "Toggle Joint Labels"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arms = [ob for ob in context.selected_objects if ob.type == 'ARMATURE']
        arms = arms or [ob for ob in context.scene.objects if ob.type == 'ARMATURE']
        for ob in arms:
            ob.data.show_names = not ob.data.show_names
        return {'FINISHED'}


class MAYA_OT_replace_objects(bpy.types.Operator):
    """Modify > Replace Objects: selected objects take the active object's shape"""
    bl_idname = "maya.replace_objects"
    bl_label = "Replace Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.make_links_data(type='OBDATA')
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Modeling helpers
# --------------------------------------------------------------------------

BOOLEAN_OPS = {'UNION': 'UNION', 'DIFFERENCE': 'DIFFERENCE', 'DIFFERENCE_BA': 'DIFFERENCE',
               'INTERSECT': 'INTERSECT', 'SLICE': 'DIFFERENCE', 'HOLE_PUNCH': 'DIFFERENCE',
               'CUT_OUT': 'INTERSECT', 'SPLIT_EDGES': 'UNION'}


class MAYA_OT_boolean(bpy.types.Operator):
    """Mesh > Booleans: the active object is A, the other selected meshes are B"""
    bl_idname = "maya.boolean"
    bl_label = "Boolean"
    bl_options = {'REGISTER', 'UNDO'}

    operation: EnumProperty(items=[(k, k.replace("_", " ").title(), "") for k in BOOLEAN_OPS])

    @classmethod
    def poll(cls, context):
        return (context.mode == 'OBJECT' and context.active_object is not None
                and len(context.selected_objects) >= 2)

    def execute(self, context):
        a = context.active_object
        others = [ob for ob in context.selected_objects if ob is not a and ob.type == 'MESH']
        if self.operation == 'DIFFERENCE_BA' and others:
            a, others = others[0], [a]
        for b in others:
            mod = a.modifiers.new(f"{self.operation.title()}_{b.name}", 'BOOLEAN')
            mod.operation = BOOLEAN_OPS[self.operation]
            mod.object = b
            b.display_type = 'WIRE'
            b.hide_render = True
        _make_only_active(context, a)
        return {'FINISHED'}


class MAYA_OT_curve_extrude(bpy.types.Operator):
    """Surfaces > Extrude: sweep the profile (other selected) along the path (active)"""
    bl_idname = "maya.curve_extrude"
    bl_label = "Extrude Curve"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        path = context.active_object
        if path is None or path.type != 'CURVE':
            self.report({'WARNING'}, "Select the profile curve, then the path curve")
            return {'CANCELLED'}
        profiles = [ob for ob in context.selected_objects if ob is not path and ob.type == 'CURVE']
        if profiles:
            path.data.bevel_mode = 'OBJECT'
            path.data.bevel_object = profiles[0]
        else:
            path.data.extrude = 0.5
        return {'FINISHED'}


class MAYA_OT_curve_planar(bpy.types.Operator):
    """Surfaces > Planar: fill closed curves"""
    bl_idname = "maya.curve_planar"
    bl_label = "Planar"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type == 'CURVE':
                ob.data.dimensions = '2D'
                ob.data.fill_mode = 'BOTH'
                for spline in ob.data.splines:
                    spline.use_cyclic_u = True
        return {'FINISHED'}


class MAYA_OT_loft(bpy.types.Operator):
    """Surfaces > Loft: bridge the selected curves into a polygon surface"""
    bl_idname = "maya.loft"
    bl_label = "Loft"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        curves = [ob for ob in context.selected_objects if ob.type == 'CURVE']
        if len(curves) < 2:
            self.report({'WARNING'}, "Select two or more curves")
            return {'CANCELLED'}
        depsgraph = context.evaluated_depsgraph_get()
        bm = bmesh.new()
        for ob in curves:
            mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(depsgraph))
            mesh.transform(ob.matrix_world)
            bm.from_mesh(mesh)
            bpy.data.meshes.remove(mesh)
        result = bpy.data.meshes.new("loftedSurface")
        bm.to_mesh(result)
        bm.free()
        ob = bpy.data.objects.new(_unique("loftedSurface", bpy.data.objects), result)
        context.collection.objects.link(ob)
        _make_only_active(context, ob)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.mesh.bridge_edge_loops()
        except RuntimeError as err:
            self.report({'WARNING'}, str(err))
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Deformers
# --------------------------------------------------------------------------

# Modifiers that deform towards another object. Maya selects the deformed
# objects first and the influence last, i.e. the active object.
TARGET_PROP = {'SHRINKWRAP': "target", 'SURFACE_DEFORM': "target", 'CURVE': "object",
               'CAST': "object"}


class MAYA_OT_add_modifier(bpy.types.Operator):
    """Add a Maya deformer / simulation node as a Blender modifier"""
    bl_idname = "maya.add_modifier"
    bl_label = "Add Deformer"
    bl_options = {'REGISTER', 'UNDO'}

    type: StringProperty()
    settings: StringProperty(description="Python dict literal of modifier settings")

    def execute(self, context):
        settings = ast.literal_eval(self.settings) if self.settings else {}
        target_prop = TARGET_PROP.get(self.type)
        active = context.active_object
        deformed = list(context.selected_objects)
        target = None
        if target_prop and active is not None and len(deformed) > 1:
            target = active
            deformed = [ob for ob in deformed if ob is not active]
        added = 0
        for ob in deformed:
            if not hasattr(ob, "modifiers"):
                continue
            try:
                mod = ob.modifiers.new(self.type.replace("_", " ").title(), self.type)
            except (TypeError, RuntimeError):
                mod = None
            if mod is None:
                continue
            for key, value in settings.items():
                setattr(mod, key, value)
            if target is not None:
                setattr(mod, target_prop, target)
            added += 1
        if not added:
            self.report({'WARNING'}, "Select objects that can take this deformer")
            return {'CANCELLED'}
        return {'FINISHED'}


class MAYA_OT_add_lattice(bpy.types.Operator):
    """Deform > Lattice: fit a 2x5x2 lattice around the selection"""
    bl_idname = "maya.add_lattice"
    bl_label = "Lattice"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objects = [ob for ob in context.selected_objects if ob.type in {'MESH', 'CURVE', 'SURFACE'}]
        if not objects:
            return {'CANCELLED'}
        corners = [ob.matrix_world @ Vector(c) for ob in objects for c in ob.bound_box]
        lo = Vector([min(c[i] for c in corners) for i in range(3)])
        hi = Vector([max(c[i] for c in corners) for i in range(3)])
        data = bpy.data.lattices.new("ffd1Lattice")
        data.points_u, data.points_v, data.points_w = 2, 5, 2
        lat = bpy.data.objects.new(_unique("ffd", bpy.data.objects), data)
        lat.location = (lo + hi) / 2
        lat.scale = [max(hi[i] - lo[i], 1e-3) for i in range(3)]
        context.collection.objects.link(lat)
        for ob in objects:
            ob.modifiers.new("Lattice", 'LATTICE').object = lat
        _make_only_active(context, lat)
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Constraints (targets first, constrained object last = active)
# --------------------------------------------------------------------------

class MAYA_OT_add_constraint(bpy.types.Operator):
    """Constrain: the last selected object follows the other selected objects"""
    bl_idname = "maya.add_constraint"
    bl_label = "Constrain"
    bl_options = {'REGISTER', 'UNDO'}

    type: StringProperty()

    def execute(self, context):
        owner = context.active_object
        targets = [ob for ob in context.selected_objects if ob is not owner]
        if owner is None or not targets:
            self.report({'WARNING'}, "Select target(s), then the object to constrain")
            return {'CANCELLED'}
        holder = context.active_pose_bone if context.mode == 'POSE' else None
        holder = holder or owner
        for target in targets:
            con = holder.constraints.new(self.type)
            if hasattr(con, "target"):
                con.target = target
            if self.type == 'CHILD_OF':
                # Maya's parent constraint keeps the current offset.
                con.inverse_matrix = target.matrix_world.inverted_safe()
            elif self.type == 'TRACK_TO':
                con.track_axis = 'TRACK_NEGATIVE_Z'
                con.up_axis = 'UP_Y'
        return {'FINISHED'}


class MAYA_OT_pole_vector(bpy.types.Operator):
    """Constrain > Pole Vector: use the selected object as the IK pole"""
    bl_idname = "maya.pole_vector"
    bl_label = "Pole Vector"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = next((ob for ob in context.selected_objects if ob.type == 'ARMATURE'), None)
        pole = next((ob for ob in context.selected_objects if ob.type != 'ARMATURE'), None)
        if arm is None or pole is None:
            self.report({'WARNING'}, "Select the pole object and the IK skeleton")
            return {'CANCELLED'}
        for pb in arm.pose.bones:
            for con in pb.constraints:
                if con.type == 'IK':
                    con.pole_target = pole
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Skeleton / Skin
# --------------------------------------------------------------------------

class MAYA_OT_joint_tool(bpy.types.Operator):
    """Skeleton > Create Joints: start a skeleton, then extrude joints"""
    bl_idname = "maya.joint_tool"
    bl_label = "Create Joints"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.mode == 'EDIT_ARMATURE':
            bpy.ops.armature.extrude_move('INVOKE_DEFAULT')
            return {'FINISHED'}
        bpy.ops.object.armature_add()
        context.active_object.show_in_front = True
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


class MAYA_OT_bind_skin(bpy.types.Operator):
    """Skin > Bind Skin: skin the selected meshes to the selected skeleton"""
    bl_idname = "maya.bind_skin"
    bl_label = "Bind Skin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = next((ob for ob in context.selected_objects if ob.type == 'ARMATURE'), None)
        meshes = [ob for ob in context.selected_objects if ob.type == 'MESH']
        if arm is None or not meshes:
            self.report({'WARNING'}, "Select a skeleton and the mesh(es) to bind")
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        return {'FINISHED'}


class MAYA_OT_detach_skin(bpy.types.Operator):
    """Skin > Unbind Skin"""
    bl_idname = "maya.detach_skin"
    bl_label = "Unbind Skin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for ob in context.selected_objects:
            if ob.type != 'MESH':
                continue
            for mod in [m for m in ob.modifiers if m.type == 'ARMATURE']:
                ob.modifiers.remove(mod)
            if ob.parent and ob.parent.type == 'ARMATURE':
                world = ob.matrix_world.copy()
                ob.parent = None
                ob.matrix_world = world
        return {'FINISHED'}


class MAYA_OT_go_to_bind_pose(bpy.types.Operator):
    """Skin > Go to Bind Pose"""
    bl_idname = "maya.go_to_bind_pose"
    bl_label = "Go to Bind Pose"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arms = [ob for ob in context.selected_objects if ob.type == 'ARMATURE']
        for ob in arms:
            for pb in ob.pose.bones:
                pb.location = (0.0, 0.0, 0.0)
                pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                pb.rotation_euler = (0.0, 0.0, 0.0)
                pb.scale = (1.0, 1.0, 1.0)
        return {'FINISHED'} if arms else {'CANCELLED'}


# --------------------------------------------------------------------------
# Playback
# --------------------------------------------------------------------------

class MAYA_OT_playback_sync(bpy.types.Operator):
    """Playback speed: real-time or play every frame"""
    bl_idname = "maya.playback_sync"
    bl_label = "Playback Speed"

    mode: EnumProperty(items=(('FRAME_DROP', "Real-time", ""), ('NONE', "Play Every Frame", ""),
                              ('AUDIO_SYNC', "Sync to Audio", "")))

    def execute(self, context):
        context.scene.sync_mode = self.mode
        return {'FINISHED'}


classes = (
    MAYA_OT_select_by_type,
    MAYA_OT_select_by_modifier,
    MAYA_OT_show_hide,
    MAYA_OT_delete_by_type,
    MAYA_OT_delete_modifiers,
    MAYA_OT_delete_constraints,
    MAYA_OT_delete_all_channels,
    MAYA_OT_delete_drivers,
    MAYA_OT_delete_rigid_bodies,
    MAYA_OT_increment_save,
    MAYA_OT_cut_selected,
    MAYA_OT_ungroup,
    MAYA_OT_create_empty_group,
    MAYA_OT_create_set,
    MAYA_OT_create_camera,
    MAYA_OT_create_subdiv,
    MAYA_OT_create_pipe,
    MAYA_OT_create_helix,
    MAYA_OT_draw_curve,
    MAYA_OT_create_ocean,
    MAYA_OT_smooth_preview_to_polys,
    MAYA_OT_display_type,
    MAYA_OT_template,
    MAYA_OT_toggle_object_prop,
    MAYA_OT_toggle_armature_names,
    MAYA_OT_replace_objects,
    MAYA_OT_boolean,
    MAYA_OT_curve_extrude,
    MAYA_OT_curve_planar,
    MAYA_OT_loft,
    MAYA_OT_add_modifier,
    MAYA_OT_add_lattice,
    MAYA_OT_add_constraint,
    MAYA_OT_pole_vector,
    MAYA_OT_joint_tool,
    MAYA_OT_bind_skin,
    MAYA_OT_detach_skin,
    MAYA_OT_go_to_bind_pose,
    MAYA_OT_playback_sync,
)
