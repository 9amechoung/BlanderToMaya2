# SPDX-License-Identifier: GPL-3.0-or-later
"""Maya menu command -> Blender action.

Keys are Maya runtime command names (as listed in menu_data.py). A spec is a
dict understood by MAYA_OT_run (maya_menus.py):

    op       Blender operator idname, run with INVOKE_DEFAULT
    props    operator properties
    mesh     True: in object mode, run on the whole mesh (edit mode, select all)
    edit     alternative spec used in edit mode
    tool     toolbar tool id to activate
    toggle   property path on the 3D view space to toggle
    editor   open a new window with this editor (area ui_type)
    area     area type the operator needs (default: 3D view)

Commands missing here are drawn greyed out, like unavailable Maya items.
"""


def O(idname, **props):
    return {"op": idname, "props": props}


def M(idname, **props):
    """Mesh operator that also works from object mode on the whole mesh."""
    return {"op": idname, "props": props, "mesh": True}


def OE(obj_spec, edit_spec):
    spec = dict(obj_spec)
    spec["edit"] = edit_spec
    return spec


def A(idname, area, **props):
    return {"op": idname, "props": props, "area": area}


def T(tool_id):
    return {"tool": tool_id}


def V(path):
    return {"toggle": path}


def W(ui_type):
    return {"editor": ui_type}


def MOD(mod_type, **settings):
    return O("maya.add_modifier", type=mod_type,
             settings=repr(settings) if settings else "")


def CON(con_type):
    return O("maya.add_constraint", type=con_type)


def P(section):
    return O("screen.userpref_show", section=section)


ACTIONS = {}

# --------------------------------------------------------------------------
# Object-type families shared by Select All / Hide / Show / Delete All
# --------------------------------------------------------------------------

TYPE_FAMILIES = {
    "Geometry": "MESH,CURVE,SURFACE,META,FONT,CURVES,POINTCLOUD,VOLUME",
    "PolygonGeometry": "MESH", "PolygonSurfaces": "MESH",
    "NURBSCurves": "CURVE", "NURBSSurfaces": "SURFACE",
    "Joints": "ARMATURE", "Kinematics": "ARMATURE", "IKHandles": "ARMATURE",
    "Lattices": "LATTICE", "Deformers": "LATTICE",
    "Cameras": "CAMERA", "Lights": "LIGHT,LIGHT_PROBE",
    "Transforms": "EMPTY", "Planes": "EMPTY",
    "HairSystems": "CURVES", "Strokes": "GREASEPENCIL",
    "SubdivSurfaces": "MESH",
}
for _family, _types in TYPE_FAMILIES.items():
    ACTIONS["SelectAll" + _family] = O("maya.select_by_type", types=_types)
    ACTIONS["Hide" + _family] = O("maya.show_hide", types=_types, show=False)
    ACTIONS["Show" + _family] = O("maya.show_hide", types=_types, show=True)
    ACTIONS["DeleteAll" + _family] = O("maya.delete_by_type", types=_types)

ACTIONS["HideAll"] = O("maya.show_hide", types="ALL", show=False)
ACTIONS["DeleteAllImagePlanes"] = O("maya.delete_by_type", types="IMAGE")
ACTIONS["SelectAllImagePlanes"] = O("maya.select_by_type", types="IMAGE")

# Simulation and deformer families live on modifiers in Blender.
for _family, _mods in {
    "NCloths": "CLOTH", "Particles": "PARTICLE_SYSTEM", "NParticles": "PARTICLE_SYSTEM",
    "Fluids": "FLUID", "NRigids": "COLLISION", "NonLinearDeformers": "SIMPLE_DEFORM,WAVE",
    "Clusters": "HOOK", "SculptObjects": "CAST", "Wires": "CURVE",
}.items():
    ACTIONS["DeleteAll" + _family] = O("maya.delete_modifiers", types=_mods, all_objects=True)
    ACTIONS["SelectAll" + _family] = O("maya.select_by_modifier", types=_mods)
    ACTIONS["Hide" + _family] = O("maya.show_hide", types="MOD:" + _mods, show=False)
    ACTIONS["Show" + _family] = O("maya.show_hide", types="MOD:" + _mods, show=True)

# --------------------------------------------------------------------------
# File
# --------------------------------------------------------------------------

ACTIONS.update({
    "NewScene": O("wm.read_homefile"),
    "OpenScene": O("wm.open_mainfile"),
    "SaveScene": O("wm.save_mainfile"),
    "SaveSceneAs": O("wm.save_as_mainfile"),
    "IncrementAndSave": O("maya.increment_save"),
    "ArchiveScene": O("file.pack_all"),
    "SavePreferences": O("wm.save_userpref"),
    "OptimizeScene": O("outliner.orphans_purge"),
    "Import": O("wm.call_menu", name="TOPBAR_MT_file_import"),
    "Export": O("wm.call_menu", name="TOPBAR_MT_file_export"),
    "ExportSelection": O("wm.call_menu", name="TOPBAR_MT_file_export"),
    "CreateReference": O("wm.link"),
    "ReferenceEditor": W("OUTLINER"),
    "ViewImage": W("IMAGE_EDITOR"),
    "ViewSequence": O("render.play_rendered_anim"),
    "Quit": O("wm.quit_blender"),
})

# --------------------------------------------------------------------------
# Edit
# --------------------------------------------------------------------------

ACTIONS.update({
    "Undo": O("ed.undo"),
    "Redo": O("ed.redo"),
    "RepeatLast": O("screen.repeat_last"),
    "RecentCommandsWindow": O("screen.repeat_history"),
    "CutSelected": O("maya.cut_selected"),
    "CopySelected": O("view3d.copybuffer"),
    "PasteSelected": O("view3d.pastebuffer"),
    "CutKeys": A("graph.copy", 'GRAPH_EDITOR'),
    "CopyKeys": A("graph.copy", 'GRAPH_EDITOR'),
    "PasteKeys": A("graph.paste", 'GRAPH_EDITOR'),
    "DeleteKeys": O("anim.keyframe_clear_v3d"),
    "SnapKeys": A("graph.snap", 'GRAPH_EDITOR'),
    "Delete": OE(O("object.delete", use_global=False, confirm=False),
                 O("maya.delete_components", clean=True)),
    "DeleteAllHistory": O("maya.delete_history", all_objects=True),
    "BakeAllNonDefHistory": O("maya.delete_history", all_objects=True, keep_deformers=True),
    "DeleteAllChannels": O("maya.delete_all_channels"),
    "DeleteAllStaticChannels": A("graph.clean", 'GRAPH_EDITOR', channels=True),
    "DeleteAllConstraints": O("maya.delete_constraints", all_objects=True),
    "DeleteAllMotionPaths": O("object.paths_clear", only_selected=False),
    "DeleteAllExpressions": O("maya.delete_drivers"),
    "DeleteAllIKHandles": O("maya.delete_constraints", all_objects=True, types="IK,SPLINE_IK"),
    "DeleteAllRigidBodies": O("maya.delete_rigid_bodies"),
    "DeleteAllRigidConstraints": O("maya.delete_rigid_bodies", constraints=True),
    "Duplicate": O("maya.duplicate"),
    "DuplicateSpecial": O("object.duplicate", linked=True),
    "DuplicateWithTransform": O("maya.duplicate_with_transform"),
    "Group": O("maya.group"),
    "Ungroup": O("maya.ungroup"),
    "Parent": O("maya.parent"),
    "Unparent": O("maya.unparent"),
})

# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------

ACTIONS.update({
    "CreateNURBSSphere": O("surface.primitive_nurbs_surface_sphere_add", radius=1.0),
    "CreateNURBSCylinder": O("surface.primitive_nurbs_surface_cylinder_add", radius=1.0),
    "CreateNURBSTorus": O("surface.primitive_nurbs_surface_torus_add", radius=1.0),
    "CreateNURBSPlane": O("surface.primitive_nurbs_surface_surface_add", radius=0.5),
    "CreateNURBSCircle": O("curve.primitive_nurbs_circle_add", radius=1.0),
    "CreatePolygonSphere": O("mesh.primitive_uv_sphere_add", radius=1.0, segments=20, ring_count=20),
    "CreatePolygonCube": O("mesh.primitive_cube_add", size=1.0),
    "CreatePolygonCylinder": O("mesh.primitive_cylinder_add", radius=1.0, depth=2.0, vertices=20),
    "CreatePolygonCone": O("mesh.primitive_cone_add", radius1=1.0, depth=2.0, vertices=20),
    "CreatePolygonTorus": O("mesh.primitive_torus_add", major_radius=1.0, minor_radius=0.5),
    "CreatePolygonPlane": O("mesh.primitive_grid_add", size=1.0, x_subdivisions=10, y_subdivisions=10),
    "CreatePolygonDisc": O("mesh.primitive_circle_add", radius=1.0, fill_type='NGON'),
    "CreatePolygonPlatonic": O("mesh.primitive_ico_sphere_add", radius=1.0, subdivisions=1),
    "CreatePolygonPyramid": O("mesh.primitive_cone_add", radius1=1.0, depth=1.0, vertices=4),
    "CreatePolygonPrism": O("mesh.primitive_cylinder_add", radius=1.0, depth=2.0, vertices=3),
    "CreatePolygonPipe": O("maya.create_pipe"),
    "CreatePolygonHelix": O("maya.create_helix"),
    "CreatePolygonSoccerBall": O("mesh.primitive_ico_sphere_add", radius=1.0, subdivisions=2),
    "CreateSubdivSphere": O("maya.create_subdiv", primitive='SPHERE'),
    "CreateSubdivCube": O("maya.create_subdiv", primitive='CUBE'),
    "CreateSubdivCylinder": O("maya.create_subdiv", primitive='CYLINDER'),
    "CreateSubdivCone": O("maya.create_subdiv", primitive='CONE'),
    "CreateSubdivPlane": O("maya.create_subdiv", primitive='PLANE'),
    "CreateSubdivTorus": O("maya.create_subdiv", primitive='TORUS'),
    "CreateDirectionalLight": O("object.light_add", type='SUN'),
    "CreatePointLight": O("object.light_add", type='POINT'),
    "CreateSpotLight": O("object.light_add", type='SPOT'),
    "CreateAreaLight": O("object.light_add", type='AREA'),
    "CVCurveTool": O("curve.primitive_nurbs_curve_add"),
    "EPCurveTool": O("curve.primitive_nurbs_path_add"),
    "CreateBezierCurveTool": O("curve.primitive_bezier_curve_add"),
    "PencilCurveTool": O("maya.draw_curve"),
    "CreatePolygonType": O("object.text_add"),
    "CreatePolygonSVG": O("import_curve.svg"),
    "CreateImagePlane": O("object.empty_add", type='IMAGE'),
    "CreateLocator": O("object.empty_add", type='PLAIN_AXES', radius=1.0),
    "CreateAnnotateNode": O("object.text_add"),
    "CreateEmptyGroup": O("maya.create_empty_group"),
    "CreateSet": O("maya.create_set"),
    "CreateQuickSelectSet": O("maya.create_set"),
    "CreateCameraOnly": O("object.camera_add"),
    "CreateCameraAim": O("maya.create_camera", aim=True),
    "CreateCameraAimUp": O("maya.create_camera", aim=True),
    "DistanceTool": T("builtin.measure"),
    "ArcLengthTool": T("builtin.measure"),
})

# --------------------------------------------------------------------------
# Select
# --------------------------------------------------------------------------

ACTIONS.update({
    "SelectAll": OE(O("object.select_all", action='SELECT'), O("mesh.select_all", action='SELECT')),
    "SelectNone": OE(O("object.select_all", action='DESELECT'), O("mesh.select_all", action='DESELECT')),
    "InvertSelection": OE(O("object.select_all", action='INVERT'), O("mesh.select_all", action='INVERT')),
    "SelectHierarchy": O("object.select_grouped", type='CHILDREN_RECURSIVE', extend=True),
    "SelectSimilar": OE(O("object.select_grouped", type='TYPE'), O("mesh.select_similar")),
    "SelectAllAssets": O("object.select_all", action='SELECT'),
    "GrowPolygonSelectionRegion": O("mesh.select_more"),
    "ShrinkPolygonSelectionRegion": O("mesh.select_less"),
    "GrowLoopPolygonSelectionRegion": O("mesh.select_next_item"),
    "ShrinkLoopPolygonSelectionRegion": O("mesh.select_prev_item"),
    "SelectToggleMode": O("maya.component_mode", mode='TOGGLE'),
    "SelectMultiComponentMask": O("maya.component_mode", mode='MULTI'),
    "SelectVertexMask": O("maya.component_mode", mode='VERT'),
    "SelectEdgeMask": O("maya.component_mode", mode='EDGE'),
    "SelectFacetMask": O("maya.component_mode", mode='FACE'),
    "SelectUVMask": O("maya.component_mode", mode='UV'),
    "SelectMeshUVShell": O("mesh.select_linked"),
    "SelectContiguousEdges": O("mesh.loop_multi_select", ring=False),
    "SelectShortestEdgePathTool": O("mesh.shortest_path_select"),
    "ConvertSelectionToVertices": O("maya.convert_selection", to='VERT'),
    "ConvertSelectionToVertexPerimeter": O("mesh.region_to_loop"),
    "ConvertSelectionToEdges": O("maya.convert_selection", to='EDGE'),
    "SelectEdgeLoopSp": O("mesh.loop_multi_select", ring=False),
    "SelectEdgeRingSp": O("mesh.loop_multi_select", ring=True),
    "ConvertSelectionToContainedEdges": O("mesh.select_mode", type='EDGE', use_expand=False),
    "ConvertSelectionToEdgePerimeter": O("mesh.region_to_loop"),
    "ConvertSelectionToFaces": O("maya.convert_selection", to='FACE'),
    "SelectFacePath": O("mesh.shortest_path_select"),
    "ConvertSelectionToContainedFaces": O("mesh.select_mode", type='FACE', use_expand=False),
    "ConvertSelectionToShell": O("mesh.select_linked"),
    "ConvertSelectionToUVShell": O("mesh.select_linked"),
    "SelectCurveCVsAll": O("curve.select_all", action='SELECT'),
    "SelectCurveCVsFirst": O("curve.de_select_first"),
    "SelectCurveCVsLast": O("curve.de_select_last"),
    "SelectCVsMask": O("object.mode_set", mode='EDIT'),
    "SelectPointsMask": O("object.mode_set", mode='EDIT'),
})

# --------------------------------------------------------------------------
# Modify
# --------------------------------------------------------------------------

ACTIONS.update({
    "MoveTool": T("builtin.move"),
    "RotateTool": T("builtin.rotate"),
    "ScaleTool": T("builtin.scale"),
    "UniversalManip": T("builtin.transform"),
    "MoveRotateScaleTool": T("builtin.transform"),
    "MoveNormalTool": T("builtin.shrink_fatten"),
    "ProportionalModificationTool": O("maya.soft_select_toggle"),
    "SoftModTool": O("maya.soft_select_toggle"),
    "ResetTransformations": O("maya.reset_transforms"),
    "FreezeTransformations": O("maya.freeze_transforms"),
    "AlignObjects": O("object.align"),
    "SetAlignTool": O("object.align"),
    "SetSnapTogetherTool": O("view3d.snap_selected_to_active"),
    "NURBSToPolygons": O("object.convert", target='MESH'),
    "CreateSubdivSurfacePoly": O("maya.smooth_preview", mode=3),
    "CreatePolyFromPreview": O("maya.smooth_preview_to_polys"),
    "TesselateSubdivSurface": O("maya.smooth_preview_to_polys"),
    "CreateCurveFromPoly": O("object.convert", target='CURVE'),
    "ConvertTypeCapsToCurves": O("object.convert", target='CURVE'),
    "NurbsCurveToBezier": O("curve.spline_type_set", type='BEZIER'),
    "BezierCurveToNurbs": O("curve.spline_type_set", type='NURBS'),
    "ConvertInstanceToObject": O("object.duplicates_make_real"),
    "GeometryToBoundingBox": O("maya.display_type", display='BOUNDS'),
    "ReplaceObjects": O("maya.replace_objects"),
    "ScriptPaintTool": O("paint.weight_paint_toggle"),
    "ArtPaintAttrTool": O("paint.weight_paint_toggle"),
})

# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

ACTIONS.update({
    "ToggleGrid": V("overlay.show_floor"),
    "ToggleVisibilityAndKeepSelection": O("maya.visibility", action='TOGGLE'),
    "TemplateObject": O("maya.template", state=True),
    "UntemplateObject": O("maya.template", state=False),
    "ShowBoundingBox": O("maya.display_type", display='BOUNDS'),
    "HideBoundingBox": O("maya.display_type", display='TEXTURED'),
    "ShowObjectGeometry": O("maya.display_type", display='TEXTURED'),
    "HideObjectGeometry": O("maya.display_type", display='BOUNDS'),
    "ToggleLocalRotationAxes": O("maya.toggle_object_prop", prop="show_axis"),
    "ToggleRotationPivots": O("maya.toggle_object_prop", prop="show_axis"),
    "ToggleScalePivots": O("maya.toggle_object_prop", prop="show_axis"),
    "ToggleSelectionHandles": O("maya.toggle_object_prop", prop="show_axis"),
    "FrameAllInAllViews": O("view3d.view_all", use_all_regions=True),
    "FrameSelectedInAllViews": O("view3d.view_selected", use_all_regions=True),
    "FrameSelectedWithoutChildrenInAllViews": O("view3d.view_selected", use_all_regions=True),
    "HideSelectedObjects": O("maya.visibility", action='HIDE'),
    "HideUnselectedObjects": O("maya.visibility", action='HIDE_UNSELECTED'),
    "ShowSelectedObjects": O("maya.visibility", action='SHOW_LAST'),
    "ShowLastHidden": O("maya.visibility", action='SHOW_LAST'),
    "ShowAll": O("maya.visibility", action='SHOW_ALL'),
    "ShowAllPolyComponents": O("mesh.reveal"),
    "ToggleBackfaceGeometry": V("shading.show_backface_culling"),
    "ToggleFaceNormalDisplay": V("overlay.show_face_normals"),
    "ToggleVertexNormalDisplay": V("overlay.show_vertex_normals"),
    "ToggleTangentDisplay": V("overlay.show_split_normals"),
    "TogglePolyDisplayHardEdges": V("overlay.show_edge_sharp"),
    "TogglePolyDisplayHardEdgesColor": V("overlay.show_edge_sharp"),
    "ToggleCreaseEdges": V("overlay.show_edge_crease"),
    "ToggleTextureBorderEdges": V("overlay.show_edge_seams"),
    "TogglePolygonFaceCenters": V("overlay.show_face_center"),
    "ToggleVertIDs": V("overlay.show_extra_indices"),
    "ToggleEdgeIDs": V("overlay.show_extra_indices"),
    "ToggleFaceIDs": V("overlay.show_extra_indices"),
    "ToggleCompIDs": V("overlay.show_extra_indices"),
    "ToggleFastInteraction": V("shading.show_xray"),
    "NURBSSmoothnessHull": O("maya.smooth_preview", mode=1),
    "NURBSSmoothnessRough": O("maya.smooth_preview", mode=1),
    "NURBSSmoothnessMedium": O("maya.smooth_preview", mode=2),
    "NURBSSmoothnessFine": O("maya.smooth_preview", mode=3),
    "SubdivSmoothnessHull": O("maya.smooth_preview", mode=1),
    "SubdivSmoothnessRough": O("maya.smooth_preview", mode=1),
    "SubdivSmoothnessMedium": O("maya.smooth_preview", mode=2),
    "SubdivSmoothnessFine": O("maya.smooth_preview", mode=3),
    "ToggleJointLabels": O("maya.toggle_armature_names"),
})

# --------------------------------------------------------------------------
# Windows (editors open in a new window, like Maya's floating editors)
# --------------------------------------------------------------------------

ACTIONS.update({
    "AttributeEditor": W("PROPERTIES"),
    "OpenChannelsLayers": O("maya.toggle_attribute_editor"),
    "OpenChannelBox": O("maya.toggle_attribute_editor"),
    "OpenLayerEditor": O("maya.toggle_attribute_editor"),
    "DisplayLayerEditorWindow": W("OUTLINER"),
    "ToolSettingsWindow": V("show_region_ui"),
    "HypergraphHierarchyWindow": W("OUTLINER"),
    "HypergraphDGWindow": W("GeometryNodeTree"),
    "SpreadSheetEditor": W("SPREADSHEET"),
    "ComponentEditor": W("SPREADSHEET"),
    "ScriptEditor": W("TEXT_EDITOR"),
    "CommandShell": W("CONSOLE"),
    "OpenModelingToolkit": V("show_region_ui"),
    "HypershadeWindow": W("ShaderNodeTree"),
    "GraphEditor": W("FCURVES"),
    "DopeSheetEditor": W("DOPESHEET"),
    "TimeEditorWindow": W("NLA_EDITOR"),
    "SequenceEditor": W("SEQUENCE_EDITOR"),
    "ShapeEditor": W("PROPERTIES"),
    "PoseEditor": W("PROPERTIES"),
    "ExpressionEditor": W("DRIVERS"),
    "NodeEditorWindow": W("GeometryNodeTree"),
    "OutlinerWindow": W("OUTLINER"),
    "OpenContentBrowser": W("ASSETS"),
    "FilePathEditor": O("file.report_missing_files"),
    "PreferencesWindow": P('INTERFACE'),
    "PerformanceSettingsWindow": P('VIEWPORT'),
    "HotkeyPreferencesWindow": P('KEYMAP'),
    "ColorPreferencesWindow": P('THEMES'),
    "MarkingMenuPreferencesWindow": P('KEYMAP'),
    "ShelfPreferencesWindow": P('ADDONS'),
    "PanelPreferencesWindow": P('INTERFACE'),
    "PluginManager": P('ADDONS'),
    "PlayblastWindow": O("render.opengl", animation=True),
})

# --------------------------------------------------------------------------
# Modeling: Mesh / Edit Mesh / Mesh Tools / Mesh Display
# --------------------------------------------------------------------------

for _name, _op in {"Union": 'UNION', "Difference": 'DIFFERENCE', "DifferenceBA": 'DIFFERENCE_BA',
                   "Intersection": 'INTERSECT', "Slice": 'SLICE', "HolePunch": 'HOLE_PUNCH',
                   "CutOut": 'CUT_OUT', "SplitEdges": 'SPLIT_EDGES'}.items():
    ACTIONS["PolygonBoolean" + _name] = O("maya.boolean", operation=_op)

ACTIONS.update({
    "CombinePolygons": O("object.join"),
    "SeparatePolygon": O("maya.separate"),
    "ConformPolygon": M("mesh.normals_make_consistent", inside=False),
    "FillHole": M("mesh.fill_holes"),
    "ReducePolygon": MOD('DECIMATE'),
    "PolyRemesh": MOD('REMESH'),
    "PolyRetopo": O("object.quadriflow_remesh"),
    "SmoothPolygon": O("maya.poly_smooth"),
    "UnsmoothPolygon": M("mesh.unsubdivide"),
    "Triangulate": M("mesh.quads_convert_to_tris"),
    "Quadrangulate": M("mesh.tris_convert_to_quads"),
    "MirrorPolygonGeometry": MOD('MIRROR'),
    "TransferAttributes": O("object.data_transfer"),
    "CleanupPolygon": M("mesh.dissolve_degenerate"),
    "SmoothProxy": O("maya.smooth_preview", mode=2),
    "UnmirrorSmoothProxy": O("maya.smooth_preview", mode=1),
    "PolyCreaseTool": O("transform.edge_crease"),
    "SmoothingDisplayToggle": O("maya.smooth_preview", mode=3),
    "SmoothingDisplayShowBoth": O("maya.smooth_preview", mode=2),
    "SubdividePolygon": M("mesh.subdivide"),
    "BevelPolygon": O("maya.bevel"),
    "BridgeOrFill": O("mesh.bridge_edge_loops"),
    "PolyCircularize": O("transform.tosphere", value=1.0),
    "PolygonCollapse": O("mesh.merge", type='COLLAPSE'),
    "ConnectComponents": O("mesh.vert_connect_path"),
    "DetachComponent": O("mesh.split"),
    "PolyExtrude": O("maya.extrude"),
    "SmartExtrude": O("view3d.edit_mesh_extrude_move_normal"),
    "PolyMerge": M("mesh.remove_doubles"),
    "MergeToCenter": O("mesh.merge", type='CENTER'),
    "MovePolygonComponent": O("transform.translate"),
    "FlipMesh": M("transform.mirror", constraint_axis=(True, False, False)),
    "Symmetrize": M("mesh.symmetrize"),
    "AverageVertex": M("mesh.vertices_smooth"),
    "ChamferVertex": O("mesh.bevel", affect='VERTICES'),
    "DeletePolyElements": O("maya.delete_components", clean=True),
    "FlipTriangleEdge": O("mesh.edge_rotate", use_ccw=False),
    "PolySpinEdgeBackward": O("mesh.edge_rotate", use_ccw=True),
    "PolySpinEdgeForward": O("mesh.edge_rotate", use_ccw=False),
    "DuplicateFace": O("mesh.duplicate_move"),
    "ExtractFace": O("mesh.separate", type='SELECTED'),
    "PokePolygon": O("mesh.poke"),
    "WedgePolygon": O("mesh.spin"),
    "ProjectCurveOnMesh": O("mesh.knife_project"),
    "SplitMeshWithProjectedCurve": O("mesh.knife_project", cut_through=True),
    "ToggleModelingToolkit": V("show_region_ui"),
    "EnterConnectTool": O("mesh.vert_connect_path"),
    "SplitEdgeRingTool": O("maya.mesh_tool", tool='LOOP_CUT'),
    "MultiCutTool": O("maya.mesh_tool", tool='KNIFE'),
    "DuplicateEdges": O("mesh.offset_edge_loops_slide"),
    "QuadDrawTool": O("maya.mesh_tool", tool='POLY_BUILD'),
    "SlideEdgeTool": O("transform.edge_slide"),
    "MergeVertexTool": O("mesh.merge", type='LAST'),
    "MakeHoleTool": O("mesh.knife_project"),
    "AveragePolygonNormals": M("mesh.average_normals"),
    "ConformPolygonNormals": M("mesh.normals_make_consistent", inside=False),
    "ReversePolygonNormals": M("mesh.flip_normals"),
    "SetToFaceNormals": M("mesh.set_normals_from_faces"),
    "PolygonHardenEdge": M("mesh.mark_sharp"),
    "PolygonSoftenEdge": M("mesh.mark_sharp", clear=True),
    "PolygonSoftenHarden": M("mesh.set_sharpness_by_angle"),
    "LockNormals": O("mesh.customdata_custom_splitnormals_add"),
    "UnlockNormals": O("mesh.customdata_custom_splitnormals_clear"),
    "PolygonNormalEditTool": O("mesh.point_normals"),
    "PaintVertexColorTool": O("paint.vertex_paint_toggle"),
})

# --------------------------------------------------------------------------
# Modeling: Curves / Surfaces
# --------------------------------------------------------------------------

ACTIONS.update({
    "DuplicateCurve": O("curve.duplicate_move"),
    "AttachCurve": O("curve.make_segment"),
    "DetachCurve": O("curve.split"),
    "CutCurve": O("curve.split"),
    "OpenCloseCurve": O("curve.cyclic_toggle"),
    "InsertKnot": O("curve.subdivide"),
    "ExtendCurve": O("curve.extrude_move"),
    "AddPointsTool": O("curve.extrude_move"),
    "SmoothCurve": O("curve.smooth"),
    "SmoothHairCurves": O("curve.smooth"),
    "ReverseCurve": O("curve.switch_direction"),
    "RebuildCurve": O("curve.decimate"),
    "StraightenCurves": O("curve.handle_type_set", type='VECTOR'),
    "CVHardness": O("curve.handle_type_set", type='VECTOR'),
    "BezierPresetBezier": O("curve.handle_type_set", type='ALIGNED'),
    "BezierPresetBezierCorner": O("curve.handle_type_set", type='FREE_ALIGN'),
    "BezierPresetCorner": O("curve.handle_type_set", type='VECTOR'),
    "BezierSetAnchorSmooth": O("curve.handle_type_set", type='ALIGNED'),
    "BezierSetAnchorBroken": O("curve.handle_type_set", type='FREE_ALIGN'),
    "BezierSetAnchorEven": O("curve.handle_type_set", type='AUTOMATIC'),
    "BezierSetAnchorUneven": O("curve.handle_type_set", type='FREE_ALIGN'),
    "CurveEditTool": T("builtin.tweak"),
    "Revolve": MOD('SCREW', steps=16),
    "Extrude": O("maya.curve_extrude"),
    "Planar": O("maya.curve_planar"),
    "Loft": O("maya.loft"),
    "ReverseSurfaceDirection": O("curve.switch_direction"),
    "SculptGeometryTool": O("object.mode_set", mode='SCULPT'),
    "OpenCloseSurfaces": O("curve.cyclic_toggle"),
    "InsertIsoparms": O("curve.subdivide"),
})

# --------------------------------------------------------------------------
# Deform
# --------------------------------------------------------------------------

ACTIONS.update({
    "CreateBlendShape": O("object.join_shapes"),
    "AddBlendShape": O("object.join_shapes"),
    "RemoveBlendShape": O("object.shape_key_remove"),
    "CreateCluster": O("object.hook_add_newob"),
    "DeltaMush": MOD('CORRECTIVE_SMOOTH'),
    "Solidify": MOD('SOLIDIFY'),
    "CreateLattice": O("maya.add_lattice"),
    "ProximityWrap": MOD('SURFACE_DEFORM'),
    "CreateWrap": MOD('SURFACE_DEFORM'),
    "CreateShrinkWrap": MOD('SHRINKWRAP'),
    "Bend": MOD('SIMPLE_DEFORM', deform_method='BEND'),
    "Flare": MOD('SIMPLE_DEFORM', deform_method='TAPER'),
    "Twist": MOD('SIMPLE_DEFORM', deform_method='TWIST'),
    "Squash": MOD('SIMPLE_DEFORM', deform_method='STRETCH'),
    "Sine": MOD('WAVE'),
    "Wave": MOD('WAVE'),
    "CreateSculptDeformer": MOD('CAST'),
    "CreateTextureDeformer": MOD('DISPLACE'),
    "CurveWarp": MOD('CURVE'),
    "WireTool": MOD('CURVE'),
    "Morph": MOD('SURFACE_DEFORM'),
    "MirrorDeformerWeights": O("object.vertex_group_mirror"),
    "PaintSetMembershipTool": O("paint.weight_paint_toggle"),
    "EditMembershipTool": O("object.vertex_group_assign"),
})
for _name in ("ArtPaintBlendShapeWeightsTool", "PaintClusterWeightsTool",
              "PaintDeltaMushWeightsTool", "PaintTensionWeightsTool",
              "PaintProximityWrapWeightsTool", "PaintLatticeWeightsTool",
              "PaintShrinkWrapWeightsTool", "PaintWireWeightsTool",
              "PaintNonlinearWeightsTool", "PaintJiggleWeightsTool",
              "PaintTextureDeformerWeightsTool", "ArtPaintSkinWeightsTool",
              "PaintSoftWeights"):
    ACTIONS[_name] = O("paint.weight_paint_toggle")

# --------------------------------------------------------------------------
# UV
# --------------------------------------------------------------------------

ACTIONS.update({
    "TextureViewWindow": W("UV"),
    "UVSetEditor": W("PROPERTIES"),
    "UVAutomaticProjection": M("uv.smart_project"),
    "BestPlaneTexturingTool": M("uv.project_from_view"),
    "UVCameraBasedProjection": M("uv.project_from_view"),
    "UVContourStretchProjection": M("uv.follow_active_quads"),
    "UVNormalBasedProjection": M("uv.smart_project"),
    "UVCylindricProjection": M("uv.cylinder_project"),
    "UVPlanarProjection": M("uv.cube_project"),
    "UVSphericalProjection": M("uv.sphere_project"),
    "AutoSeamUVs": M("uv.smart_project"),
    "CutUVsWithoutHotkey": O("mesh.mark_seam"),
    "SewUVsWithoutHotkey": O("mesh.mark_seam", clear=True),
    "SplitUV": O("mesh.mark_seam"),
    "MergeUV": A("uv.weld", 'IMAGE_EDITOR'),
})

# --------------------------------------------------------------------------
# Rigging: Skeleton / Skin / Constrain
# --------------------------------------------------------------------------

ACTIONS.update({
    "JointTool": O("maya.joint_tool"),
    "InsertJointTool": O("armature.subdivide"),
    "MirrorJoint": O("armature.symmetrize"),
    "OrientJoint": O("armature.calculate_roll"),
    "RemoveJoint": O("armature.dissolve"),
    "ConnectJoint": O("armature.parent_set", type='CONNECTED'),
    "DisconnectJoint": O("armature.parent_clear", type='DISCONNECT'),
    "ToggleSelectedLabels": O("maya.toggle_armature_names"),
    "ShowAllLabels": O("maya.toggle_armature_names"),
    "HideAllLabels": O("maya.toggle_armature_names"),
    "IKHandleTool": O("pose.ik_add", with_targets=True),
    "IKSplineHandleTool": O("pose.constraint_add", type='SPLINE_IK'),
    "SmoothBindSkin": O("maya.bind_skin"),
    "InteractiveBindSkin": O("maya.bind_skin"),
    "VolumeSkinBinding": O("maya.bind_skin"),
    "DetachSkin": O("maya.detach_skin"),
    "GoToBindPose": O("maya.go_to_bind_pose"),
    "MirrorSkinWeights": O("object.vertex_group_mirror"),
    "CopySkinWeights": O("object.data_transfer", data_type='VGROUP_WEIGHTS'),
    "SmoothSkinWeights": O("object.vertex_group_smooth"),
    "WeightHammer": O("object.vertex_group_smooth"),
    "CopyVertexWeights": O("object.vertex_weight_copy"),
    "PasteVertexWeights": O("object.vertex_weight_paste"),
    "PruneSmallWeights": O("object.vertex_group_clean"),
    "NormalizeWeights": O("object.vertex_group_normalize_all"),
    "EnableWeightNrm": O("object.vertex_group_normalize_all"),
    "SetMaxInfluences": O("object.vertex_group_limit_total"),
    "RemoveUnusedInfluences": O("object.vertex_group_clean", group_select_mode='ALL'),
    "RemoveInfluence": O("object.vertex_group_remove"),
    "AddInfluence": O("object.vertex_group_add"),
    "ParentConstraint": CON('CHILD_OF'),
    "PointConstraint": CON('COPY_LOCATION'),
    "OrientConstraint": CON('COPY_ROTATION'),
    "ScaleConstraint": CON('COPY_SCALE'),
    "AimConstraint": CON('TRACK_TO'),
    "PoleVectorConstraint": O("maya.pole_vector"),
    "GeometryConstraint": CON('SHRINKWRAP'),
    "PointOnPolyConstraint": CON('SHRINKWRAP'),
    "NormalConstraint": CON('SHRINKWRAP'),
    "TangentConstraint": CON('FOLLOW_PATH'),
    "SetKeyPath": CON('FOLLOW_PATH'),
    "RemoveConstraintTarget": O("maya.delete_constraints"),
})

# --------------------------------------------------------------------------
# Animation: Key / Playback / Visualize
# --------------------------------------------------------------------------

ACTIONS.update({
    "SetKey": O("maya.set_key", channels='ALL'),
    "SetKeyAnimated": O("anim.keyframe_insert_by_name", type='Available'),
    "SetKeyTranslate": O("maya.set_key", channels='TRANSLATE'),
    "SetKeyRotate": O("maya.set_key", channels='ROTATE'),
    "SetKeyScale": O("maya.set_key", channels='SCALE'),
    "SetBreakdownKey": O("maya.set_key", channels='ALL', breakdown=True),
    "InsertKey": O("maya.set_key", channels='ALL'),
    "InsertKeyTranslate": O("maya.set_key", channels='TRANSLATE'),
    "InsertKeyRotate": O("maya.set_key", channels='ROTATE'),
    "InsertKeyScale": O("maya.set_key", channels='SCALE'),
    "HoldCurrentKeys": O("maya.set_key", channels='ALL'),
    "PlaybackForward": O("screen.animation_play"),
    "PlaybackBackward": O("screen.animation_play", reverse=True),
    "PlaybackStop": O("screen.animation_cancel", restore_frame=False),
    "NextKey": O("screen.keyframe_jump", next=True),
    "PreviousKey": O("screen.keyframe_jump", next=False),
    "SelectNextKey": O("screen.keyframe_jump", next=True),
    "SelectPreviousKey": O("screen.keyframe_jump", next=False),
    "NextFrame": O("screen.frame_offset", delta=1),
    "PreviousFrame": O("screen.frame_offset", delta=-1),
    "GoToMinFrame": O("screen.frame_jump", end=False),
    "GoToMaxFrame": O("screen.frame_jump", end=True),
    "PlaybackRealtime": O("maya.playback_sync", mode='FRAME_DROP'),
    "PlaybackPefRealtime": O("maya.playback_sync", mode='FRAME_DROP'),
    "PlaybackFree": O("maya.playback_sync", mode='NONE'),
    "OpenBluePencil": T("builtin.annotate"),
    "AnimationSnapshot": O("object.paths_calculate"),
    "AnimationSweep": O("object.paths_calculate"),
})

# --------------------------------------------------------------------------
# FX (Blender simulation equivalents)
# --------------------------------------------------------------------------

ACTIONS.update({
    "CreateEmitter": O("object.particle_system_add"),
    "EmitFromObject": O("object.particle_system_add"),
    "NCreateEmitter": O("object.particle_system_add"),
    "NEmitFromObject": O("object.particle_system_add"),
    "MakeCollide": MOD('COLLISION'),
    "nClothMakeCollide": MOD('COLLISION'),
    "MakeFluidCollide": MOD('COLLISION'),
    "CreateSoftBody": MOD('SOFT_BODY'),
    "CreateNSoftBody": MOD('SOFT_BODY'),
    "nClothCreate": MOD('CLOTH'),
    "nClothRemove": O("maya.delete_modifiers", types="CLOTH"),
    "nClothDeleteHistory": O("maya.delete_modifiers", types="CLOTH"),
    "FluidEmitter": O("object.quick_liquid"),
    "EmitFluidFromObject": O("object.quick_liquid"),
    "Create3DContainerEmitter": O("object.quick_smoke"),
    "Create2DContainerEmitter": O("object.quick_smoke"),
    "CreateOcean": O("maya.create_ocean"),
    "CreatePond": O("maya.create_ocean"),
    "CreateHair": O("object.quick_fur"),
    "Smoke": O("object.quick_smoke"),
    "Fire": O("object.quick_smoke", style='FIRE'),
    "Shatter": O("object.quick_explode"),
    "Air": O("object.effector_add", type='WIND'),
    "Drag": O("object.effector_add", type='DRAG'),
    "Gravity": O("object.effector_add", type='FORCE'),
    "Newton": O("object.effector_add", type='FORCE'),
    "Radial": O("object.effector_add", type='FORCE'),
    "Turbulence": O("object.effector_add", type='TURBULENCE'),
    "Uniform": O("object.effector_add", type='WIND'),
    "Vortex": O("object.effector_add", type='VORTEX'),
    "VolumeAxis": O("object.effector_add", type='FLUID'),
    "CreateCurveField": O("object.effector_add", type='GUIDE'),
    "CreateActiveRigidBody": O("rigidbody.objects_add", type='ACTIVE'),
    "CreatePassiveRigidBody": O("rigidbody.objects_add", type='PASSIVE'),
    "CreateNailConstraint": O("rigidbody.connect", con_type='POINT'),
    "CreatePinConstraint": O("rigidbody.connect", con_type='FIXED'),
    "CreateHingeConstraint": O("rigidbody.connect", con_type='HINGE'),
    "CreateSpringConstraint": O("rigidbody.connect", con_type='GENERIC_SPRING'),
    "BreakRigidBodyConnection": O("rigidbody.objects_remove"),
    "nClothCache": O("ptcache.bake_all", bake=True),
    "CreateParticleDiskCache": O("ptcache.bake_all", bake=True),
    "CreateFluidCache": O("ptcache.bake_all", bake=True),
    "DeleteMemoryCaching": O("ptcache.free_bake_all"),
    "fluidDeleteCache": O("ptcache.free_bake_all"),
    "DisableAllCaches": O("ptcache.free_bake_all"),
})

# --------------------------------------------------------------------------
# Shelf-only commands
# --------------------------------------------------------------------------

ACTIONS.update({
    "CenterPivot": O("maya.center_pivot"),
    "DeleteHistory": O("maya.delete_history"),
    "ArtPaintSelectTool": T("builtin.select_circle"),
    "CreateSweepMesh": O("maya.curve_extrude"),
    "CreateHairOptions": O("object.quick_fur"),
    "makeCollideNCloth": MOD('COLLISION'),
    "deleteNclothCache": O("ptcache.free_bake_all"),
    "SetInitialState": O("ptcache.bake_all", bake=True),
    "ClearInitialState": O("ptcache.free_bake_all"),
    "InteractivePlayback": O("screen.animation_play"),
    "MakeCurvesDynamic": O("object.quick_fur"),
    "ConvertToFrozen": O("paint.mask_flood_fill", mode='VALUE', value=1.0),
    "uvSetEditor": W("PROPERTIES"),
    "SetMeshGrabUVTool": W("UV"),
    "SetCutSewUVTool": W("UV"),
    "HypergraphWindow": W("OUTLINER"),
    "performBridgeOrFill": O("mesh.bridge_edge_loops"),
    "performBevelOrChamfer": O("maya.bevel"),
    "dR_multiCutTool": O("maya.mesh_tool", tool='KNIFE'),
    "dR_quadDrawTool": O("maya.mesh_tool", tool='POLY_BUILD'),
    "TumbleTool": O("view3d.view_orbit", type='ORBITRIGHT'),
    "Delete": OE(O("object.delete", use_global=False, confirm=False),
                 O("maya.delete_components", clean=True)),
    "Help": O("wm.url_open_preset", type='MANUAL'),
})

# Sculpting shelf: Maya mesh sculpt tools -> Blender essential sculpt brushes.
for _tool, _brush in {
    "Sculpt": "Draw", "Smooth": "Smooth", "Relax": "Relax Slide", "Grab": "Grab",
    "Pinch": "Pinch/Magnify", "Flatten": "Flatten/Contrast", "Foamy": "Clay",
    "Spray": "Draw Sharp", "Repeat": "Layer", "Imprint": "Draw", "Wax": "Clay Strips",
    "Scrape": "Scrape/Fill", "Fill": "Fill/Deepen", "Knife": "Crease Sharp",
    "Smear": "Smear", "Bulge": "Inflate/Deflate", "Amplify": "Sharpen", "Freeze": "Mask",
}.items():
    ACTIONS[f"SetMesh{_tool}Tool"] = O("maya.sculpt_brush", brush=_brush)

# --------------------------------------------------------------------------
# Second pass: more Maya commands with Blender equivalents
# --------------------------------------------------------------------------

ACTIONS.update({
    # Edit / Create
    "ScaleKeys": A("transform.transform", 'GRAPH_EDITOR', mode='TIME_SCALE'),
    "CreatePartition": O("maya.create_set"),
    "CreateContainer": O("maya.create_set"),
    "CreateDagContainer": O("maya.create_set"),
    "AddToContainer": O("maya.create_set"),
    "CreateVolumeLight": O("object.light_add", type='POINT'),
    "CreateConstructionPlane": O("object.empty_add", type='PLAIN_AXES'),
    "CreateNURBSSquare": O("curve.primitive_nurbs_circle_add", radius=1.0),
    "CreatePolygonSuperEllipse": O("mesh.primitive_uv_sphere_add", radius=1.0),
    # Select
    "SelectAllRigidBodies": O("maya.select_rigid"),
    "SelectAllRigidConstraints": O("maya.select_rigid", constraints=True),
    "SelectAllFollicles": O("maya.select_by_type", types="CURVES"),
    "SelectAllBrushes": O("maya.select_by_type", types="CURVES"),
    "ConvertSelectionToFacePerimeter": O("mesh.region_to_loop"),
    "ConvertSelectionToShellBorder": O("mesh.region_to_loop"),
    "ConvertSelectionToUVShellBorder": O("mesh.region_to_loop"),
    "PolygonSelectionConstraints": O("mesh.select_similar"),
    "SelectCurvePointsMask": O("object.mode_set", mode='EDIT'),
    "SelectHullsMask": O("object.mode_set", mode='EDIT'),
    "SelectSurfacePointsMask": O("object.mode_set", mode='EDIT'),
    # Modify
    "ShowManipulatorTool": T("builtin.transform"),
    "SetDefaultManipNone": T("builtin.select_box"),
    "SetDefaultManipMove": T("builtin.move"),
    "SetDefaultManipRotate": T("builtin.rotate"),
    "SetDefaultManipScale": T("builtin.scale"),
    "SetDefaultManipTransform": T("builtin.transform"),
    "PositionAlongCurve": CON('FOLLOW_PATH'),
    "CreateSubdivSurface": O("maya.smooth_preview", mode=3),
    "FluidsToPolygons": O("object.convert", target='MESH'),
    "PaintEffectsToPoly": O("object.convert", target='MESH'),
    "PaintEffectsToCurve": O("object.convert", target='CURVE'),
    "MakeLive": O("maya.snap_live"),
    # Display
    "HideDeformingGeometry": O("maya.show_hide", types="MOD:ARMATURE,LATTICE,MESH_DEFORM", show=False),
    "ShowDeformingGeometry": O("maya.show_hide", types="MOD:ARMATURE,LATTICE,MESH_DEFORM", show=True),
    "HideNonlinears": O("maya.show_hide", types="MOD:SIMPLE_DEFORM,WAVE", show=False),
    "ShowNonlinears": O("maya.show_hide", types="MOD:SIMPLE_DEFORM,WAVE", show=True),
    "HideSmoothSkinInfluences": O("maya.show_hide", types="ARMATURE", show=False),
    "ShowSmoothSkinInfluences": O("maya.show_hide", types="ARMATURE", show=True),
    "HideWrapInfluences": O("maya.show_hide", types="MOD:SURFACE_DEFORM", show=False),
    "ShowWrapInfluences": O("maya.show_hide", types="MOD:SURFACE_DEFORM", show=True),
    "HideFollicles": O("maya.show_hide", types="CURVES", show=False),
    "ShowFollicles": O("maya.show_hide", types="CURVES", show=True),
    "HideLightManipulators": V("show_gizmo_light_size"),
    "ShowLightManipulators": V("show_gizmo_light_size"),
    "HideCameraManipulators": V("show_gizmo_camera_lens"),
    "ShowCameraManipulators": V("show_gizmo_camera_lens"),
    "TogglePolyDisplayEdges": V("overlay.show_wireframes"),
    "TogglePolyDisplaySoftEdges": V("overlay.show_edge_sharp"),
    "ToggleBorderEdges": V("overlay.show_edge_seams"),
    "TogglePolyNonPlanarFaceDisplay": V("overlay.show_statvis"),
    "ToggleNormals": V("overlay.show_face_normals"),
    "ToggleSurfaceOrigin": V("overlay.show_object_origins"),
    "ToggleKeepWireCulling": V("shading.show_backface_culling"),
    "ToggleCullingVertices": V("shading.show_backface_culling"),
    "ToggleEffectsMeshDisplay": V("overlay.show_wireframes"),
    "SetWireframeColor": O("maya.toggle_object_prop", prop="show_wire"),
    # Windows
    "NamespaceEditor": W("OUTLINER"),
    "SetEditor": W("OUTLINER"),
    "PartitionEditor": W("OUTLINER"),
    "AssetEditor": W("OUTLINER"),
    "ConnectionEditor": W("DRIVERS"),
    "CharacterAnimationEditor": W("NLA_EDITOR"),
    "DeformerSetEditor": W("PROPERTIES"),
    "OpenMotionTrailEditor": O("object.paths_calculate"),
    "OpenCreaseEditor": W("PROPERTIES"),
    "DisplayViewport": W("VIEW_3D"),
    # Mesh display
    "CreateEmptySet": O("geometry.color_attribute_add"),
    "AssignNewSet": O("geometry.color_attribute_add"),
    "DeleteCurrentSet": O("geometry.color_attribute_remove"),
    "PolygonApplyColor": O("paint.vertex_color_set"),
    "OpenColorSetEditor": W("PROPERTIES"),
    # Curves / Surfaces
    "FitBSpline": O("curve.spline_type_set", type='NURBS'),
    "Bevel": O("maya.curve_bevel"),
    "BevelPlus": O("maya.curve_bevel"),
    "Birail1": O("maya.curve_extrude"),
    "Birail2": O("maya.curve_extrude"),
    "Birail3": O("maya.curve_extrude"),
    "Boundary": O("maya.loft"),
    "SquareSurface": O("maya.loft"),
    "AttachSurfaces": O("object.join"),
    "AttachSurfaceWithoutMoving": O("object.join"),
    "DetachSurfaces": O("curve.split"),
    "SurfaceBooleanUnionTool": O("maya.boolean", operation='UNION'),
    "SurfaceBooleanSubtractTool": O("maya.boolean", operation='DIFFERENCE'),
    "SurfaceBooleanIntersectTool": O("maya.boolean", operation='INTERSECT'),
    "SurfaceEditingTool": T("builtin.tweak"),
    "RebuildSurfaces": O("object.convert", target='MESH'),
    # Deform
    "AddWire": MOD('CURVE'),
    "RemoveWire": O("maya.delete_modifiers", types="CURVE"),
    "PointOnCurve": CON('FOLLOW_PATH'),
    "PruneCluster": O("object.vertex_group_clean"),
    "PruneLattice": O("object.vertex_group_clean"),
    "PruneSculpt": O("object.vertex_group_clean"),
    "PruneWire": O("object.vertex_group_clean"),
    "SetShrinkWrapTarget": MOD('SHRINKWRAP'),
    "RemoveShrinkWrapTarget": O("maya.delete_modifiers", types="SHRINKWRAP"),
    "AddWrapInfluence": MOD('SURFACE_DEFORM'),
    "RemoveWrapInfluence": O("maya.delete_modifiers", types="SURFACE_DEFORM"),
    "DeleteUVsWithoutHotkey": O("mesh.uv_texture_remove"),
    # Skeleton / Skin / Constrain
    "FBIKLabelLeft": O("maya.joint_side", side='L'),
    "FBIKLabelRight": O("maya.joint_side", side='R'),
    "FBIKLabelCenter": O("maya.joint_side", side='C'),
    "FBIKLabelNone": O("maya.joint_side", side='NONE'),
    "EnableSelectedIKHandles": O("maya.toggle_ik", enable=True),
    "DisableSelectedIKHandles": O("maya.toggle_ik", enable=False),
    "AssumePreferredAngle": O("maya.go_to_bind_pose"),
    "MoveSkinJointsTool": T("builtin.move"),
    "Rivet": O("object.vertex_parent_set"),
    "UVPin": O("object.vertex_parent_set"),
    "ProximityPin": O("object.vertex_parent_set"),
    # Key / Playback / Visualize
    "PlaybackRangeMinMax": O("anim.previewrange_clear"),
    "PlaybackRangeStartEnd": O("anim.previewrange_clear"),
    "PlaybackRangeHighlight": A("anim.previewrange_set", 'DOPESHEET_EDITOR'),
    "UpdateSnapshot": O("object.paths_update"),
    "KeyBlendShapeTargetsWeight": O("maya.set_key", channels='ALL'),
})
