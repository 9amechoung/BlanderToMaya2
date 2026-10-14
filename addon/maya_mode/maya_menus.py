# SPDX-License-Identifier: GPL-3.0-or-later
"""Maya main menu bar: File Edit Create Select Modify Display Windows plus
the menus of the active menu set (Modeling / Rigging / Animation / FX).

Menus are generated from menu_data.MENU_SETS; each item runs its Maya
command through MAYA_OT_run, which looks the command up in actions.ACTIONS.
Commands without a Blender equivalent are shown greyed out, as Maya does
for unavailable items. An option box runs the command and then opens
Blender's "Adjust Last Operation" panel (Blender's option window).
"""

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

from .actions import ACTIONS
from .menu_data import MENU_SETS

MENU_SET_ITEMS = (
    ('Modeling', "Modeling", "F2"),
    ('Rigging', "Rigging", "F3"),
    ('Animation', "Animation", "F4"),
    ('FX', "FX", "F5"),
)

# (menu set, title) -> generated Menu idname; filled by register().
MENU_IDS = {}
_menu_classes = []
_original_draw_left = None


# --------------------------------------------------------------------------
# Running a Maya command
# --------------------------------------------------------------------------

def _find_area(context, area_type):
    if context.area is not None and context.area.type == area_type:
        return context.area
    screen = context.window.screen if context.window else None
    areas = [a for a in (screen.areas if screen else ()) if a.type == area_type]
    return max(areas, key=lambda a: a.width * a.height) if areas else None


def _call_op(idname, props, mode='INVOKE_DEFAULT'):
    module, name = idname.split(".")
    getattr(getattr(bpy.ops, module), name)(mode, **props)


def _toggle(space, path):
    *parents, attr = path.split(".")
    owner = space
    for part in parents:
        owner = getattr(owner, part)
    setattr(owner, attr, not getattr(owner, attr))


def _open_editor(context, ui_type):
    before = set(context.window_manager.windows)
    bpy.ops.wm.window_new()
    new = [w for w in context.window_manager.windows if w not in before]
    if new:
        new[0].screen.areas[0].ui_type = ui_type


def run_command(context, name, options=False):
    """Run Maya command `name`. Returns an error message or None."""
    spec = ACTIONS.get(name)
    if spec is None:
        return "No Blender equivalent"
    if context.mode != 'OBJECT' and "edit" in spec:
        spec = spec["edit"]
    if "editor" in spec:
        _open_editor(context, spec["editor"])
        return None

    area = _find_area(context, spec.get("area", 'VIEW_3D'))
    override = {}
    if area is not None:
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        override = {"area": area, "region": region}
    elif "area" in spec:
        return f"Open a {spec['area'].replace('_', ' ').title()} first"

    with context.temp_override(**override):
        if "tool" in spec:
            bpy.ops.wm.tool_set_by_id(name=spec["tool"])
        elif "toggle" in spec:
            if area is None:
                return "Needs a 3D viewport"
            _toggle(area.spaces.active, spec["toggle"])
        else:
            active = context.view_layer.objects.active if context.view_layer else None
            if spec.get("mesh") and context.mode == 'OBJECT' and active and active.type == 'MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                try:
                    _call_op(spec["op"], spec["props"], 'EXEC_DEFAULT')
                finally:
                    bpy.ops.object.mode_set(mode='OBJECT')
            else:
                _call_op(spec["op"], spec["props"])
            if options:
                bpy.ops.screen.redo_last('INVOKE_DEFAULT')
    return None


class MAYA_OT_run(bpy.types.Operator):
    """Run a Maya menu command"""
    bl_idname = "maya.run"
    bl_label = "Maya Command"

    command: StringProperty()
    label: StringProperty(options={'SKIP_SAVE'})
    options: BoolProperty(options={'SKIP_SAVE'}, description="Show the option window")

    @classmethod
    def description(cls, context, props):
        spec = ACTIONS.get(props.command)
        name = props.label or props.command
        if spec is None:
            return f"{name}: no Blender equivalent"
        target = spec.get("op") or spec.get("tool") or spec.get("toggle") or spec.get("editor")
        return f"{name}  (Blender: {target})"

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        try:
            error = run_command(context, self.command, self.options)
        except (RuntimeError, TypeError, ValueError, AttributeError) as err:
            text = str(err).strip()
            error = text.splitlines()[-1] if text else repr(err)
        if error:
            self.report({'WARNING'}, f"{self.label or self.command}: {error}")
            return {'CANCELLED'}
        return {'FINISHED'}


# --------------------------------------------------------------------------
# Generated menus
# --------------------------------------------------------------------------

def _draw_items(layout, items, submenu_ids):
    for item in items:
        kind = item[0]
        if kind == "-":
            layout.separator()
            if item[1]:
                layout.label(text=item[1])
        elif kind == "s":
            layout.menu(submenu_ids[id(item)], text=item[1])
        else:
            _, label, command, has_options = item
            row = layout.row(align=True)
            row.enabled = command in ACTIONS
            op = row.operator("maya.run", text=label)
            op.command = command
            op.label = label
            if has_options:
                op = row.operator("maya.run", text="", icon='OPTIONS')
                op.command = command
                op.label = label
                op.options = True


def _make_menu(idname, title, items, submenu_ids):
    def draw(self, context):
        _draw_items(self.layout, items, submenu_ids)
    return type(idname, (bpy.types.Menu,), {
        "bl_idname": idname, "bl_label": title, "draw": draw,
    })


def _build_classes():
    classes = []
    counter = [0]

    def build(title, items):
        submenu_ids = {}
        for item in items:
            if item[0] == "s":
                submenu_ids[id(item)] = build(item[1], item[2])
        counter[0] += 1
        idname = f"MAYA_MT_menu_{counter[0]}"
        classes.append(_make_menu(idname, title, items, submenu_ids))
        return idname

    for menu_set, menus in MENU_SETS.items():
        for title, items in menus:
            MENU_IDS[(menu_set, title)] = build(title, items)
    return classes


class MAYA_MT_blender_menus(bpy.types.Menu):
    """Blender's own main menus, kept one click away"""
    bl_idname = "MAYA_MT_blender_menus"
    bl_label = "Blender"

    def draw(self, context):
        layout = self.layout
        for idname, text in (("TOPBAR_MT_blender", "Blender"), ("TOPBAR_MT_file", "File"),
                             ("TOPBAR_MT_edit", "Edit"), ("TOPBAR_MT_render", "Render"),
                             ("TOPBAR_MT_window", "Window"), ("TOPBAR_MT_help", "Help")):
            layout.menu(idname, text=text)
        layout.separator()
        layout.menu("MAYA_MT_main", text="Maya Mode")


def draw_maya_menubar(layout, context):
    wm = context.window_manager
    layout.menu("MAYA_MT_blender_menus", text="", icon='BLENDER')
    layout.prop(wm, "maya_menu_set", text="")
    for title, _items in MENU_SETS["Common"]:
        layout.menu(MENU_IDS[("Common", title)], text=title)
    layout.separator()
    for title, _items in MENU_SETS[wm.maya_menu_set]:
        layout.menu(MENU_IDS[(wm.maya_menu_set, title)], text=title)


def _draw_left(self, context):
    addon = context.preferences.addons.get(__package__)
    if addon is None or not addon.preferences.use_maya_menubar:
        return _original_draw_left(self, context)
    layout = self.layout
    draw_maya_menubar(layout, context)
    layout.separator()
    if not context.screen.show_fullscreen:
        layout.template_ID_tabs(context.window, "workspace", new="workspace.add",
                                menu="TOPBAR_MT_workspace_menu")
    else:
        layout.operator("screen.back_to_previous", icon='SCREEN_BACK', text="Back to Previous")


classes = (
    MAYA_OT_run,
    MAYA_MT_blender_menus,
)


def register():
    global _original_draw_left
    bpy.types.WindowManager.maya_menu_set = EnumProperty(
        name="Menu Set", items=MENU_SET_ITEMS, default='Modeling',
        description="Maya menu set (F2 Modeling, F3 Rigging, F4 Animation, F5 FX)")
    _menu_classes[:] = _build_classes()
    for cls in _menu_classes:
        bpy.utils.register_class(cls)
    topbar = bpy.types.TOPBAR_HT_upper_bar
    _original_draw_left = topbar.draw_left
    topbar.draw_left = _draw_left


def unregister():
    global _original_draw_left
    if _original_draw_left is not None:
        bpy.types.TOPBAR_HT_upper_bar.draw_left = _original_draw_left
        _original_draw_left = None
    for cls in reversed(_menu_classes):
        bpy.utils.unregister_class(cls)
    _menu_classes.clear()
    MENU_IDS.clear()
    del bpy.types.WindowManager.maya_menu_set
