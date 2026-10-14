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
        return f"{name}  (Blender: {target})\nShift+Click: option box"

    def invoke(self, context, event):
        if event.shift or event.ctrl:
            self.options = True
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

# Blender built-in icons for Maya commands, by exact name first, then by the
# first keyword found in the command name. Commands with no fitting Blender
# icon stay text-only.
ICON_EXACT = {
    "CreatePolygonSphere": 'MESH_UVSPHERE', "CreatePolygonCube": 'MESH_CUBE',
    "CreatePolygonCylinder": 'MESH_CYLINDER', "CreatePolygonCone": 'MESH_CONE',
    "CreatePolygonTorus": 'MESH_TORUS', "CreatePolygonPlane": 'MESH_GRID',
    "CreatePolygonDisc": 'MESH_CIRCLE', "CreatePolygonPlatonic": 'MESH_ICOSPHERE',
    "CreatePolygonSoccerBall": 'MESH_ICOSPHERE', "CreatePolygonPyramid": 'MESH_CONE',
    "CreatePolygonPrism": 'MESH_CYLINDER', "CreateNURBSSphere": 'SURFACE_NSPHERE',
    "CreateNURBSCylinder": 'SURFACE_NCYLINDER', "CreateNURBSTorus": 'SURFACE_NTORUS',
    "CreateNURBSPlane": 'SURFACE_NSURFACE', "CreateNURBSCircle": 'CURVE_NCIRCLE',
    "CreateNURBSSquare": 'CURVE_NCIRCLE', "CreateLocator": 'EMPTY_AXIS',
    "CreateEmptyGroup": 'EMPTY_AXIS', "CreatePolygonType": 'FONT_DATA',
    "NextKey": 'NEXT_KEYFRAME', "PreviousKey": 'PREV_KEYFRAME',
    "PlaybackForward": 'PLAY', "PlaybackBackward": 'PLAY_REVERSE', "PlaybackStop": 'PAUSE',
    "GoToMinFrame": 'REW', "GoToMaxFrame": 'FF', "NextFrame": 'FRAME_NEXT',
    "PreviousFrame": 'FRAME_PREV', "Undo": 'LOOP_BACK', "Redo": 'LOOP_FORWARDS',
    "NewScene": 'FILE_NEW', "OpenScene": 'FILE_FOLDER', "SaveScene": 'FILE_TICK',
    "SaveSceneAs": 'FILE_TICK', "Import": 'IMPORT', "Export": 'EXPORT',
    "ExportSelection": 'EXPORT', "Quit": 'QUIT', "MoveTool": 'OBJECT_ORIGIN',
    "SelectToggleMode": 'OBJECT_DATAMODE', "SelectVertexMask": 'VERTEXSEL',
    "SelectEdgeMask": 'EDGESEL', "SelectFacetMask": 'FACESEL', "SelectUVMask": 'UV',
    "MultiCutTool": 'MOD_EDGESPLIT', "QuadDrawTool": 'MESH_GRID',
    "SplitEdgeRingTool": 'MOD_MULTIRES', "GraphEditor": 'GRAPH',
    "DopeSheetEditor": 'ACTION', "OutlinerWindow": 'OUTLINER', "AttributeEditor": 'PROPERTIES',
    "ScriptEditor": 'TEXT', "CommandShell": 'CONSOLE', "TextureViewWindow": 'UV',
    "PreferencesWindow": 'PREFERENCES', "HotkeyPreferencesWindow": 'KEYINGSET',
    "PluginManager": 'PLUGIN', "PlayblastWindow": 'RENDER_ANIMATION',
}
ICON_KEYWORDS = (
    ("Boolean", 'MOD_BOOLEAN'), ("Combine", 'AUTOMERGE_ON'), ("Separate", 'UNLINKED'),
    ("ShrinkWrap", 'MOD_SHRINKWRAP'), ("Wrap", 'MOD_MESHDEFORM'), ("Lattice", 'MOD_LATTICE'),
    ("BlendShape", 'SHAPEKEY_DATA'), ("Cluster", 'HOOK'), ("Bend", 'MOD_SIMPLEDEFORM'),
    ("Twist", 'MOD_SIMPLEDEFORM'), ("Flare", 'MOD_SIMPLEDEFORM'), ("Squash", 'MOD_SIMPLEDEFORM'),
    ("Sine", 'MOD_WAVE'), ("Wave", 'MOD_WAVE'), ("DeltaMush", 'MOD_SMOOTH'),
    ("Mirror", 'MOD_MIRROR'), ("Bevel", 'MOD_BEVEL'), ("Chamfer", 'MOD_BEVEL'),
    ("Extrude", 'MOD_SOLIDIFY'), ("Solidify", 'MOD_SOLIDIFY'), ("Triangulate", 'MOD_TRIANGULATE'),
    ("Reduce", 'MOD_DECIM'), ("Remesh", 'MOD_REMESH'), ("Smooth", 'MOD_SMOOTH'),
    ("Merge", 'AUTOMERGE_ON'), ("Collapse", 'AUTOMERGE_ON'), ("Bridge", 'MOD_WIREFRAME'),
    ("Poke", 'DECORATE'), ("Subdivide", 'MOD_SUBSURF'), ("Subdiv", 'MOD_SUBSURF'),
    ("Normal", 'NORMALS_FACE'), ("Harden", 'SHARPCURVE'), ("Soften", 'SMOOTHCURVE'),
    ("UV", 'UV'), ("Joint", 'BONE_DATA'), ("IK", 'CON_KINEMATIC'),
    ("Skin", 'MOD_ARMATURE'), ("Weight", 'MOD_VERTEX_WEIGHT'), ("Influence", 'GROUP_VERTEX'),
    ("ParentConstraint", 'CON_CHILDOF'), ("PointConstraint", 'CON_LOCLIKE'),
    ("OrientConstraint", 'CON_ROTLIKE'), ("ScaleConstraint", 'CON_SIZELIKE'),
    ("AimConstraint", 'CON_TRACKTO'), ("Constraint", 'CONSTRAINT'),
    ("SetKey", 'KEY_HLT'), ("InsertKey", 'KEY_HLT'), ("DeleteKeys", 'KEY_DEHLT'),
    ("Light", 'LIGHT'), ("Camera", 'CAMERA_DATA'), ("Bezier", 'CURVE_BEZCURVE'),
    ("Curve", 'CURVE_DATA'), ("Surface", 'SURFACE_DATA'), ("Sculpt", 'SCULPTMODE_HLT'),
    ("SetMesh", 'BRUSH_DATA'), ("Paint", 'BRUSH_DATA'), ("Hair", 'CURVES_DATA'),
    ("Cloth", 'MOD_CLOTH'), ("Particle", 'PARTICLES'), ("Emit", 'PARTICLES'),
    ("Fluid", 'MOD_FLUIDSIM'), ("Ocean", 'MOD_OCEAN'), ("Smoke", 'MOD_FLUIDSIM'),
    ("Fire", 'MOD_FLUIDSIM'), ("RigidBody", 'RIGID_BODY'), ("Collide", 'MOD_PHYSICS'),
    ("SoftBody", 'MOD_SOFT'), ("Turbulence", 'FORCE_TURBULENCE'), ("Vortex", 'FORCE_VORTEX'),
    ("Drag", 'FORCE_DRAG'), ("Air", 'FORCE_WIND'), ("Uniform", 'FORCE_WIND'),
    ("Newton", 'FORCE_FORCE'), ("Radial", 'FORCE_FORCE'), ("Gravity", 'FORCE_FORCE'),
    ("Cache", 'DISK_DRIVE'), ("Delete", 'X'), ("Duplicate", 'DUPLICATE'),
    ("Ungroup", 'GROUP'), ("Group", 'GROUP'), ("Unparent", 'UNLINKED'), ("Parent", 'LINKED'),
    ("Freeze", 'FREEZE'), ("Reset", 'LOOP_BACK'), ("Pivot", 'PIVOT_BOUNDBOX'),
    ("Snap", 'SNAP_ON'), ("Align", 'ALIGN_CENTER'), ("Hide", 'HIDE_ON'), ("Show", 'HIDE_OFF'),
    ("Frame", 'ZOOM_SELECTED'), ("Grid", 'GRID'), ("Template", 'RESTRICT_SELECT_ON'),
    ("BoundingBox", 'SHADING_BBOX'), ("Toggle", 'CHECKBOX_HLT'), ("Select", 'RESTRICT_SELECT_OFF'),
    ("Convert", 'FILE_REFRESH'), ("Window", 'WINDOW'), ("Editor", 'WINDOW'),
)
_valid_icons = None


def command_icon(command):
    global _valid_icons
    if _valid_icons is None:
        _valid_icons = set(bpy.types.UILayout.bl_rna.functions["operator"]
                           .parameters["icon"].enum_items.keys())
    icon = ICON_EXACT.get(command)
    if icon is None:
        icon = next((i for key, i in ICON_KEYWORDS if key in command), 'NONE')
    return icon if icon in _valid_icons else 'NONE'


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
            # One button per line: Blender menus break apart rows of buttons,
            # so the option box is "label □" and opens with Shift+click.
            _, label, command, has_options = item
            available = command in ACTIONS
            col = layout.column()
            col.enabled = available
            text = f"{label}   □" if has_options else label
            op = col.operator("maya.run", text=text, emboss=False,
                              icon=command_icon(command) if available else 'NONE')
            op.command = command
            op.label = label


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
    sub = layout.row()
    sub.ui_units_x = 6
    sub.prop(wm, "maya_menu_set", text="")
    for title, _items in MENU_SETS["Common"]:
        layout.menu(MENU_IDS[("Common", title)], text=title)
    layout.separator(type='LINE')
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
    layout.separator(type='LINE')
    if context.screen.show_fullscreen:
        layout.operator("screen.back_to_previous", icon='SCREEN_BACK', text="Back to Previous")
        return
    # Maya shows one workspace selector instead of a row of tabs.
    row = layout.row(align=True)
    row.label(text="Workspace:")
    sub = row.row(align=True)
    sub.ui_units_x = 8
    sub.template_ID(context.window, "workspace", new="workspace.add")


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
    ob = context.active_object
    if context.mode == 'EDIT_MESH' and ob is not None and ob.type == 'MESH':
        row.prop(ob, "use_mesh_mirror_x", text="Sym X", toggle=True)

    # Selection mask by object type (Maya's status-line mask buttons).
    view = _find_area(context, 'VIEW_3D')
    if view is not None:
        space = view.spaces.active
        row = layout.row(align=True)
        for prop, icon in SELECT_MASKS:
            if hasattr(space, prop):
                row.prop(space, prop, text="", icon=icon)


SELECT_MASKS = (
    ("show_object_select_mesh", 'OUTLINER_OB_MESH'),
    ("show_object_select_curve", 'OUTLINER_OB_CURVE'),
    ("show_object_select_surf", 'OUTLINER_OB_SURFACE'),
    ("show_object_select_armature", 'OUTLINER_OB_ARMATURE'),
    ("show_object_select_lattice", 'OUTLINER_OB_LATTICE'),
    ("show_object_select_empty", 'OUTLINER_OB_EMPTY'),
    ("show_object_select_light", 'OUTLINER_OB_LIGHT'),
    ("show_object_select_camera", 'OUTLINER_OB_CAMERA'),
)

# Words dropped from shelf button labels so the shelf stays compact.
SHELF_TRIM = ("Polygon ", "NURBS ", " Tool", "Create ", "...")


def _shelf_label(label):
    for word in SHELF_TRIM:
        label = label.replace(word, "")
    return label.strip() or label


def draw_shelf(layout, context):
    wm = context.window_manager
    sub = layout.row()
    sub.ui_units_x = 6
    sub.prop(wm, "maya_shelf", text="")
    row = layout.row(align=True)
    for name, buttons in SHELVES:
        if name != wm.maya_shelf:
            continue
        for label, command in buttons:
            available = command in ACTIONS
            cell = row.row(align=True)
            cell.enabled = available
            op = cell.operator("maya.run", text=_shelf_label(label),
                               icon=command_icon(command) if available else 'NONE')
            op.command = command
            op.label = label


_original_info_draw = None


def _info_header_draw(self, context):
    """The thin Info strip above the viewport becomes the status line + shelf;
    a normal-sized Info editor keeps its own header."""
    area = context.area
    is_strip = area is not None and area.height < 80
    if not (is_strip and _pref(context, "use_maya_shelf")):
        return _original_info_draw(self, context)
    layout = self.layout
    draw_status_line(layout, context)
    layout.separator(type='LINE')
    draw_shelf(layout, context)


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
# Viewport camera name at the bottom centre ("persp", "top", "front", "side")
# --------------------------------------------------------------------------

_view_label_handle = None


def view_name(rv3d, scene=None):
    if rv3d.view_perspective == 'CAMERA':
        cam = scene.camera if scene else None
        return cam.name if cam else "camera"
    if rv3d.is_perspective:
        return "persp"
    from mathutils import Vector
    look = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
    for direction, name in (((0, 0, -1), "top"), ((0, 0, 1), "bottom"), ((0, 1, 0), "front"),
                            ((0, -1, 0), "back"), ((-1, 0, 0), "side"), ((1, 0, 0), "left")):
        if look.dot(Vector(direction)) > 0.999:
            return name
    return "ortho"


def _draw_view_label():
    context = bpy.context
    if not _pref(context, "use_maya_menubar"):
        return
    import blf
    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None:
        return
    text = view_name(rv3d, context.scene)
    font = 0
    blf.size(font, 13 * context.preferences.system.ui_scale)
    width, _height = blf.dimensions(font, text)
    blf.position(font, (region.width - width) / 2, 12 * context.preferences.system.ui_scale, 0)
    blf.color(font, 0.85, 0.85, 0.85, 0.9)
    blf.draw(font, text)


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
        active_set = context.window_manager.maya_menu_set
        col = layout.column(align=True)
        rows = [("", "Common")] + [(name, name) for name, _l, _h in MENU_SET_ITEMS]
        for label, menu_set in rows:
            split = col.split(factor=0.1)
            name = split.row()
            name.alignment = 'RIGHT'
            name.label(text=label, icon='RIGHTARROW' if menu_set == active_set else 'NONE')
            row = split.row(align=True)
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


def _open_channel_box_tab(view, attempts=10):
    """Show the Channel Box tab in the viewport sidebar. The tab list only
    exists after the sidebar has drawn once, so retry briefly."""
    def attempt():
        nonlocal attempts
        try:
            sidebar = next((r for r in view.regions if r.type == 'UI'), None)
            if sidebar is not None:
                sidebar.active_panel_category = "Channel Box"
                return None
        except AttributeError:
            return None  # not settable in this Blender version
        except (TypeError, ReferenceError):
            pass
        attempts -= 1
        return 0.2 if attempts > 0 else None
    if attempt() is not None:
        bpy.app.timers.register(attempt, first_interval=0.2)


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
        # Maya's viewport: no navigation buttons, view name drawn at the bottom.
        space.show_gizmo_navigate = False
        space.overlay.show_text = False
        _open_channel_box_tab(view)
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
    global _original_draw_left, _original_info_draw
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
    _original_info_draw = bpy.types.INFO_HT_header.draw
    bpy.types.INFO_HT_header.draw = _info_header_draw
    bpy.types.VIEW3D_MT_editor_menus.append(_draw_view_menus)
    bpy.types.WindowManager.maya_command = StringProperty(
        name="Command Line", description="Python command; press Enter to run",
        update=_run_command_line, options={'SKIP_SAVE'})
    bpy.types.WindowManager.maya_command_result = StringProperty(options={'SKIP_SAVE'})
    bpy.types.STATUSBAR_HT_header.prepend(_draw_command_line)
    global _view_label_handle
    _view_label_handle = bpy.types.SpaceView3D.draw_handler_add(
        _draw_view_label, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    global _original_draw_left, _original_info_draw
    global _view_label_handle
    if _view_label_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_view_label_handle, 'WINDOW')
        _view_label_handle = None
    bpy.types.STATUSBAR_HT_header.remove(_draw_command_line)
    del bpy.types.WindowManager.maya_command
    del bpy.types.WindowManager.maya_command_result
    bpy.types.VIEW3D_MT_editor_menus.remove(_draw_view_menus)
    if _original_info_draw is not None:
        bpy.types.INFO_HT_header.draw = _original_info_draw
        _original_info_draw = None
    if _original_draw_left is not None:
        bpy.types.TOPBAR_HT_upper_bar.draw_left = _original_draw_left
        _original_draw_left = None
    for cls in reversed(_menu_classes):
        bpy.utils.unregister_class(cls)
    _menu_classes.clear()
    MENU_IDS.clear()
    del bpy.types.WindowManager.maya_menu_set
    del bpy.types.WindowManager.maya_shelf
