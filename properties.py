import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)
import math

# --- Auto Mark Sharp Edges Settings ---
class EvolverAutoSharpSettings(bpy.types.PropertyGroup):
    """Stores settings specifically for the Auto Mark Sharp Edges detector"""
    bl_idname = "object.evolver_auto_sharp_settings"

    auto_sharp_primary_angle: FloatProperty(
        name="Primary Detection Angle",
        description="Dihedral angle threshold to detect sharp edges",
        default=math.radians(30.0),
        min=0.0, max=math.pi,
        subtype='ANGLE',
        unit='ROTATION' # Ensures proper display as degrees
    )
    auto_sharp_use_existing_sharps: BoolProperty(
        name="Use Blender Sharps",
        description="Consider existing edges marked as 'Sharp'",
        default=True
    )
    auto_sharp_use_existing_creases: BoolProperty(
        name="Use Blender Creases",
        description="Consider existing edge creases",
        default=True
    )
    auto_sharp_min_crease_value: FloatProperty(
        name="Min Crease Value",
        description="Minimum crease value to consider an edge for sharpness",
        default=0.1, min=0.0, max=1.0
    )
    auto_sharp_use_existing_seams: BoolProperty(
        name="Use Blender Seams",
        description="Consider existing edge seams",
        default=True
    )
    auto_sharp_use_bevel_weights: BoolProperty(
        name="Use Bevel Weights",
        description="Consider existing edge bevel weights",
        default=False
    )
    auto_sharp_min_bevel_weight: FloatProperty(
        name="Min Bevel Weight",
        description="Minimum bevel weight to consider an edge for sharpness",
        default=0.1, min=0.0, max=1.0
    )
    auto_sharp_use_curvature: BoolProperty(
        name="Enable Curvature Analysis",
        description="Use curvature analysis to detect sharp features (can be slow on dense meshes)",
        default=True
    )
    auto_sharp_curvature_sensitivity: FloatProperty(
        name="Curvature Sensitivity",
        description="Sensitivity for curvature-based detection. Higher values detect more subtle features",
        default=0.5, min=0.0, max=1.0,
        subtype='FACTOR'
    )
    auto_sharp_preserve_uv_boundaries: BoolProperty(
        name="Preserve UV Island Boundaries",
        description="Detect sharp edges along UV island boundaries",
        default=True
    )
    auto_sharp_min_feature_length: IntProperty(
        name="Min Feature Length",
        description="Minimum number of connected edges to form a continuous sharp feature (helps reduce noise)",
        default=3, min=1
    )

    # Internal property to store previewed edges (set of edge indices)
    # This is not ideal for PropertyGroup as it's dynamic runtime data.
    # We'll manage this via the operator or a global variable for simplicity here.
    # For more robust state, consider custom data layers or a more sophisticated manager.
    # preview_edges_indices: CollectionProperty(type=bpy.types.IntProperty) # Example, but not used this way


# --- Main Evolver Remesher Settings ---
class EvolverRemesherSettings(bpy.types.PropertyGroup):
    bl_idname = "object.evolver_remesher_settings"

    # --- Target Resolution ---
    target_mode: EnumProperty(
        name="Target Mode",
        items=[
            ('POLYCOUNT', "Polycount", "Target a specific polygon count"),
            ('EDGE_LENGTH', "Average Edge Length", "Target an average edge length"),
            ('VOXEL_SIZE', "Voxel Size", "Target based on voxel size (if using a voxel-based method)"),
        ],
        default='POLYCOUNT',
        description="Method to determine the resolution of the remeshed output"
    )
    polycount_is_percentage: BoolProperty(
        name="Relative Polycount",
        description="Target polycount as a percentage of the original, otherwise absolute value",
        default=True
    )
    polycount_absolute: IntProperty(
        name="Absolute Polycount",
        description="Target number of polygons",
        default=5000, min=10
    )
    polycount_percentage: FloatProperty(
        name="Polycount Percentage",
        description="Target polycount as a percentage of the original mesh's face count",
        default=0.5, min=0.01, max=5.0, # Allow up to 500%
        subtype='FACTOR',
        precision=2
    )
    avg_edge_length: FloatProperty(
        name="Average Edge Length",
        description="Desired average edge length in the remeshed output (world units)",
        default=0.1, min=0.001, soft_max=10.0,
        subtype='DISTANCE',
        unit='LENGTH'
    )
    voxel_size_absolute: FloatProperty(
        name="Voxel Size",
        description="Absolute voxel size for voxel-based remeshing approaches (world units)",
        default=0.05, min=0.001, soft_max=1.0,
        subtype='DISTANCE',
        unit='LENGTH'
    )

    # --- Feature Definition ---
    # These settings are for the main remesher, but can be informed by the Auto-Sharp tool
    main_auto_detect_angle: FloatProperty(
        name="Sharp Angle (Remesher)",
        description="Angle threshold for sharp edge preservation during remeshing (if not using explicitly marked sharps)",
        default=math.radians(45.0), min=0.0, max=math.pi,
        subtype='ANGLE',
        unit='ROTATION'
    )
    use_marked_sharp: BoolProperty(
        name="Preserve Marked Sharps",
        description="Preserve edges explicitly marked as 'Sharp'",
        default=True
    )
    use_marked_crease: BoolProperty(
        name="Preserve Marked Creases",
        description="Preserve edges with crease values",
        default=True
    )
    crease_threshold: FloatProperty(
        name="Min Crease for Remesher",
        description="Minimum crease value to be considered a sharp feature by the remesher",
        default=0.25, min=0.0, max=1.0
    )
    use_marked_seam: BoolProperty(
        name="Preserve Marked Seams",
        description="Preserve edges marked as 'Seam'",
        default=True
    )
    use_bevel_weights_remesher: BoolProperty( # Renamed to avoid conflict with auto_sharp
        name="Preserve Bevel Weights",
        description="Consider bevel weights for feature preservation during remeshing",
        default=False
    )
    bevel_weight_threshold_remesher: FloatProperty( # Renamed
        name="Min Bevel for Remesher",
        description="Minimum bevel weight to be considered for feature preservation",
        default=0.25, min=0.0, max=1.0
    )
    hard_edge_strictness: FloatProperty(
        name="Hard Edge Strictness",
        description="How strictly hard edges are followed. Lower values allow more deviation for better topology",
        default=0.8, min=0.0, max=1.0,
        subtype='FACTOR'
    )

    # --- Output Topology ---
    quad_dominance: FloatProperty(
        name="Quad Dominance",
        description="Preference for quadrilateral faces (0.0 = tris, 1.0 = quads)",
        default=0.9, min=0.0, max=1.0,
        subtype='FACTOR'
    )
    attempt_pure_quads: BoolProperty(
        name="Attempt Pure Quads",
        description="Try to generate an all-quad mesh (can be slower and might not always succeed)",
        default=False
    )

    # --- Edge Flow Control ---
    curvature_influence: FloatProperty(
        name="Curvature Influence on Flow",
        description="How much mesh curvature guides edge flow (0.0 = none, 1.0 = strong)",
        default=0.5, min=0.0, max=1.0,
        subtype='FACTOR'
    )
    symmetry_x: BoolProperty(name="Symmetry X", default=False)
    symmetry_y: BoolProperty(name="Symmetry Y", default=False)
    symmetry_z: BoolProperty(name="Symmetry Z", default=False)
    
    guide_curves_collection: PointerProperty(
        name="Guide Curves Collection",
        description="Collection containing curve objects to guide edge flow",
        type=bpy.types.Collection
    )

    # --- Detail & Quality ---
    detail_capture_bias: FloatProperty(
        name="Detail Capture Bias",
        description="Bias towards capturing fine details vs. smoother surfaces",
        default=0.5, min=0.0, max=1.0,
        subtype='FACTOR'
    )
    quality_preset: EnumProperty(
        name="Quality Preset",
        items=[
            ('DRAFT', "Draft", "Fastest, lowest quality"),
            ('MEDIUM', "Medium", "Balanced speed and quality"),
            ('HIGH', "High", "Slower, higher quality detail"),
            ('CUSTOM', "Custom", "Use custom settings below"),
        ],
        default='MEDIUM',
        # update=update_quality_settings_func # Placeholder for an update function
        description="Overall quality preset"
    )
    # --- PROMPT FOR CODING AGENT (for update_quality_settings_func) ---
    # TASK: Implement the 'update_quality_settings_func'.
    # DETAILS:
    #   - This function should be called when 'quality_preset' changes.
    #   - Based on the selected preset (DRAFT, MEDIUM, HIGH), it should adjust other relevant
    #     quality/performance settings (e.g., 'relaxation_iterations', 'max_quad_aspect_ratio',
    #     potentially internal solver parameters not yet exposed in UI).
    #   - If preset is 'CUSTOM', it should not change other settings, allowing manual override.
    #   - Signature: def update_quality_settings_func(self, context):
    # --- END PROMPT ---

    max_quad_aspect_ratio: FloatProperty(
        name="Max Quad Aspect Ratio",
        description="Maximum allowed aspect ratio for quads. Higher values allow more stretched quads.",
        default=5.0, min=1.0, soft_max=20.0
    )
    relaxation_iterations: IntProperty(
        name="Relaxation Iterations",
        description="Number of mesh relaxation/smoothing iterations",
        default=5, min=0, max=50
    )

    # --- Data Transfer ---
    transfer_uvs: BoolProperty(name="Transfer UVs", default=True)
    transfer_vertex_colors: BoolProperty(name="Transfer Vertex Colors", default=True)
    transfer_vertex_groups: BoolProperty(name="Transfer Vertex Groups/Weights", default=True)
    transfer_custom_normals: BoolProperty(name="Transfer Custom Normals (Experimental)", default=False)
    transfer_shape_keys: BoolProperty(name="Transfer Shape Keys (Experimental)", default=False)

    # --- Advanced Options ---
    show_advanced_options: BoolProperty(name="Show Advanced Options", default=False)
    
    preserve_uv_island_boundaries_remesher: BoolProperty( # Renamed
        name="Preserve UV Boundaries (Remesher)",
        description="Attempt to preserve UV island boundaries during remeshing",
        default=True
    )
    use_adaptive_density_map: BoolProperty(
        name="Use Adaptive Density Map",
        description="Use a map (vertex group or color) to control local mesh density",
        default=False
    )
    density_map_type: EnumProperty(
        name="Density Map Type",
        items=[
            ('VERTEX_GROUP', "Vertex Group", "Use a vertex group for density"),
            ('VERTEX_COLOR', "Vertex Color", "Use a vertex color layer for density (e.g., red channel)"),
        ],
        default='VERTEX_GROUP'
    )
    density_vertex_group: StringProperty(
        name="Density Vertex Group",
        description="Name of the vertex group to use for adaptive density"
    )
    density_vertex_color_layer: StringProperty(
        name="Density Vertex Color Layer",
        description="Name of the vertex color layer to use for adaptive density"
    )
    boundary_handling: EnumProperty(
        name="Open Boundary Handling",
        items=[
            ('RELAX', "Relax", "Allow open boundaries to relax naturally"),
            ('FIXED', "Fixed", "Keep open boundary vertices fixed in place"),
            ('PROJECT', "Project", "Project open boundaries onto original shape"),
        ],
        default='RELAX',
        description="How to treat open mesh boundaries"
    )
    non_destructive_mode: BoolProperty(
        name="Non-Destructive Mode",
        description="Create a new object for the remeshed result, keeping the original",
        default=True
    )
    output_suffix: StringProperty(
        name="Output Suffix",
        description="Suffix to add to the name of the new object in non-destructive mode",
        default="_remeshed"
    )
    
    # --- Internal / Runtime ---
    # These are not directly part of the PropertyGroup UI but used by operators
    # Storing preview state here is an option, though can be tricky with PropertyGroups
    # For now, we'll manage preview state more directly in operators or a global registry.
    # _preview_active: BoolProperty(default=False) # Internal flag
    # _preview_edge_indices: StringProperty() # Serialized list/set of edge indices for preview


def register():
    bpy.utils.register_class(EvolverAutoSharpSettings)
    bpy.utils.register_class(EvolverRemesherSettings)
    
    bpy.types.Object.evolver_remesher_settings = PointerProperty(type=EvolverRemesherSettings)
    # The AutoSharp settings are specific to the operator's context,
    # or could be part of the main EvolverRemesherSettings if desired.
    # For now, we'll make them accessible via the scene for the operator to use, or operator properties.
    # If you want AutoSharp settings to be per-object and persistent, add them to EvolverRemesherSettings
    # or create a separate PointerProperty on bpy.types.Object for them.
    # Let's assume for now the AutoSharp settings are globally configured via a panel,
    # so we can put them on the Scene.
    bpy.types.Scene.evolver_auto_sharp_settings = PointerProperty(type=EvolverAutoSharpSettings)


def unregister():
    del bpy.types.Scene.evolver_auto_sharp_settings
    del bpy.types.Object.evolver_remesher_settings
    
    bpy.utils.unregister_class(EvolverRemesherSettings)
    bpy.utils.unregister_class(EvolverAutoSharpSettings)