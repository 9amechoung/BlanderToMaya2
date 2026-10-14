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
from .menu_data import MENU_SETS, SHELVES

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


def _pref(context, name):
    """Add-on preference, defaulting to on when the add-on runs unregistered
    in preferences (e.g. loaded from a script)."""
    addon = context.preferences.addons.get(__package__)
    return getattr(addon.preferences, name, True) if addon else True


def _draw_left(self, context):
    if not _pref(context, "use_maya_menubar"):
        return _original_draw_left(self, context)
    layout = self.layout
    draw_maya_menubar(layout, context)
    layout.separator()
    if not context.screen.show_fullscreen:
        layout.template_ID_tabs(context.window, "workspace", new="workspace.add",
                                menu="TOPBAR_MT_workspace_menu")
    else:
        layout.operator("screen.back_to_previous", icon='SCREEN_BACK', text="Back to Previous")


# --------------------------------------------------------------------------
# Status line + shelf (drawn in the header of a thin Info area at the top)
# --------------------------------------------------------------------------

def draw_status_line(layout, context):
    ts = context.tool_settings
    row = layout.row(align=True)
    op = row.operator("maya.component_mode", text="", icon='OBJECT_DATAMODE',
                      depress=context.mode == 'OBJECT')
    op.mode = 'OBJECT'
    for mode, icon, index in (('VERT', 'VERTEXSEL', 0), ('EDGE', 'EDGESEL', 1),
                              ('FACE', 'FACESEL', 2)):
        op = row.operator("maya.component_mode", text="", icon=icon,
                          depress=context.mode == 'EDIT_MESH' and ts.mesh_select_mode[index])
        op.mode = mode
    row = layout.row(align=True)
    row.prop(ts, "use_snap", text="", icon='SNAP_OFF' if not ts.use_snap else 'SNAP_ON')
    for element, icon in (('GRID', 'SNAP_GRID'), ('EDGE', 'SNAP_EDGE'),
                          ('VERTEX', 'SNAP_VERTEX'), ('FACE_PROJECT', 'SNAP_FACE'), ('FACE', 'SNAP_FACE')):
        if element in ts.bl_rna.properties["snap_elements"].enum_items:
            row.prop_enum(ts, "snap_elements", element, text="", icon=icon)
    row = layout.row(align=True)
    prop = "use_proportional_edit_objects" if context.mode == 'OBJECT' else "use_proportional_edit"
    row.prop(ts, prop, text="Soft", toggle=True)


def draw_shelf(layout, context):
    wm = context.window_manager
    layout.prop(wm, "maya_shelf", text="")
    row = layout.row(align=True)
    for name, buttons in SHELVES:
        if name != wm.maya_shelf:
            continue
        for label, command in buttons:
            sub = row.row(align=True)
            sub.enabled = command in ACTIONS
            op = sub.operator("maya.run", text=label)
            op.command = command
            op.label = label


def _draw_info_header(self, context):
    if not _pref(context, "use_maya_shelf"):
        return
    draw_status_line(self.layout, context)
    self.layout.separator()
    draw_shelf(self.layout, context)
    self.layout.separator()


# --------------------------------------------------------------------------
# Viewport panel menus (Maya: View / Shading / Lighting / Show / Panels)
# --------------------------------------------------------------------------

SHOW_TYPES = (
    ("show_object_viewport_mesh", "Polygons"), ("show_object_viewport_surf", "NURBS Surfaces"),
    ("show_object_viewport_curve", "NURBS Curves"), ("show_object_viewport_curves", "Hair"),
    ("show_object_viewport_font", "Text"), ("show_object_viewport_meta", "Metaballs"),
    ("show_object_viewport_pointcloud", "Particles"), ("show_object_viewport_volume", "Volumes"),
    ("show_object_viewport_armature", "Joints"), ("show_object_viewport_lattice", "Deformers"),
    ("show_object_viewport_empty", "Locators"), ("show_object_viewport_light", "Lights"),
    ("show_object_viewport_light_probe", "Light Probes"), ("show_object_viewport_camera", "Cameras"),
    ("show_object_viewport_grease_pencil", "Grease Pencil"),
)


class MAYA_MT_view_shading(bpy.types.Menu):
    bl_idname = "MAYA_MT_view_shading"
    bl_label = "Shading"

    def draw(self, context):
        layout = self.layout
        space = context.space_data
        for mode, text in (('WIRE', "Wireframe"), ('SHADED', "Smooth Shade All"),
                           ('TEXTURED', "Hardware Texturing")):
            layout.operator("maya.shading", text=text).mode = mode
        layout.operator("maya.display_type", text="Bounding Box").display = 'BOUNDS'
        layout.separator()
        layout.prop(space.overlay, "show_wireframes", text="Wireframe on Shaded")
        layout.prop(space.shading, "show_xray", text="X-Ray")
        layout.prop(space.shading, "show_backface_culling", text="Backface Culling")
        layout.prop(space.overlay, "show_face_orientation", text="Face Orientation")
        layout.separator()
        layout.operator("maya.smooth_preview", text="Smooth Mesh Preview").mode = 3


class MAYA_MT_view_lighting(bpy.types.Menu):
    bl_idname = "MAYA_MT_view_lighting"
    bl_label = "Lighting"

    def draw(self, context):
        layout = self.layout
        shading = context.space_data.shading
        layout.operator("maya.shading", text="Use Default Lighting").mode = 'SHADED'
        layout.operator("maya.shading", text="Use All Lights").mode = 'LIGHTS'
        layout.separator()
        if shading.type == 'SOLID':
            layout.prop(shading, "show_shadows", text="Shadows")
            layout.prop(shading, "show_cavity", text="Ambient Occlusion")
        layout.prop(shading, "use_scene_world", text="Use Scene World")


class MAYA_MT_view_show(bpy.types.Menu):
    bl_idname = "MAYA_MT_view_show"
    bl_label = "Show"

    def draw(self, context):
        layout = self.layout
        space = context.space_data
        layout.operator("maya.view_show_all", text="All").show = True
        layout.operator("maya.view_show_all", text="None").show = False
        layout.separator()
        for prop, text in SHOW_TYPES:
            if hasattr(space, prop):
                layout.prop(space, prop, text=text)
        layout.separator()
        layout.prop(space.overlay, "show_floor", text="Grid")
        layout.prop(space.overlay, "show_cursor", text="3D Cursor")
        layout.prop(space.overlay, "show_object_origins", text="Pivots")
        layout.prop(space, "show_gizmo", text="Manipulators")
        layout.prop(space, "show_region_hud", text="Heads Up Display")


class MAYA_MT_view_panels(bpy.types.Menu):
    bl_idname = "MAYA_MT_view_panels"
    bl_label = "Panels"

    def draw(self, context):
        layout = self.layout
        for view, text in (('PERSP', "Perspective"), ('TOP', "Top"), ('FRONT', "Front"),
                           ('RIGHT', "Side")):
            layout.operator("maya.set_view", text=text).view = view
        layout.operator("view3d.view_camera", text="Look Through Selected Camera")
        layout.separator()
        layout.operator("screen.region_quadview", text="Layouts: Four Panes")
        layout.operator("screen.screen_full_area", text="Maximize Panel")
        layout.separator()
        layout.menu("MAYA_MT_hotbox_panels", text="Panel")


class MAYA_OT_view_show_all(bpy.types.Operator):
    """Show > All / None for object types in this viewport"""
    bl_idname = "maya.view_show_all"
    bl_label = "Show Object Types"

    show: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return context.space_data is not None and context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        for prop, _text in SHOW_TYPES:
            if hasattr(context.space_data, prop):
                setattr(context.space_data, prop, self.show)
        return {'FINISHED'}


def _draw_view_menus(self, context):
    if not _pref(context, "use_maya_menubar"):
        return
    layout = self.layout
    for idname in ("MAYA_MT_view_shading", "MAYA_MT_view_lighting", "MAYA_MT_view_show",
                   "MAYA_MT_view_panels"):
        layout.menu(idname)


# --------------------------------------------------------------------------
# Command line (status bar): run a Python line, like Maya's command line
# --------------------------------------------------------------------------

_command_namespace = {}


def _run_command_line(self, context):
    text = self.maya_command.strip()
    if not text:
        return
    namespace = _command_namespace
    namespace.setdefault("bpy", bpy)
    namespace["C"] = bpy.context
    namespace["D"] = bpy.data
    try:
        try:
            result = eval(compile(text, "<Maya command line>", "eval"), namespace)
            message = "" if result is None else repr(result)
        except SyntaxError:
            exec(compile(text, "<Maya command line>", "exec"), namespace)
            message = ""
        context.window_manager.maya_command_result = message or "OK"
    except Exception as err:  # the user's own command: report any failure
        context.window_manager.maya_command_result = f"{type(err).__name__}: {err}"


def _draw_command_line(self, context):
    if not _pref(context, "use_maya_shelf"):
        return
    wm = context.window_manager
    row = self.layout.row(align=True)
    row.label(text="Python")
    row.prop(wm, "maya_command", text="")
    sub = row.row()
    sub.ui_units_x = 14
    sub.label(text=wm.maya_command_result)


class MAYA_PT_hotbox(bpy.types.Panel):
    """Maya hotbox: every menu of every menu set, in rows, under the mouse"""
    bl_idname = "MAYA_PT_hotbox"
    bl_label = "Hotbox"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_ui_units_x = 60

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.alignment = 'CENTER'
        for title, _items in MENU_SETS["Common"]:
            row.menu(MENU_IDS[("Common", title)], text=title)
        for menu_set, _label, _hint in MENU_SET_ITEMS:
            row = col.row(align=True)
            row.alignment = 'CENTER'
            row.label(text=menu_set + ":")
            for title, _items in MENU_SETS[menu_set]:
                row.menu(MENU_IDS[(menu_set, title)], text=title)
        layout.separator()
        row = layout.row(align=True)
        row.alignment = 'CENTER'
        for view, text in (('PERSP', "Persp"), ('TOP', "Top"), ('FRONT', "Front"),
                           ('RIGHT', "Side")):
            row.operator("maya.set_view", text=text).view = view
        row.separator()
        for mode, text in (('OBJECT', "Object"), ('VERT', "Vertex"), ('EDGE', "Edge"),
                           ('FACE', "Face"), ('UV', "UV")):
            row.operator("maya.component_mode", text=text).mode = mode
        row.separator()
        row.menu("MAYA_MT_hotbox_panels", text="Panels")
        row.menu("MAYA_MT_hotbox_display", text="Display")


class MAYA_OT_setup_layout(bpy.types.Operator):
    """Arrange the window like Maya: status line and shelf on top,
    channel box on the right of the viewport, time slider at the bottom"""
    bl_idname = "maya.setup_layout"
    bl_label = "Maya Layout"

    def execute(self, context):
        screen = context.window.screen
        views = [a for a in screen.areas if a.type == 'VIEW_3D']
        if not views:
            self.report({'WARNING'}, "No 3D viewport in this workspace")
            return {'CANCELLED'}
        view = max(views, key=lambda a: a.width * a.height)
        # Shelf strip: a thin Info editor directly above the viewport.
        strip = next((a for a in screen.areas if a.type == 'INFO' and a.height < 80
                      and a.x == view.x and a.width == view.width), None)
        if strip is None:
            before = set(screen.areas)
            region = next(r for r in view.regions if r.type == 'WINDOW')
            with context.temp_override(area=view, region=region):
                bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.96)
            new = [a for a in screen.areas if a not in before]
            if new:
                # The split's new area is the thin top part; its size fields
                # aren't valid until the next redraw, so don't sort by them.
                strip = new[0]
                strip.ui_type = 'INFO'
        space = view.spaces.active
        space.show_region_ui = True
        space.show_region_toolbar = True
        space.show_region_tool_header = True
        return {'FINISHED'}


classes = (
    MAYA_OT_run,
    MAYA_MT_blender_menus,
    MAYA_PT_hotbox,
    MAYA_OT_setup_layout,
    MAYA_MT_view_shading,
    MAYA_MT_view_lighting,
    MAYA_MT_view_show,
    MAYA_MT_view_panels,
    MAYA_OT_view_show_all,
)


def register():
    global _original_draw_left
    bpy.types.WindowManager.maya_menu_set = EnumProperty(
        name="Menu Set", items=MENU_SET_ITEMS, default='Modeling',
        description="Maya menu set (F2 Modeling, F3 Rigging, F4 Animation, F5 FX)")
    bpy.types.WindowManager.maya_shelf = EnumProperty(
        name="Shelf", items=[(name, name, "") for name, _b in SHELVES], default='Polygons')
    _menu_classes[:] = _build_classes()
    for cls in _menu_classes:
        bpy.utils.register_class(cls)
    topbar = bpy.types.TOPBAR_HT_upper_bar
    _original_draw_left = topbar.draw_left
    topbar.draw_left = _draw_left
    bpy.types.INFO_HT_header.prepend(_draw_info_header)
    bpy.types.VIEW3D_MT_editor_menus.append(_draw_view_menus)
    bpy.types.WindowManager.maya_command = StringProperty(
        name="Command Line", description="Python command; press Enter to run",
        update=_run_command_line, options={'SKIP_SAVE'})
    bpy.types.WindowManager.maya_command_result = StringProperty(options={'SKIP_SAVE'})
    bpy.types.STATUSBAR_HT_header.prepend(_draw_command_line)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(_draw_command_line)
    del bpy.types.WindowManager.maya_command
    del bpy.types.WindowManager.maya_command_result
    bpy.types.VIEW3D_MT_editor_menus.remove(_draw_view_menus)
    bpy.types.INFO_HT_header.remove(_draw_info_header)
    global _original_draw_left
    if _original_draw_left is not None:
        bpy.types.TOPBAR_HT_upper_bar.draw_left = _original_draw_left
        _original_draw_left = None
    for cls in reversed(_menu_classes):
        bpy.utils.unregister_class(cls)
    _menu_classes.clear()
    MENU_IDS.clear()
    del bpy.types.WindowManager.maya_menu_set
    del bpy.types.WindowManager.maya_shelf
