# SPDX-License-Identifier: GPL-3.0-or-later
"""Marking menus rebuilt as Blender pie menus.

Directions follow Maya's default layout (see docs/01-maya-anatomy.md), so
gesture muscle memory carries over: e.g. RMB over a mesh, flick left = vertex.
"""

import bpy
from bpy.props import EnumProperty, StringProperty

from .utils import fill_pie


def _op(idname, text, icon='NONE', **props):
    def draw(layout):
        op = layout.operator(idname, text=text, icon=icon)
        for key, value in props.items():
            setattr(op, key, value)
    return draw


def _menu(idname, text, icon='NONE'):
    def draw(layout):
        layout.menu(idname, text=text, icon=icon)
    return draw


def _tool(tool_id, text, icon='NONE'):
    return _op("wm.tool_set_by_id", text, icon, name=tool_id)


def _orientation(value, text, icon='NONE'):
    return _op("wm.context_set_enum", text, icon,
               data_path="scene.transform_orientation_slots[0].type", value=value)


class MAYA_OT_mesh_tool(bpy.types.Operator):
    """Enter component mode on the object under the mouse and start a tool"""
    bl_idname = "maya.mesh_tool"
    bl_label = "Mesh Tool"
    bl_options = {'REGISTER', 'UNDO'}

    tool: EnumProperty(items=(
        ('KNIFE', "Multi-Cut", ""),
        ('LOOP_CUT', "Insert Edge Loop", ""),
        ('POLY_BUILD', "Quad Draw", ""),
        ('SCULPT', "Sculpt", ""),
    ))
    target: StringProperty()

    def execute(self, context):
        target = bpy.data.objects.get(self.target) or context.active_object
        if target is None or target.type != 'MESH':
            return {'CANCELLED'}
        if context.mode == 'OBJECT':
            for ob in context.selected_objects:
                ob.select_set(False)
            target.select_set(True)
            context.view_layer.objects.active = target
        if self.tool == 'SCULPT':
            bpy.ops.object.mode_set(mode='SCULPT')
            return {'FINISHED'}
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        tool_id = {
            'KNIFE': "builtin.knife",
            'LOOP_CUT': "builtin.loop_cut",
            'POLY_BUILD': "builtin.poly_build",
        }[self.tool]
        bpy.ops.wm.tool_set_by_id(name=tool_id)
        return {'FINISHED'}


class _Pie(bpy.types.Menu):
    bl_label = ""

    def slots(self, context):
        return {}

    def draw(self, context):
        fill_pie(self.layout.menu_pie(), self.slots(context))


class MAYA_MT_pie_components(_Pie):
    """RMB over a mesh: choose the component type"""
    bl_idname = "MAYA_MT_pie_components"
    bl_label = "Components"

    def slots(self, context):
        target = context.window_manager.maya_mm_target
        mode = "maya.component_mode"
        return {
            'N': _op(mode, "Edge", 'EDGESEL', mode='EDGE', target=target),
            'W': _op(mode, "Vertex", 'VERTEXSEL', mode='VERT', target=target),
            'S': _op(mode, "Face", 'FACESEL', mode='FACE', target=target),
            'E': _op(mode, "UV", 'UV', mode='UV', target=target),
            'NE': _op(mode, "Object Mode", 'OBJECT_DATAMODE', mode='OBJECT'),
            'SE': _op(mode, "Multi", 'MOD_WIREFRAME', mode='MULTI', target=target),
        }


class MAYA_MT_pie_object(_Pie):
    """RMB over empty space: selection commands"""
    bl_idname = "MAYA_MT_pie_object"
    bl_label = "Select"

    def slots(self, context):
        return {
            'N': _op("object.select_all", "Select All", 'SELECT_SET', action='SELECT'),
            'S': _op("object.select_all", "Select None", 'SELECT_SUBTRACT', action='DESELECT'),
            'W': _op("object.select_all", "Invert Selection", 'SELECT_DIFFERENCE', action='INVERT'),
            'E': _op("object.select_grouped", "Select Hierarchy", 'OUTLINER',
                     type='CHILDREN_RECURSIVE', extend=True),
            'NE': _op("view3d.view_all", "Frame All", 'VIEW_ZOOM'),
            'NW': _op("view3d.view_selected", "Frame Selection", 'ZOOM_SELECTED'),
        }


class MAYA_MT_pie_create(_Pie):
    """Shift+RMB over empty space: polygon primitives"""
    bl_idname = "MAYA_MT_pie_create"
    bl_label = "Create"

    def slots(self, context):
        # Maya primitive defaults, in scene units.
        return {
            'S': _op("mesh.primitive_cube_add", "Cube", 'MESH_CUBE', size=1.0),
            'E': _op("mesh.primitive_uv_sphere_add", "Sphere", 'MESH_UVSPHERE',
                     radius=1.0, segments=20, ring_count=20),
            'W': _op("mesh.primitive_cylinder_add", "Cylinder", 'MESH_CYLINDER',
                     radius=1.0, depth=2.0, vertices=20),
            'SW': _op("mesh.primitive_cone_add", "Cone", 'MESH_CONE',
                      radius1=1.0, depth=2.0, vertices=20),
            'NW': _op("mesh.primitive_plane_add", "Plane", 'MESH_PLANE', size=1.0),
            'NE': _op("mesh.primitive_circle_add", "Disc", 'MESH_CIRCLE',
                      radius=1.0, fill_type='NGON'),
            'SE': _op("mesh.primitive_torus_add", "Torus", 'MESH_TORUS',
                      major_radius=1.0, minor_radius=0.5),
            'N': _menu("VIEW3D_MT_mesh_add", "More Primitives", 'ADD'),
        }


class MAYA_MT_pie_mesh_tools(_Pie):
    """Shift+RMB over a mesh in object mode"""
    bl_idname = "MAYA_MT_pie_mesh_tools"
    bl_label = "Mesh Tools"

    def slots(self, context):
        target = context.window_manager.maya_mm_target
        tool = "maya.mesh_tool"
        return {
            'W': _op(tool, "Multi-Cut", 'MOD_EDGESPLIT', tool='KNIFE', target=target),
            'SW': _op(tool, "Insert Edge Loop", 'MOD_MULTIRES', tool='LOOP_CUT', target=target),
            'N': _op(tool, "Quad Draw", 'MESH_GRID', tool='POLY_BUILD', target=target),
            'NW': _op(tool, "Sculpt", 'SCULPTMODE_HLT', tool='SCULPT', target=target),
            'S': _op("maya.poly_smooth", "Smooth", 'MOD_SUBSURF'),
            'E': _op("object.shade_smooth", "Soften Edges", 'SHADING_RENDERED'),
            'SE': _op("object.shade_flat", "Harden Edges", 'SHADING_SOLID'),
            'NE': _op("object.join", "Combine", 'AUTOMERGE_ON'),
        }


class MAYA_MT_pie_vertex_tools(_Pie):
    """Shift+RMB in vertex mode"""
    bl_idname = "MAYA_MT_pie_vertex_tools"
    bl_label = "Vertex Tools"

    def slots(self, context):
        return {
            'S': _op("maya.extrude", "Extrude Vertex", 'MOD_SOLIDIFY'),
            'E': _op("maya.bevel", "Chamfer Vertex", 'MOD_BEVEL'),
            'SW': _op("maya.delete_components", "Delete Vertex", 'X'),
            'N': _op("mesh.remove_doubles", "Merge", 'AUTOMERGE_ON'),
            'NE': _op("mesh.merge", "Merge To Center", 'PIVOT_MEDIAN', type='CENTER'),
            'W': _tool("builtin.knife", "Multi-Cut", 'MOD_EDGESPLIT'),
            'NW': _op("mesh.vert_connect_path", "Connect", 'LINKED'),
            'SE': _op("mesh.vertices_smooth", "Average Vertices", 'MOD_SMOOTH'),
        }


class MAYA_MT_pie_edge_tools(_Pie):
    """Shift+RMB in edge mode"""
    bl_idname = "MAYA_MT_pie_edge_tools"
    bl_label = "Edge Tools"

    def slots(self, context):
        return {
            'S': _op("maya.extrude", "Extrude Edge", 'MOD_SOLIDIFY'),
            'E': _op("maya.bevel", "Bevel Edge", 'MOD_BEVEL'),
            'SW': _op("maya.delete_components", "Delete Edge", 'X', clean=True),
            'N': _op("mesh.merge", "Collapse", 'AUTOMERGE_ON', type='COLLAPSE'),
            'NE': _op("mesh.bridge_edge_loops", "Bridge", 'MOD_LATTICE'),
            'W': _tool("builtin.knife", "Multi-Cut", 'MOD_EDGESPLIT'),
            'NW': _tool("builtin.loop_cut", "Insert Edge Loop", 'MOD_MULTIRES'),
            'SE': _menu("MAYA_MT_soften_harden", "Soften / Harden", 'MOD_SMOOTH'),
        }


class MAYA_MT_pie_face_tools(_Pie):
    """Shift+RMB in face mode"""
    bl_idname = "MAYA_MT_pie_face_tools"
    bl_label = "Face Tools"

    def slots(self, context):
        return {
            'S': _op("maya.extrude", "Extrude Face", 'MOD_SOLIDIFY'),
            'E': _op("maya.bevel", "Bevel Face", 'MOD_BEVEL'),
            'SW': _op("mesh.separate", "Extract", 'UNLINKED', type='SELECTED'),
            'N': _op("mesh.merge", "Merge To Center", 'PIVOT_MEDIAN', type='CENTER'),
            'NE': _op("mesh.poke", "Poke Face", 'DECORATE'),
            'W': _tool("builtin.knife", "Multi-Cut", 'MOD_EDGESPLIT'),
            'NW': _op("mesh.duplicate_move", "Duplicate Face", 'DUPLICATE'),
            'SE': _menu("MAYA_MT_face_normals", "Face Normals", 'NORMALS_FACE'),
        }


class MAYA_MT_pie_convert(_Pie):
    """Ctrl+RMB in component mode: convert selection"""
    bl_idname = "MAYA_MT_pie_convert"
    bl_label = "Convert Selection"

    def slots(self, context):
        conv = "maya.convert_selection"
        return {
            'W': _op(conv, "To Vertices", 'VERTEXSEL', to='VERT'),
            'N': _op(conv, "To Edges", 'EDGESEL', to='EDGE'),
            'S': _op(conv, "To Faces", 'FACESEL', to='FACE'),
            'E': _op(conv, "To Edge Perimeter", 'SELECT_EXTEND', to='EDGE_PERIMETER'),
            'NE': _op("mesh.select_more", "Grow Selection", 'ADD'),
            'NW': _op("mesh.select_less", "Shrink Selection", 'REMOVE'),
            'SE': _op("mesh.loop_multi_select", "To Edge Loop", 'MOD_CURVE', ring=False),
            'SW': _op("mesh.loop_multi_select", "To Edge Ring", 'MOD_SCREW', ring=True),
        }


class MAYA_MT_pie_transform(_Pie):
    """W/E/R + LMB: manipulator axis orientation and pivot"""
    bl_idname = "MAYA_MT_pie_transform"
    bl_label = "Axis Orientation"

    def slots(self, context):
        return {
            'W': _orientation('GLOBAL', "World", 'ORIENTATION_GLOBAL'),
            'NW': _orientation('LOCAL', "Object", 'ORIENTATION_LOCAL'),
            'N': _orientation('PARENT', "Parent (Maya Local)", 'ORIENTATION_PARENT'),
            'SW': _orientation('NORMAL', "Normal", 'ORIENTATION_NORMAL'),
            'NE': _orientation('GIMBAL', "Gimbal", 'ORIENTATION_GIMBAL'),
            'S': _orientation('VIEW', "Screen", 'ORIENTATION_VIEW'),
            'SE': _op("wm.context_set_enum", "Pivot: Cursor", 'PIVOT_CURSOR',
                      data_path="tool_settings.transform_pivot_point", value='CURSOR'),
            'E': _op("maya.pivot_reset", "Reset Pivot", 'PIVOT_MEDIAN'),
        }


class MAYA_MT_pie_select_tool(_Pie):
    """Q + LMB: selection style"""
    bl_idname = "MAYA_MT_pie_select_tool"
    bl_label = "Select Tool"

    def slots(self, context):
        return {
            'NW': _tool("builtin.select_box", "Marquee", 'SELECT_SET'),
            'NE': _tool("builtin.select", "Drag (Tweak)", 'RESTRICT_SELECT_OFF'),
            'W': _tool("builtin.select_circle", "Paint", 'BRUSH_DATA'),
            'SW': _tool("builtin.select_lasso", "Lasso", 'MOD_CURVE'),
        }


class MAYA_MT_pie_hotbox(_Pie):
    """Space hold: the hotbox"""
    bl_idname = "MAYA_MT_pie_hotbox"
    bl_label = "Hotbox"

    def slots(self, context):
        return {
            'N': _menu("MAYA_MT_hotbox_views", "Views", 'VIEW_CAMERA'),
            'W': _menu("MAYA_MT_hotbox_components", "Selection Mode", 'RESTRICT_SELECT_OFF'),
            'E': _menu("MAYA_MT_hotbox_display", "Display", 'OVERLAY'),
            'S': _menu("MAYA_MT_hotbox_panels", "Panels", 'WINDOW'),
            'NW': _menu("TOPBAR_MT_file", "File", 'FILE_FOLDER'),
            'NE': _menu("TOPBAR_MT_edit", "Edit", 'EDITMODE_HLT'),
            'SW': _menu("MAYA_MT_mesh", "Mesh", 'MESH_DATA'),
            'SE': _menu("MAYA_MT_edit_mesh", "Edit Mesh", 'EDITMODE_HLT'),
        }


# ---- small sub-menus used by the pies ------------------------------------

class MAYA_MT_soften_harden(bpy.types.Menu):
    bl_idname = "MAYA_MT_soften_harden"
    bl_label = "Soften / Harden"

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.mark_sharp", text="Harden Edge").clear = False
        layout.operator("mesh.mark_sharp", text="Soften Edge").clear = True
        layout.operator("mesh.faces_shade_smooth", text="Soften All (Smooth Faces)")
        layout.operator("mesh.faces_shade_flat", text="Harden All (Flat Faces)")


class MAYA_MT_face_normals(bpy.types.Menu):
    bl_idname = "MAYA_MT_face_normals"
    bl_label = "Face Normals"

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.flip_normals", text="Reverse")
        layout.operator("mesh.normals_make_consistent", text="Conform").inside = False


class MAYA_MT_hotbox_views(bpy.types.Menu):
    bl_idname = "MAYA_MT_hotbox_views"
    bl_label = "Views"

    def draw(self, context):
        layout = self.layout
        for view, text in (('PERSP', "Perspective"), ('TOP', "Top"),
                           ('FRONT', "Front"), ('RIGHT', "Side")):
            layout.operator("maya.set_view", text=text).view = view
        layout.separator()
        layout.operator("view3d.view_camera", text="Look Through Camera")
        layout.operator("screen.region_quadview", text="Four Views")


class MAYA_MT_hotbox_components(bpy.types.Menu):
    bl_idname = "MAYA_MT_hotbox_components"
    bl_label = "Selection Mode"

    def draw(self, context):
        layout = self.layout
        for mode, text in (('OBJECT', "Object (F8)"), ('VERT', "Vertex (F9)"),
                           ('EDGE', "Edge (F10)"), ('FACE', "Face (F11)"),
                           ('UV', "UV (F12)"), ('MULTI', "Multi (F7)")):
            layout.operator("maya.component_mode", text=text).mode = mode


class MAYA_MT_hotbox_display(bpy.types.Menu):
    bl_idname = "MAYA_MT_hotbox_display"
    bl_label = "Display"

    def draw(self, context):
        layout = self.layout
        space = context.space_data
        if space is None or space.type != 'VIEW_3D':
            layout.label(text="Use in a 3D viewport")
            return
        layout.prop(space.overlay, "show_floor", text="Grid")
        layout.prop(space.overlay, "show_wireframes", text="Wireframe on Shaded")
        layout.prop(space.shading, "show_xray", text="X-Ray")
        layout.prop(space.overlay, "show_face_orientation", text="Face Orientation")
        layout.prop(space, "show_gizmo", text="Manipulators")
        layout.separator()
        layout.operator("maya.shading", text="Wireframe (4)").mode = 'WIRE'
        layout.operator("maya.shading", text="Shaded (5)").mode = 'SHADED'
        layout.operator("maya.shading", text="Textured (6)").mode = 'TEXTURED'
        layout.operator("maya.shading", text="Use All Lights (7)").mode = 'LIGHTS'


class MAYA_MT_hotbox_panels(bpy.types.Menu):
    bl_idname = "MAYA_MT_hotbox_panels"
    bl_label = "Panels"

    def draw(self, context):
        layout = self.layout
        for ui_type, text in (('VIEW_3D', "Model Panel"), ('OUTLINER', "Outliner"),
                              ('FCURVES', "Graph Editor"), ('DOPESHEET', "Dope Sheet"),
                              ('ShaderNodeTree', "Hypershade"), ('UV', "UV Editor"),
                              ('PROPERTIES', "Attribute Editor")):
            op = layout.operator("wm.context_set_enum", text=text)
            op.data_path = "area.ui_type"
            op.value = ui_type


classes = (
    MAYA_OT_mesh_tool,
    MAYA_MT_pie_components,
    MAYA_MT_pie_object,
    MAYA_MT_pie_create,
    MAYA_MT_pie_mesh_tools,
    MAYA_MT_pie_vertex_tools,
    MAYA_MT_pie_edge_tools,
    MAYA_MT_pie_face_tools,
    MAYA_MT_pie_convert,
    MAYA_MT_pie_transform,
    MAYA_MT_pie_select_tool,
    MAYA_MT_pie_hotbox,
    MAYA_MT_soften_harden,
    MAYA_MT_face_normals,
    MAYA_MT_hotbox_views,
    MAYA_MT_hotbox_components,
    MAYA_MT_hotbox_display,
    MAYA_MT_hotbox_panels,
)
