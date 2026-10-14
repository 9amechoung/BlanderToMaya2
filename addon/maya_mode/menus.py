# SPDX-License-Identifier: GPL-3.0-or-later
"""Maya main-menu structure (Modify / Mesh / Edit Mesh / Mesh Tools / Display)
mapped onto Blender operators, exposed as a "Maya" menu in the top bar."""

import bpy


class MAYA_MT_modify(bpy.types.Menu):
    bl_idname = "MAYA_MT_modify"
    bl_label = "Modify"

    def draw(self, context):
        layout = self.layout
        layout.operator("maya.freeze_transforms")
        layout.operator("maya.reset_transforms")
        layout.operator("maya.center_pivot")
        layout.separator()
        layout.operator("maya.group", text="Group (Ctrl+G)")
        layout.operator("maya.parent", text="Parent (P)")
        layout.operator("maya.unparent", text="Unparent (Shift+P)")
        layout.separator()
        layout.operator("maya.delete_history", text="Delete History").keep_deformers = False
        layout.operator("maya.delete_history",
                        text="Delete Non-Deformer History").keep_deformers = True


class MAYA_MT_mesh(bpy.types.Menu):
    bl_idname = "MAYA_MT_mesh"
    bl_label = "Mesh"

    def draw(self, context):
        layout = self.layout
        layout.operator("object.join", text="Combine")
        layout.operator("maya.separate")
        layout.separator()
        layout.operator("maya.poly_smooth")
        layout.operator("object.modifier_add", text="Mirror").type = 'MIRROR'
        layout.operator("object.modifier_add", text="Reduce").type = 'DECIMATE'
        layout.separator()
        layout.operator("mesh.quads_convert_to_tris", text="Triangulate")
        layout.operator("mesh.tris_convert_to_quads", text="Quadrangulate")
        layout.operator("mesh.fill_holes", text="Fill Hole")
        layout.separator()
        layout.operator("object.modifier_add", text="Booleans").type = 'BOOLEAN'


class MAYA_MT_edit_mesh(bpy.types.Menu):
    bl_idname = "MAYA_MT_edit_mesh"
    bl_label = "Edit Mesh"

    def draw(self, context):
        layout = self.layout
        layout.operator("maya.extrude", text="Extrude (Ctrl+E)")
        layout.operator("maya.bevel", text="Bevel (Ctrl+B)")
        layout.operator("mesh.bridge_edge_loops", text="Bridge")
        layout.operator("mesh.poke", text="Poke")
        layout.operator("mesh.inset", text="Inset / Offset")
        layout.separator()
        layout.operator("mesh.remove_doubles", text="Merge")
        layout.operator("mesh.merge", text="Merge To Center").type = 'CENTER'
        layout.operator("mesh.merge", text="Collapse").type = 'COLLAPSE'
        layout.separator()
        layout.operator("mesh.split", text="Detach")
        layout.operator("mesh.separate", text="Extract").type = 'SELECTED'
        layout.operator("mesh.duplicate_move", text="Duplicate")
        layout.separator()
        layout.operator("maya.delete_components", text="Delete Edge/Vertex").clean = True
        layout.operator("mesh.edge_rotate", text="Spin Edge Forward").use_ccw = False
        layout.operator("mesh.edge_rotate", text="Spin Edge Backward").use_ccw = True


class MAYA_MT_mesh_tools(bpy.types.Menu):
    bl_idname = "MAYA_MT_mesh_tools"
    bl_label = "Mesh Tools"

    def draw(self, context):
        layout = self.layout
        for tool, text in (("KNIFE", "Multi-Cut (Ctrl+Shift+X)"),
                           ("LOOP_CUT", "Insert Edge Loop"),
                           ("POLY_BUILD", "Quad Draw (Ctrl+Shift+Q)")):
            layout.operator("maya.mesh_tool", text=text).tool = tool
        layout.operator("mesh.offset_edge_loops_slide", text="Offset Edge Loop")
        layout.operator("transform.edge_slide", text="Slide Edge")


class MAYA_MT_display(bpy.types.Menu):
    bl_idname = "MAYA_MT_display"
    bl_label = "Display"

    def draw(self, context):
        layout = self.layout
        layout.operator("maya.smooth_preview", text="Smooth Preview Off (1)").mode = 1
        layout.operator("maya.smooth_preview", text="Cage + Smooth (2)").mode = 2
        layout.operator("maya.smooth_preview", text="Smooth Preview (3)").mode = 3
        layout.separator()
        layout.operator("maya.visibility", text="Hide Selection (Ctrl+H)").action = 'HIDE'
        layout.operator("maya.visibility", text="Show Last Hidden (Ctrl+Shift+H)").action = 'SHOW_LAST'
        layout.operator("maya.visibility", text="Hide Unselected (Alt+H)").action = 'HIDE_UNSELECTED'
        layout.operator("maya.visibility", text="Show All").action = 'SHOW_ALL'
        layout.separator()
        layout.operator("view3d.localview", text="Isolate Select (Ctrl+1)")


class MAYA_MT_main(bpy.types.Menu):
    bl_idname = "MAYA_MT_main"
    bl_label = "Maya"

    def draw(self, context):
        layout = self.layout
        layout.menu("MAYA_MT_modify")
        layout.menu("MAYA_MT_display")
        layout.separator()
        layout.menu("MAYA_MT_mesh")
        layout.menu("MAYA_MT_edit_mesh")
        layout.menu("MAYA_MT_mesh_tools")
        layout.separator()
        layout.operator("maya.apply_setup", icon='PREFERENCES')


def draw_topbar(self, context):
    self.layout.menu("MAYA_MT_main")


classes = (
    MAYA_MT_modify,
    MAYA_MT_mesh,
    MAYA_MT_edit_mesh,
    MAYA_MT_mesh_tools,
    MAYA_MT_display,
    MAYA_MT_main,
)


def register():
    bpy.types.TOPBAR_MT_editor_menus.append(draw_topbar)


def unregister():
    bpy.types.TOPBAR_MT_editor_menus.remove(draw_topbar)
