import bpy
import bmesh
import math
from mathutils import Vector, kdtree # For potential KD-Tree use
from . import utils # For report_message or bmesh_from_obj if used directly here

# --- Constants for detection types (matching the plan) ---
TYPE_NONE = "NONE"
TYPE_BLENDER_SEAM = "BLENDER_SEAM"
TYPE_UV_SEAM_BOUNDARY = "UV_SEAM_BOUNDARY"
TYPE_BLENDER_SHARP = "BLENDER_SHARP"
TYPE_BLENDER_CREASE = "BLENDER_CREASE"
TYPE_ANGLE_SHARP = "ANGLE_SHARP"
TYPE_CURVATURE_SHARP = "CURVATURE_SHARP"
TYPE_BLENDER_BEVEL = "BLENDER_BEVEL"

# Priority order (lower index = higher priority)
# Matches the plan: BLENDER_SEAM / UV_SEAM_BOUNDARY have highest priority.
# Architectural plan had UV_SEAM_BOUNDARY as highest together with BLENDER_SEAM.
# Let's make it explicit if they are different or combined.
# Assuming UV_SEAM_BOUNDARY can be a distinct detection, but often correlates with BLENDER_SEAM.
PRIORITY_ORDER = [
    TYPE_UV_SEAM_BOUNDARY, # Often user-intent for UVs, implies hard edge for remeshing.
    TYPE_BLENDER_SEAM,    # Explicit user intent for seam.
    TYPE_BLENDER_SHARP,   # Explicit user intent for visual sharpness.
    TYPE_BLENDER_CREASE,  # Explicit user intent for subdivision control.
    TYPE_ANGLE_SHARP,     # Geometric detection.
    TYPE_CURVATURE_SHARP, # Geometric detection for organic forms.
    TYPE_BLENDER_BEVEL,   # Weaker indicator, but can be useful.
]


# --- AM1: Pre-computation & Data Acquisition ---
def am1_prepare_bmesh_data(bm):
    """
    Prepares BMesh data for analysis. Ensures lookup tables and calculates normals.
    Input: bm (BMesh)
    Output: (Boolean success)
    """
    if not bm:
        # --- PROMPT FOR CODING AGENT (ERROR HANDLING) ---
        # TASK: Enhance error handling here. This function assumes bm is valid.
        # DETAILS: Consider raising an exception if bm is None or invalid,
        #          or return a more detailed status object.
        # --- END PROMPT ---
        return False

    try:
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # Pre-calculate face normals
        for f in bm.faces:
            f.normal_update() # Ensures f.normal is accurate

        # Pre-calculate vertex normals (geometric, Blender's default calculation)
        for v in bm.verts:
            v.normal_update() # Ensures v.normal is accurate

        # --- PROMPT FOR CODING AGENT (KD-Tree/BVH) ---
        # TASK: Implement KD-Tree or BVH-Tree construction if needed for advanced curvature analysis (AM2c)
        #       or neighborhood queries in AM3.
        # DETAILS:
        #   - Store the tree on the bm object (e.g., bm.kd_tree) or return it.
        #   - Use `mathutils.kdtree.KDTree` for points (e.g., vertex coordinates).
        #   - Example:
        #     size = len(bm.verts)
        #     kd = kdtree.KDTree(size)
        #     for i, v in enumerate(bm.verts):
        #         kd.insert(v.co, i)
        #     kd.balance()
        #     bm.kd_tree = kd # Store it for later use
        # CURRENT_IMPLEMENTATION: KD-Tree/BVH is not built by default.
        # --- END PROMPT ---

        return True
    except Exception as e:
        # --- PROMPT FOR CODING AGENT (LOGGING) ---
        # TASK: Implement more robust logging using Python's `logging` module.
        # DETAILS: Log the exception `e` with traceback for easier debugging.
        # --- END PROMPT ---
        print(f"EvolverRemesher Core: Error in AM1 pre-computation: {e}")
        return False


# --- AM2: Candidate Edge Detection (Multi-Source) ---

def am2a_dihedral_angle_analysis(bm, primary_detection_angle_rad):
    """
    Detects candidate sharp edges based on dihedral angle.
    Input: bm (BMesh), primary_detection_angle_rad (float, angle in radians)
    Output: Set of BMEdge objects identified as ANGLE_SHARP
    """
    angle_sharp_candidates = set()
    if not bm or not bm.edges: return angle_sharp_candidates

    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            face1 = edge.link_faces[0]
            face2 = edge.link_faces[1]
            # Normals should be pre-calculated by am1_prepare_bmesh_data
            angle = face1.normal.angle(face2.normal) 
            if angle > primary_detection_angle_rad:
                angle_sharp_candidates.add(edge)
    return angle_sharp_candidates

def am2b_existing_blender_data_scan(bm, use_sharps, use_creases, min_crease_val,
                                   use_seams, use_bevels, min_bevel_val):
    """
    Detects candidate edges based on existing Blender mesh data.
    Input: bm (BMesh), various boolean flags and thresholds from settings.
    Output: Dictionary {detection_type: set(BMEdge)}
    """
    candidates_by_type = {
        TYPE_BLENDER_SHARP: set(),
        TYPE_BLENDER_CREASE: set(),
        TYPE_BLENDER_SEAM: set(),
        TYPE_BLENDER_BEVEL: set(),
    }
    if not bm or not bm.edges: return candidates_by_type

    for edge in bm.edges:
        if use_sharps and (edge.smooth is False or edge.use_edge_sharp is True): # 'smooth' is older, 'use_edge_sharp' for custom normals
            candidates_by_type[TYPE_BLENDER_SHARP].add(edge)
        
        if use_creases and edge.crease > min_crease_val:
            candidates_by_type[TYPE_BLENDER_CREASE].add(edge)
            # --- PROMPT FOR CODING AGENT (METRIC STORAGE) ---
            # TASK: Consider how to store the actual crease value if needed later for AM4 (e.g., setting crease on new mesh).
            # DETAILS: The current `candidates_by_type` only stores the edge. If metrics like crease value
            #          are needed, the structure should be `dict[detection_type, dict[BMEdge, metric_value]]`.
            #          This applies to bevel weight as well.
            #          For AM3 (Prioritization), you'll need to aggregate all (type, metric) per edge.
            # --- END PROMPT ---

        if use_seams and edge.seam:
            candidates_by_type[TYPE_BLENDER_SEAM].add(edge)

        if use_bevels and edge.bevel_weight > min_bevel_val:
            candidates_by_type[TYPE_BLENDER_BEVEL].add(edge)
            # See prompt above for metric storage.

    return candidates_by_type

def am2c_curvature_based_analysis(bm, curvature_sensitivity):
    """
    Detects candidate sharp edges based on mesh curvature.
    Input: bm (BMesh), curvature_sensitivity (float, 0.0-1.0)
    Output: Set of BMEdge objects identified as CURVATURE_SHARP
    """
    curvature_sharp_candidates = set()
    if not bm or not bm.edges: return curvature_sharp_candidates

    # --- PROMPT FOR CODING AGENT (CURVATURE ANALYSIS IMPLEMENTATION) ---
    # TASK: Implement robust curvature analysis (Method A or B from architectural plan Section 3.2 AM2c).
    # DETAILS:
    #   Method A (Edge-Centric - Simpler, start here if Method B is too complex initially):
    #     - For each edge, analyze change in vertex normals of its verts (v1, v2) relative to edge vector.
    #     - Or, compare normals of adjacent faces not sharing the edge but incident to its vertices.
    #   Method B (Vertex-Centric Saliency - More Robust, ideal goal):
    #     - Calculate per-vertex principal curvatures (k_min, k_max) or other saliency metrics.
    #       - This might involve fitting a quadratic surface or using discrete differential geometry operators (e.g., cotangent weights for mean curvature normal).
    #     - Identify vertices with:
    #         - High absolute mean curvature.
    #         - High absolute Gaussian curvature.
    #         - Significant difference in principal curvature magnitudes (ridges/valleys).
    #     - Edges connecting such salient vertices, or edges whose vertices exhibit a sharp change in curvature across the edge, become candidates.
    #   - `curvature_sensitivity` should influence thresholds. Higher sensitivity = lower thresholds, detecting more subtle features.
    #   - Add identified BMEdge objects to `curvature_sharp_candidates`.
    #   - Store a curvature metric/saliency score per edge if possible for AM3.
    # CHALLENGES:
    #   - Performance: Python implementation can be slow for dense meshes.
    #   - Robustness: Curvature calculation can be sensitive to noisy mesh data.
    #   - Algorithm Complexity: Implementing accurate discrete curvature operators is non-trivial.
    # LIBRARIES/REFERENCES:
    #   - Search for "discrete curvature estimation on triangle meshes", "principal curvature estimation".
    #   - Papers on mesh saliency. Blender's own sculpt tools have internal curvature calculations.
    # CURRENT_IMPLEMENTATION: Placeholder, returns an empty set.
    # --- END PROMPT ---

    print(f"EvolverRemesher Core: AM2c Curvature analysis STUB - sensitivity: {curvature_sensitivity}. No edges will be marked by this method.")
    # Example (very naive and likely not robust - for illustration of structure only):
    # for edge in bm.edges:
    #     if len(edge.verts) == 2:
    #         v1_normal = edge.verts[0].normal
    #         v2_normal = edge.verts[1].normal
    #         # This is a very poor proxy for curvature change along an edge
    #         if v1_normal.dot(v2_normal) < (1.0 - curvature_sensitivity * 0.5): # Arbitrary threshold
    #             curvature_sharp_candidates.add(edge)
    
    return curvature_sharp_candidates

def am2d_uv_island_boundary_analysis(bm):
    """
    Detects candidate sharp edges based on UV island boundaries.
    Input: bm (BMesh)
    Output: Set of BMEdge objects identified as UV_SEAM_BOUNDARY
    """
    uv_seam_boundary_candidates = set()
    if not bm or not bm.edges: return uv_seam_boundary_candidates

    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        print("EvolverRemesher Core: AM2d - No active UV layer found.")
        return uv_seam_boundary_candidates

    # --- PROMPT FOR CODING AGENT (UV BOUNDARY DETECTION IMPLEMENTATION) ---
    # TASK: Implement robust UV island boundary detection.
    # DETAILS:
    #   - An edge is a UV boundary if its loops (belonging to adjacent faces) map to
    #     UV coordinates that are not "welded" or "continuous" in the UV map.
    #   - Method 1 (Simpler, relies on existing `edge.seam` if UVs were unwrapped using seams):
    #     - Check `edge.seam`. This is often, but not always, a UV boundary.
    #     - This might overlap significantly with `TYPE_BLENDER_SEAM`. The distinction is
    #       that `TYPE_UV_SEAM_BOUNDARY` is specifically for preserving UV map discontinuities
    #       even if the user didn't mark it as a generic "seam" for other purposes.
    #   - Method 2 (More Robust, analyzes UV connectivity):
    #     - For each edge with two linked faces:
    #       - Get the two loops associated with this edge (one for each face).
    #       - Compare their UV coordinates (`loop[uv_layer].uv`).
    #       - True boundary if UVs are different *and* if traversing UV space from one loop's UV vertex
    #         does not reach the other loop's UV vertex without crossing a "UV seam" (which is hard to define without full UV graph traversal).
    #       - A common proxy: if an edge's loops have different UV coordinates for the same vertex index, it's often a split.
    #         Or if `loop[uv_layer].uv_seam` attribute exists and is true (newer Blender versions might have this).
    #   - Consider edges on the boundary of the mesh itself (if `edge.is_boundary` is true). These are always UV boundaries.
    # CURRENT_IMPLEMENTATION: Placeholder. A simple check for `edge.seam` could be a starting point,
    #                        but the goal is to detect actual UV splits even if not marked as `edge.seam`.
    # --- END PROMPT ---

    print("EvolverRemesher Core: AM2d UV Island Boundary analysis STUB. No edges will be marked by this method yet.")
    # Simplistic example (might be redundant with BLENDER_SEAM, true UV boundary is more complex):
    # for edge in bm.edges:
    #    if edge.seam: # This is often how UV islands are made, but not always exclusively.
    #        # A more robust check would involve looking at loop[uv_layer].uv coordinates
    #        # and their connectivity in UV space.
    #        is_true_uv_boundary = False
    #        if len(edge.link_loops) >= 2: # An edge has at least two loops (one per side per face)
    #            # This check is tricky: we need to see if verts that share this edge in 3D
    #            # map to different, disconnected locations in UV space.
    #            # A heuristic: if any two loops sharing this edge have substantially different UVs for their verts.
    #            # Or if any loop on this edge is marked as a UV seam internally.
    #            # For now, let's assume edge.seam is a strong indicator for this simple stub.
    #            is_true_uv_boundary = True # Placeholder logic
    #
    #        if is_true_uv_boundary:
    #             uv_seam_boundary_candidates.add(edge)

    return uv_seam_boundary_candidates


# --- AM3: Candidate Filtering, Refinement & Prioritization ---
def am3_filter_refine_prioritize(bm, all_candidate_sources, min_feature_length):
    """
    Consolidates candidates, applies priorities, and filters based on feature length.
    Input:
        bm (BMesh)
        all_candidate_sources (dict): {BMEdge: [(detection_type, metric_value), ...]}
                                      Example: {edge1: [("ANGLE_SHARP", 60.0), ("CURVATURE_SHARP", 0.8)]}
        min_feature_length (int): Minimum length for a chain of ANGLE_SHARP or CURVATURE_SHARP edges.
    Output:
        final_selected_edges (set of BMEdge): Edges to be definitively marked sharp.
    """
    final_selected_edges = set()
    if not bm or not all_candidate_sources:
        return final_selected_edges

    priority_resolved_edges = {} # {BMEdge: (winning_type, winning_metric)}

    # 1. Priority Resolution
    for edge, detections in all_candidate_sources.items():
        if not detections:
            continue
        
        winning_detection = detections[0] # Default to the first one
        current_best_priority_index = float('inf')

        for detection_type, metric_value in detections:
            try:
                priority_index = PRIORITY_ORDER.index(detection_type)
                if priority_index < current_best_priority_index:
                    current_best_priority_index = priority_index
                    winning_detection = (detection_type, metric_value)
            except ValueError:
                # This detection_type is not in our PRIORITY_ORDER, handle as lowest priority or log
                print(f"Warning: Detection type '{detection_type}' not in PRIORITY_ORDER.")
                # Could assign it a priority lower than any in the list
                if float('inf') < current_best_priority_index: # Only if nothing better was found
                    winning_detection = (detection_type, metric_value) # Keep it if it's all we have
        
        priority_resolved_edges[edge] = winning_detection


    # --- PROMPT FOR CODING AGENT (NOISE REDUCTION & CHAIN FORMATION IMPLEMENTATION) ---
    # TASK: Implement robust noise reduction and chain formation for ANGLE_SHARP and CURVATURE_SHARP edges.
    # DETAILS:
    #   - Algorithm Idea (as per plan Section 3.3 AM3):
    #     - Initialize `processed_edges` set.
    #     - Iterate through `priority_resolved_edges`. If an edge is ANGLE_SHARP or CURVATURE_SHARP and not processed:
    #       - Start a chain (DFS or BFS) along connected edges that are also ANGLE_SHARP/CURVATURE_SHARP
    #         (and also in `priority_resolved_edges` with that winning type).
    #       - Mark visited edges in `processed_edges`.
    #       - Store the chain.
    #   - Filtering Rules:
    #     - Discard chains shorter than `min_feature_length`.
    #     - Exception: Keep edges in short chains if part of a junction (vertex connected to 3+
    #                  edges from `priority_resolved_edges` that are themselves considered sharp after initial prio).
    #     - (Advanced) For CURVATURE_SHARP chains: Analyze consistency of curvature magnitude/direction.
    # CHALLENGES:
    #   - Defining "connected" and "compatible types" for chaining.
    #   - Efficiently finding junctions.
    #   - Robustly handling complex branching features.
    # CURRENT_IMPLEMENTATION: Basic pass-through for explicit types, placeholder for geometric type filtering.
    # --- END PROMPT ---

    print("EvolverRemesher Core: AM3 Noise Reduction & Chain Formation STUB.")
    
    # For now, a simplified approach:
    # - Explicit types (BLENDER_*) are always included if they won the priority.
    # - Geometric types (ANGLE_SHARP, CURVATURE_SHARP) will be subject to chaining (stubbed).
    
    geometric_candidates_for_chaining = {} # {BMEdge: (type, metric)}
    
    for edge, (winning_type, metric) in priority_resolved_edges.items():
        if winning_type in [TYPE_BLENDER_SEAM, TYPE_UV_SEAM_BOUNDARY, TYPE_BLENDER_SHARP, TYPE_BLENDER_CREASE, TYPE_BLENDER_BEVEL]:
            final_selected_edges.add(edge)
        elif winning_type in [TYPE_ANGLE_SHARP, TYPE_CURVATURE_SHARP]:
            geometric_candidates_for_chaining[edge] = (winning_type, metric)
            # For STUB: add them directly for now, a_s actual chaining logic is missing
            # In full impl, only add if part of a valid chain.
            final_selected_edges.add(edge) 
            
    # Placeholder for actual chaining logic operating on `geometric_candidates_for_chaining`
    # and `min_feature_length`. The result of chaining would then update `final_selected_edges`.
    # For example:
    # chained_geometric_edges = perform_chaining_and_filtering(geometric_candidates_for_chaining, min_feature_length, bm)
    # final_selected_edges.update(chained_geometric_edges)

    return final_selected_edges


# --- AM4: Output & User Feedback (Applying to BMesh) ---
def am4_apply_sharps_to_bmesh(bm, selected_sharp_edges, auto_sharp_settings):
    """
    Applies the detected sharpness to the BMesh edges.
    Input:
        bm (BMesh)
        selected_sharp_edges (set of BMEdge): Final edges to mark.
        auto_sharp_settings (EvolverAutoSharpSettings): User settings to guide how marks are applied.
                                                        (e.g. if creases should also be set)
    Output:
        (int) Number of edges marked.
    """
    if not bm or not selected_sharp_edges:
        return 0

    # --- PROMPT FOR CODING AGENT (ENHANCED MARKING LOGIC) ---
    # TASK: Enhance how edges are marked based on their original detected type and user preferences.
    # DETAILS:
    #   - The `selected_sharp_edges` currently doesn't retain the "winning_type" from AM3.
    #     AM3 should ideally output `final_selected_features = {BMEdge: (winning_type, metric)}`.
    #   - Then, AM4 can use `winning_type` to decide:
    #     - If `edge.use_edge_sharp = True` is always set. (Likely yes for all)
    #     - If `edge.crease` should be set (e.g., if winning_type was BLENDER_CREASE, or if a global
    #       "auto-crease all detected sharps" option is enabled).
    #     - If `edge.seam` should be set (e.g., if winning_type was BLENDER_SEAM or UV_SEAM_BOUNDARY).
    #   - `auto_sharp_settings` might include toggles like `set_crease_on_detected_angle_sharps`, etc.
    # CURRENT_IMPLEMENTATION: Marks all selected edges with `use_edge_sharp = True`.
    # --- END PROMPT ---

    marked_count = 0
    for edge in selected_sharp_edges:
        if isinstance(edge, bmesh.types.BMEdge) and edge.is_valid:
            edge.use_edge_sharp = True
            
            # Example of more detailed marking (requires `winning_type`):
            # winning_type, metric = final_selected_features.get(edge)
            # if winning_type == TYPE_BLENDER_CREASE and auto_sharp_settings.auto_sharp_use_existing_creases:
            #    edge.crease = metric # Assuming metric was the original crease value
            # elif winning_type == TYPE_BLENDER_SEAM and auto_sharp_settings.auto_sharp_use_existing_seams:
            #    edge.seam = True
            # Add more logic based on settings and detected types.

            marked_count += 1
        else:
            print(f"Warning: Invalid edge found in selected_sharp_edges: {edge}")
            
    return marked_count


# --- Main Orchestration Function for Auto Mark Sharp Edges ---
def auto_detect_and_mark_edges(bm, settings: bpy.types.PropertyGroup): # Type hint with actual settings class
    """
    Main orchestrator for the Auto Mark Sharp Edges process.
    Input:
        bm (BMesh): The BMesh to operate on.
        settings (EvolverAutoSharpSettings): User-configurable parameters.
    Output:
        (set of BMEdge): The set of edges identified as sharp and to be marked/previewed.
                         Returns empty set on failure.
    """
    if not bm or not settings:
        # --- PROMPT FOR CODING AGENT (ROBUST INPUT VALIDATION) ---
        # TASK: Add more robust input validation.
        # DETAILS: Check bm.is_valid, ensure settings object is correctly populated, etc.
        #          Return meaningful error indicators or raise exceptions.
        # --- END PROMPT ---
        return set()

    print("Starting Auto Mark Sharp Edges detection...")

    # AM1: Pre-computation
    if not am1_prepare_bmesh_data(bm):
        print("EvolverRemesher Core: AM1 data preparation failed.")
        return set()

    # AM2: Candidate Edge Detection
    all_detected_candidates_map = {} # {BMEdge: [(detection_type, metric_value), ...]}

    # Helper to aggregate candidates
    def add_candidates(edge_set, det_type, metric=1.0): # Default metric
        for edge in edge_set:
            if edge not in all_detected_candidates_map:
                all_detected_candidates_map[edge] = []
            all_detected_candidates_map[edge].append((det_type, metric))

    # 2a. Dihedral Angle
    angle_sharps = am2a_dihedral_angle_analysis(bm, settings.auto_sharp_primary_angle)
    add_candidates(angle_sharps, TYPE_ANGLE_SHARP, settings.auto_sharp_primary_angle) # Metric could be the angle itself
    print(f"AM2a Dihedral Angle: Found {len(angle_sharps)} candidates.")

    # 2b. Existing Blender Data
    existing_data_map = am2b_existing_blender_data_scan(
        bm,
        settings.auto_sharp_use_existing_sharps,
        settings.auto_sharp_use_existing_creases, settings.auto_sharp_min_crease_value,
        settings.auto_sharp_use_existing_seams,
        settings.auto_sharp_use_bevel_weights, settings.auto_sharp_min_bevel_weight
    )
    for det_type, edges in existing_data_map.items():
        # --- PROMPT FOR CODING AGENT (METRIC FOR EXISTING DATA) ---
        # TASK: Ensure actual metrics (crease value, bevel weight) are passed if am2b_existing_blender_data_scan is updated
        #       to provide them, instead of just adding edges.
        # DETAILS: The `add_candidates` helper currently uses a default metric or the primary angle for angle sharps.
        #          For creases/bevels, the metric should be the actual value from the edge.
        # --- END PROMPT ---
        add_candidates(edges, det_type) # Default metric 1.0 for now, ideally store original value
        print(f"AM2b Existing Data ({det_type}): Found {len(edges)} candidates.")

    # 2c. Curvature-Based (if enabled)
    if settings.auto_sharp_use_curvature:
        curvature_sharps = am2c_curvature_based_analysis(bm, settings.auto_sharp_curvature_sensitivity)
        add_candidates(curvature_sharps, TYPE_CURVATURE_SHARP, settings.auto_sharp_curvature_sensitivity) # Metric could be sensitivity or a saliency score
        print(f"AM2c Curvature: Found {len(curvature_sharps)} candidates.")
    
    # 2d. UV Island Boundaries (if enabled)
    if settings.auto_sharp_preserve_uv_boundaries:
        uv_boundaries = am2d_uv_island_boundary_analysis(bm)
        add_candidates(uv_boundaries, TYPE_UV_SEAM_BOUNDARY)
        print(f"AM2d UV Boundaries: Found {len(uv_boundaries)} candidates.")

    if not all_detected_candidates_map:
        print("EvolverRemesher Core: No candidate edges found by any method.")
        return set()
    
    print(f"Total unique edges with any candidate detection: {len(all_detected_candidates_map)}")

    # AM3: Filtering, Refinement & Prioritization
    final_edges_to_mark = am3_filter_refine_prioritize(bm, all_detected_candidates_map, settings.auto_sharp_min_feature_length)
    print(f"AM3 Filtering & Prioritization: Selected {len(final_edges_to_mark)} final edges.")

    if not final_edges_to_mark:
        print("EvolverRemesher Core: No edges selected after filtering and prioritization.")
        return set()
        
    return final_edges_to_mark


def register():
    pass # No classes to register here, functions are used by operators

def unregister():
    pass