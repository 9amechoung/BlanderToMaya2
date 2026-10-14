# SPDX-License-Identifier: GPL-3.0-or-later
"""Channel Box / Layer Editor in the 3D view sidebar ("Channels" tab).

Maya shows transform channels, then the SHAPES node, then INPUTS (the
construction history). Blender's closest equivalent of construction history
is the modifier stack, so INPUTS lists modifiers with their editable values.
Animated values get Blender's keyed / animated field colors automatically.
"""

import bpy

AXES = ("X", "Y", "Z")
# Generic modifier properties that are not interesting as "channels".
SKIP_PROPS = {"rna_type", "name", "type", "show_viewport", "show_render",
              "show_in_editmode", "show_on_cage", "show_expanded", "is_active",
              "use_pin_to_last", "is_override_data", "use_apply_on_spline",
              "execution_time", "persistent_uid"}
MAX_INPUT_CHANNELS = 8


def _channel_rows(layout, owner, path, label):
    col = layout.column(align=True)
    for i, axis in enumerate(AXES):
        col.prop(owner, path, index=i, text=f"{label} {axis}")


class VIEW3D_PT_maya_channel_box(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Channels"
    bl_label = "Channel Box"

    def draw(self, context):
        layout = self.layout
        ob = context.active_object
        if ob is None:
            layout.label(text="Nothing selected")
            return
        layout.prop(ob, "name", text="", icon='OBJECT_DATA')

        owner = ob
        if context.mode == 'POSE' and context.active_pose_bone:
            owner = context.active_pose_bone
            layout.label(text=owner.name, icon='BONE_DATA')

        _channel_rows(layout, owner, "location", "Translate")
        if owner.rotation_mode == 'QUATERNION':
            col = layout.column(align=True)
            for i, axis in enumerate("WXYZ"):
                col.prop(owner, "rotation_quaternion", index=i, text=f"Rotate {axis}")
        elif owner.rotation_mode == 'AXIS_ANGLE':
            layout.prop(owner, "rotation_axis_angle", text="Rotate")
        else:
            _channel_rows(layout, owner, "rotation_euler", "Rotate")
        _channel_rows(layout, owner, "scale", "Scale")
        if owner is ob:
            layout.prop(ob, "hide_viewport", text="Visibility", invert_checkbox=True)
        layout.prop(owner, "rotation_mode", text="Rotate Order")

        if ob.data is not None:
            box = layout.box()
            box.label(text="SHAPES")
            box.prop(ob.data, "name", text="",
                     icon='MESH_DATA' if ob.type == 'MESH' else 'DOT')

        if ob.modifiers:
            box = layout.box()
            box.label(text="INPUTS")
            for mod in ob.modifiers:
                self._draw_input(box, mod)

    @staticmethod
    def _draw_input(layout, mod):
        header = layout.row(align=True)
        header.prop(mod, "show_expanded", text="", emboss=False,
                    icon='DISCLOSURE_TRI_DOWN' if mod.show_expanded else 'DISCLOSURE_TRI_RIGHT')
        header.label(text=mod.name)
        header.prop(mod, "show_viewport", text="")
        if not mod.show_expanded:
            return
        col = layout.column(align=True)
        shown = 0
        for prop in mod.bl_rna.properties:
            if shown >= MAX_INPUT_CHANNELS:
                break
            if prop.identifier in SKIP_PROPS or prop.is_readonly:
                continue
            if prop.type not in {'INT', 'FLOAT', 'BOOLEAN'} or getattr(prop, "is_array", False):
                continue
            col.prop(mod, prop.identifier)
            shown += 1


class VIEW3D_PT_maya_layer_editor(bpy.types.Panel):
    """Display layers: top-level collections with visibility / render / select toggles"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Channels"
    bl_label = "Layer Editor"

    def draw(self, context):
        layout = self.layout
        root = context.view_layer.layer_collection
        if not root.children:
            layout.label(text="No layers (collections)")
        for lc in root.children:
            row = layout.row(align=True)
            row.prop(lc, "hide_viewport", text="", emboss=False)
            row.prop(lc.collection, "hide_render", text="", emboss=False)
            row.prop(lc.collection, "hide_select", text="", emboss=False)
            row.label(text=lc.name)


classes = (
    VIEW3D_PT_maya_channel_box,
    VIEW3D_PT_maya_layer_editor,
)
