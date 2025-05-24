import bpy
import gpu
from gpu_extras.batch import batch_for_shader

# Store active draw handlers globally for now.
# A more robust system might involve a manager class.
_active_draw_handlers = {} # {context_hash: (handler, bmesh_edges_ref)}

# --- PROMPT FOR CODING AGENT (IMPROVE DRAW HANDLER MANAGEMENT) ---
# TASK: Design a more robust system for managing draw handlers.
# DETAILS:
#   - Problem: Using a simple global dict `_active_draw_handlers` can lead to stale handlers if not cleared properly
#     (e.g., on file load, addon disable/re-enable without Blender restart).
#   - Consider:
#     - A manager class registered with `bpy.app.handlers` (e.g., `load_post`, `depsgraph_update_post`)
#       to clean up or re-validate handlers.
#     - Storing handler references more carefully, perhaps keyed by object or scene, and ensuring
#       they are removed when the object/scene is removed or the addon unregisters.
#   - For previewing on BMesh data that might change (e.g. if user edits mesh while preview is active),
#     the preview needs to be updated or invalidated.
# CURRENT_IMPLEMENTATION: Simple global dictionary.
# --- END PROMPT ---

def draw_preview_sharps(context, edges_to_draw_indices, obj_matrix_world):
    """
    Draws the given edges in the 3D View.
    `edges_to_draw_indices` is expected to be a list/set of (v1_idx, v2_idx) tuples for edges.
    This function needs access to the BMesh or vertex coordinates of the object.
    For simplicity, this example assumes we get coords from obj.data.vertices.
    A more direct BMesh approach would be better if the BMesh is readily available.
    """
    if not edges_to_draw_indices:
        return

    # --- PROMPT FOR CODING AGENT (ACCESSING MESH DATA FOR DRAWING) ---
    # TASK: Determine the best way to access vertex coordinates for drawing.
    # DETAILS:
    #   - `edges_to_draw_indices` currently implies we have BMesh edge indices, but this draw function
    #     needs vertex coordinates.
    #   - If the `auto_detect_and_mark_edges` returns BMEdge objects, we can get `e.verts[0].co`, `e.verts[1].co`.
    #   - If it returns edge indices, we need the BMesh they belong to.
    #   - The current draft implies passing vertex indices of the edges.
    #   - The preview system needs to efficiently get coordinates. If working on a temporary BMesh for preview,
    #     use those coordinates. If previewing on the actual object data, use `obj.data.vertices[idx].co`.
    #
    #   - This example assumes `edges_to_draw_indices` contains tuples of vertex coordinates:
    #     `[(v1_co, v2_co), (v3_co, v4_co), ...]`
    #     This structure needs to be prepared by the calling operator.
    # --- END PROMPT ---

    coords = []
    for v1_co, v2_co in edges_to_draw_indices:
        coords.append(obj_matrix_world @ v1_co) # Apply object transform
        coords.append(obj_matrix_world @ v2_co)

    if not coords:
        return

    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    # --- PROMPT FOR CODING AGENT (CUSTOMIZE PREVIEW APPEARANCE) ---
    # TASK: Allow customization of preview line color and thickness.
    # DETAILS:
    #   - Add addon preferences or operator properties for line color and thickness.
    #   - Use these values here.
    # --- END PROMPT ---
    batch = batch_for_shader(shader, 'LINES', {"pos": coords})
    
    # Save and set GL state
    original_line_width = gpu.state.line_width_get()
    original_blend = gpu.state.blend_get()
    
    gpu.state.line_width_set(2.0) # Example line width
    gpu.state.blend_set('ALPHA') # Enable blending for potential future alpha effects

    shader.bind()
    shader.uniform_float("color", (1.0, 0.5, 0.0, 1.0))  # Orange color for preview
    batch.draw(shader)

    # Restore GL state
    gpu.state.line_width_set(original_line_width)
    gpu.state.blend_set(original_blend)


def add_preview_handler(context, obj, edges_bm): # edges_bm is a set of BMEdge
    """Adds a draw handler for the given object and BMesh edges."""
    remove_preview_handler(context) # Clear any existing handler for this context

    if not obj or not obj.data or not edges_bm:
        return

    # Convert BMEdge objects to a list of (v1.co, v2.co) tuples in local space
    # This is crucial: the draw handler will need these coordinates.
    # If the BMesh is freed before drawing, these coordinates must be stored.
    edge_vertex_coords = []
    for edge in edges_bm:
        if edge.is_valid and len(edge.verts) == 2:
            edge_vertex_coords.append((edge.verts[0].co.copy(), edge.verts[1].co.copy()))
    
    if not edge_vertex_coords:
        print("Draw Handler: No valid edge coordinates to draw.")
        return

    # The draw handler function needs `context` if it's to access settings,
    # but for drawing itself, it primarily needs the geometry data and object matrix.
    # We pass `edge_vertex_coords` and `obj.matrix_world` as arguments.
    args = (context, edge_vertex_coords, obj.matrix_world)
    handler = bpy.types.SpaceView3D.draw_handler_add(draw_preview_sharps, args, 'WINDOW', 'POST_VIEW')
    
    # Use a hash of the context area to uniquely identify the handler,
    # assuming one preview per 3D View area.
    # This is a simplification. A robust system needs careful keying.
    context_key = hash(context.area)
    _active_draw_handlers[context_key] = handler
    
    # Tag region for redraw
    if context.area:
        context.area.tag_redraw()
    print(f"Draw Handler: Added preview for {len(edge_vertex_coords)} edges.")


def remove_preview_handler(context):
    """Removes the draw handler for the given context."""
    context_key = hash(context.area)
    handler = _active_draw_handlers.pop(context_key, None)
    if handler:
        bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
        if context.area:
            context.area.tag_redraw()
        print("Draw Handler: Removed preview.")
        return True
    return False

def clear_all_preview_handlers():
    """Removes all active draw handlers managed by this module."""
    # --- PROMPT FOR CODING AGENT (IMPROVE HANDLER CLEARING ON UNREGISTER) ---
    # TASK: Ensure this function is called during addon unregistration or when Blender closes.
    # DETAILS: If not, draw handlers can persist and cause errors or unwanted drawing.
    #          This is part of the "robust handler management" task.
    # --- END PROMPT ---
    keys_to_remove = list(_active_draw_handlers.keys()) # Iterate over a copy
    count = 0
    for key in keys_to_remove:
        handler = _active_draw_handlers.pop(key, None)
        if handler:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handler, 'WINDOW')
                count +=1
            except Exception as e:
                print(f"Error removing draw handler: {e}")
    if count > 0:
        print(f"Draw Handler: Cleared {count} preview handlers.")
        # Redraw all 3D views to ensure cleared previews disappear
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()


def register():
    # Call clear_all_preview_handlers() here too, in case of re-registration without Blender restart
    # to clean up any orphaned handlers from a previous session of the addon.
    clear_all_preview_handlers()

def unregister():
    clear_all_preview_handlers()