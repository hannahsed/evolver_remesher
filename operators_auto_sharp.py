import bpy
import bmesh
from . import utils
from . import properties # To access EvolverAutoSharpSettings
from . import core_auto_sharp
from . import draw_handlers

# --- Global or better, operator-instance storage for previewed BMesh edges ---
# This is a tricky part. Storing BMesh data directly long-term is problematic.
# Storing edge indices and the object they relate to is safer.
# For the preview, we need the BMEdge objects temporarily to pass to the draw_handler setup.
_transient_preview_bmesh_edges = None # Stores set of BMEdge from the preview BMesh
_transient_preview_object_name = None # Name of the object being previewed

class OBJECT_OT_EvolverAutoDetectPreviewSharps(bpy.types.Operator):
    bl_idname = "object.evolver_auto_detect_preview_sharps"
    bl_label = "Preview Auto Sharps"
    bl_description = "Detects and previews sharp edges based on current settings without applying them"
    bl_options = {'REGISTER', 'UNDO_GROUPED'} # Group with apply for single undo if used sequentially

    # --- PROMPT FOR CODING AGENT (OPERATOR PROPERTIES FOR AUTO-SHARP) ---
    # TASK: Decide if Auto-Sharp settings should be operator properties (for `invoke_props_dialog`)
    #       or if they are always read from `context.scene.evolver_auto_sharp_settings`.
    # DETAILS:
    #   - If operator properties: Define them here, and `invoke()` can show a dialog.
    #     This is good for a one-off operation with settings adjustment.
    #   - If scene properties: The panel updates them, and this operator just reads them.
    #     This is good for iterative adjustment via a panel.
    #   - The current `properties.py` puts `EvolverAutoSharpSettings` on the Scene. This operator will use that.
    #     No extra properties needed here unless you want an `invoke_props_dialog`.
    # --- END PROMPT ---

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode in {'OBJECT', 'EDIT'}

    def execute(self, context):
        global _transient_preview_bmesh_edges, _transient_preview_object_name
        
        obj = context.active_object
        auto_sharp_settings = context.scene.evolver_auto_sharp_settings # Get from Scene

        if not auto_sharp_settings:
            utils.report_message(self, 'ERROR', "Auto Sharp settings not found.")
            return {'CANCELLED'}

        # Clear previous preview first, regardless of object
        draw_handlers.remove_preview_handler(context)
        _transient_preview_bmesh_edges = None
        _transient_preview_object_name = None

        # Use the bmesh context manager from utils
        # Important: For preview, we operate on a *copy* of the mesh data in object mode,
        # or directly on edit_mesh data. The context manager handles this.
        # The bmesh itself won't be modified by the preview, only read.
        mode_for_bmesh = 'EDIT' if obj.mode == 'EDIT' else 'OBJECT'
        
        with utils.bmesh_from_obj(obj, mode=mode_for_bmesh) as bm:
            if bm is None:
                utils.report_message(self, 'ERROR', f"Could not get BMesh from object '{obj.name}'.")
                return {'CANCELLED'}

            # Ensure freshest data if in edit mode
            if obj.mode == 'EDIT':
                bm.verts.ensure_lookup_table() # etc. are done by context manager
            
            # Run the core detection logic
            # This function returns a set of BMEdge objects from the `bm` passed to it.
            detected_bm_edges = core_auto_sharp.auto_detect_and_mark_edges(bm, auto_sharp_settings)

            if not detected_bm_edges:
                utils.report_message(self, 'INFO', "No sharp edges detected for preview.")
                # No need to call remove_preview_handler again, already done above.
                return {'FINISHED'}

            # Store these BMEdge objects TEMPORARILY for the draw_handler setup.
            # This is a bit risky if the BMesh (`bm`) is freed before draw_handler uses them.
            # `add_preview_handler` copies coordinates, so it should be okay.
            _transient_preview_bmesh_edges = detected_bm_edges 
            _transient_preview_object_name = obj.name

            draw_handlers.add_preview_handler(context, obj, _transient_preview_bmesh_edges)
            utils.report_message(self, 'INFO', f"Previewing {len(detected_bm_edges)} potential sharp edges.")
            
            # --- PROMPT FOR CODING AGENT (BMESH LIFECYCLE FOR PREVIEW) ---
            # TASK: Critically review the BMesh lifecycle for preview.
            # DETAILS:
            #   - `_transient_preview_bmesh_edges` stores BMEdge objects. If the `bm` from `bmesh_from_obj`
            #     is freed (which it is for object mode), these BMEdge objects become invalid.
            #   - `draw_handlers.add_preview_handler` was modified to copy vertex coordinates from these
            #     BMEdges *before* the BMesh is potentially freed. This should mitigate the issue.
            #   - Ensure this path is robust. If `bm` comes from `from_edit_mesh`, it's not freed by the
            #     context manager, so BMEdge refs remain valid as long as edit mode is active and mesh doesn't change topology.
            # --- END PROMPT ---

        return {'FINISHED'}


class OBJECT_OT_EvolverAutoApplySharps(bpy.types.Operator):
    bl_idname = "object.evolver_auto_apply_sharps"
    bl_label = "Apply Auto Sharps"
    bl_description = "Applies the auto-detected sharp edges to the mesh"
    bl_options = {'REGISTER', 'UNDO'}

    # --- PROMPT FOR CODING AGENT (APPLY FROM PREVIEW OR RECALCULATE?) ---
    # TASK: Decide if "Apply" uses the last previewed edges or always recalculates.
    # DETAILS:
    #   - Option 1 (Use Preview): If `_transient_preview_bmesh_edges` and `_transient_preview_object_name` match
    #     the current context, apply these. This is faster if settings haven't changed.
    #     Challenge: What if the mesh was edited after preview? The BMEdge refs might be invalid.
    #                Storing edge *indices* from preview might be more robust if mesh topology doesn't change.
    #   - Option 2 (Recalculate): Always run `core_auto_sharp.auto_detect_and_mark_edges` again. Safer, ensures
    #     latest mesh state and settings are used, but can be slower.
    # CURRENT_IMPLEMENTATION: Recalculates for safety and simplicity.
    # --- END PROMPT ---

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and obj.mode in {'OBJECT', 'EDIT'}

    def execute(self, context):
        global _transient_preview_bmesh_edges, _transient_preview_object_name # For potentially clearing preview state
        
        obj = context.active_object
        auto_sharp_settings = context.scene.evolver_auto_sharp_settings

        if not auto_sharp_settings:
            utils.report_message(self, 'ERROR', "Auto Sharp settings not found.")
            return {'CANCELLED'}

        original_mode = obj.mode
        bm = None
        
        try:
            if obj.mode == 'EDIT':
                # Need to ensure we are on the right object if multi-editing
                # For simplicity, assume active_object is the target in edit mode.
                bm = bmesh.from_edit_mesh(obj.data)
            else: # Object mode
                bm = bmesh.new()
                bm.from_mesh(obj.data)

            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            # Run detection (safer to re-run than trust potentially stale preview data)
            final_edges_to_mark_bm = core_auto_sharp.auto_detect_and_mark_edges(bm, auto_sharp_settings)

            if not final_edges_to_mark_bm:
                utils.report_message(self, 'INFO', "No sharp edges detected to apply.")
                if obj.mode == 'OBJECT' and bm: bm.free()
                return {'FINISHED'}

            # AM4: Apply these edges to the BMesh
            # The `core_auto_sharp.am4_apply_sharps_to_bmesh` function is responsible for this.
            # It needs the set of BMEdge objects from the *current* BMesh `bm`.
            marked_count = core_auto_sharp.am4_apply_sharps_to_bmesh(bm, final_edges_to_mark_bm, auto_sharp_settings)

            if marked_count > 0:
                if obj.mode == 'EDIT':
                    bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=False)
                else: # Object mode
                    bm.to_mesh(obj.data)
                    obj.data.update() # Crucial for custom normals and other non-geometry data to refresh
                
                utils.report_message(self, 'INFO', f"Applied {marked_count} sharp edges to '{obj.name}'.")
                
                # Clear preview after applying, as it's now "baked"
                draw_handlers.remove_preview_handler(context)
                _transient_preview_bmesh_edges = None
                _transient_preview_object_name = None
            else:
                utils.report_message(self, 'INFO', "No edges were marked (either none detected or filter removed all).")

        except Exception as e:
            utils.report_message(self, 'ERROR', f"Error applying sharps: {e}")
            # --- PROMPT FOR CODING AGENT (TRACEBACK LOGGING) ---
            # TASK: Log the full traceback for exceptions.
            # import traceback; traceback.print_exc()
            # --- END PROMPT ---
            return {'CANCELLED'}
        finally:
            if obj.mode == 'OBJECT' and bm:
                bm.free()
        
        return {'FINISHED'}


class OBJECT_OT_EvolverClearPreviewSharps(bpy.types.Operator):
    bl_idname = "object.evolver_clear_preview_sharps"
    bl_label = "Clear Preview Sharps"
    bl_description = "Clears any active sharp edge preview"
    bl_options = {'REGISTER', 'INTERNAL'} # Internal usually means not shown in search

    # No poll needed, can always try to clear

    def execute(self, context):
        global _transient_preview_bmesh_edges, _transient_preview_object_name
        
        if draw_handlers.remove_preview_handler(context):
            _transient_preview_bmesh_edges = None
            _transient_preview_object_name = None
            utils.report_message(self, 'INFO', "Sharp edge preview cleared.")
        else:
            utils.report_message(self, 'INFO', "No active sharp edge preview to clear.")
        return {'FINISHED'}

# --- PROMPT FOR CODING AGENT (CLEAR ALL SHARPS OPERATOR) ---
# TASK: Implement an operator `OBJECT_OT_EvolverClearAllMarkedSharps`.
# DETAILS:
#   - This operator should iterate through all edges of the active mesh object.
#   - It should set `edge.use_edge_sharp = False` for all edges.
#   - Optionally, provide options to also clear `edge.crease` and `edge.seam` if desired.
#   - Handle both Object and Edit modes.
#   - `bl_options = {'REGISTER', 'UNDO'}`.
# --- END PROMPT ---


def register():
    bpy.utils.register_class(OBJECT_OT_EvolverAutoDetectPreviewSharps)
    bpy.utils.register_class(OBJECT_OT_EvolverAutoApplySharps)
    bpy.utils.register_class(OBJECT_OT_EvolverClearPreviewSharps)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_EvolverClearPreviewSharps)
    bpy.utils.unregister_class(OBJECT_OT_EvolverAutoApplySharps)
    bpy.utils.unregister_class(OBJECT_OT_EvolverAutoDetectPreviewSharps)
    
    # Ensure any lingering previews are cleared on unregister
    draw_handlers.clear_all_preview_handlers() # Call the global clearer