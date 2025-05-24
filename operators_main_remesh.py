import bpy
from . import utils
from . import properties # For EvolverRemesherSettings
from . import core_remesh_logic # For the actual remeshing

class OBJECT_OT_EvolverRemeshOperator(bpy.types.Operator):
    bl_idname = "object.evolver_remesh_operator"
    bl_label = "Evolver Remesh"
    bl_description = "Performs advanced remeshing on the selected object(s)"
    bl_options = {'REGISTER', 'UNDO'}

    # --- PROMPT FOR CODING AGENT (MODAL OPERATOR IMPLEMENTATION) ---
    # TASK: Convert this operator to be MODAL for long remeshing processes.
    # DETAILS:
    #   - `execute()` should set up the remeshing task, add a modal handler (`context.window_manager.modal_handler_add(self)`),
    #     and return `{'RUNNING_MODAL'}`.
    #   - A `modal(self, context, event)` method will then be called repeatedly.
    #     - Handle events: `ESC` to cancel, `TIMER` to do a chunk of work.
    #     - Update progress: `context.window_manager.progress_update()`.
    #     - Return `{'RUNNING_MODAL'}` to continue, `{'FINISHED'}` or `{'CANCELLED'}` to stop.
    #   - The actual remeshing logic in `core_remesh_logic.py` needs to be designed to be iterative or pausable.
    # CHALLENGES:
    #   - Making the core C/C++ remeshing library (if used) pausable/iterative.
    #   - Managing state across modal calls.
    # CURRENT_IMPLEMENTATION: Synchronous (will freeze Blender for long operations).
    # --- END PROMPT ---

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
        # Could also check utils.get_selected_mesh_objects(context) if supporting multi-object

    def execute(self, context):
        # --- PROMPT FOR CODING AGENT (MULTI-OBJECT HANDLING) ---
        # TASK: Implement support for processing multiple selected mesh objects.
        # DETAILS:
        #   - Check `remesher_settings.process_mode` (ACTIVE or SELECTED - this property needs to be added to EvolverRemesherSettings).
        #   - If "SELECTED", iterate through `utils.get_selected_mesh_objects(context)`.
        #   - Each object might have its own `evolver_remesher_settings`.
        #   - Progress bar should reflect total progress across all objects.
        # CURRENT_IMPLEMENTATION: Processes active object only.
        # --- END PROMPT ---

        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            utils.report_message(self, 'ERROR', "No active mesh object selected.")
            return {'CANCELLED'}

        remesher_settings = active_obj.evolver_remesher_settings
        if not remesher_settings:
            utils.report_message(self, 'ERROR', f"Evolver Remesher settings not found on object '{active_obj.name}'.")
            return {'CANCELLED'}

        utils.report_message(self, 'INFO', f"Starting Evolver Remesh for '{active_obj.name}'...")
        
        # For progress bar (simple version)
        wm = context.window_manager
        wm.progress_begin(0, 100) # Min, Max for progress
        wm.progress_update(10) # Initial progress

        # --- 1. Feature Definition / Pre-processing ---
        # This is where you'd use `remesher_settings` related to features:
        # - `remesher_settings.use_marked_sharp`, `.use_marked_crease`, etc.
        # - `remesher_settings.main_auto_detect_angle`
        # - Potentially run the "Auto Mark Sharp Edges" system internally if configured,
        #   using `core_auto_sharp.auto_detect_and_mark_edges()` followed by `am4_apply_sharps_to_bmesh()`.
        #   This would modify the input BMesh *before* passing it to the core remesher.
        #
        # --- PROMPT FOR CODING AGENT (INTEGRATE AUTO-SHARP INTO MAIN REMESH FLOW) ---
        # TASK: Optionally run the Auto-Mark-Sharps system as a pre-processing step.
        # DETAILS:
        #   - Add a boolean setting to `EvolverRemesherSettings`, e.g., `run_auto_sharp_before_remesh: BoolProperty(...)`.
        #   - If true, get/create `EvolverAutoSharpSettings` (perhaps from scene or default),
        #     and call `core_auto_sharp.auto_detect_and_mark_edges()` then `am4_apply_sharps_to_bmesh()`
        #     on a BMesh representation of `active_obj.data`.
        #   - The `core_remesh_logic.perform_remeshing` would then receive this pre-processed BMesh.
        # --- END PROMPT ---
        wm.progress_update(20)


        # --- 2. Core Remeshing ---
        # This is the call to your main remeshing algorithm.
        # It needs the object's mesh data (likely as a BMesh) and all `remesher_settings`.
        
        # For non-destructive, we operate on a copy of the mesh data
        # and create a new object. For destructive, we modify in place.
        
        input_mesh_data = active_obj.data
        if remesher_settings.non_destructive_mode:
            # Create a copy of the mesh data to pass to the remesher
            # The remesher should then return new mesh data (verts, faces)
            # or a new BMesh that we convert.
            temp_bm = bmesh.new()
            temp_bm.from_mesh(input_mesh_data)
            # --- PROMPT FOR CODING AGENT (TRANSFORM HANDLING FOR REMESHER) ---
            # TASK: Decide if the core remesher operates in local or world space.
            # DETAILS:
            #   - If world space: `temp_bm.transform(active_obj.matrix_world)` before remeshing.
            #     The output mesh will be in world space; transform it back to local for the new object.
            #   - If local space: Pass `temp_bm` as is. New object will share original's transform.
            #   - This choice affects how guide curves, voxel sizes, etc., are interpreted.
            # Assume local space for now for simplicity.
            # --- END PROMPT ---
            
            # This is where the magic happens!
            new_mesh_data_tuple = core_remesh_logic.perform_remeshing(
                context, temp_bm, remesher_settings, active_obj # Pass original obj for context if needed
            )
            temp_bm.free()
        else: # Destructive
            # Directly operate on a BMesh of the active object
            bm = bmesh.new() # Or use edit mode bmesh if in edit mode
            bm.from_mesh(input_mesh_data)
            
            # --- PROMPT FOR CODING AGENT (DESTRUCTIVE MODE AND EDIT MODE) ---
            # TASK: Handle destructive remeshing correctly, especially if in Edit Mode.
            # DETAILS:
            #   - If in Edit Mode, `bm = bmesh.from_edit_mesh(input_mesh_data)` should be used.
            #   - After `core_remesh_logic.perform_remeshing` (which would modify `bm` in place),
            #     call `bmesh.update_edit_mesh(input_mesh_data)`.
            #   - The `core_remesh_logic.perform_remeshing` needs a flag or different signature
            #     to know if it should return new data or modify the input BMesh.
            # --- END PROMPT ---
            new_mesh_data_tuple = core_remesh_logic.perform_remeshing(
                context, bm, remesher_settings, active_obj
            )
            # If perform_remeshing modified bm in-place:
            # bm.to_mesh(active_obj.data)
            # active_obj.data.update()
            # bm.free()
            # This part needs careful design of core_remesh_logic interface.


        wm.progress_update(80)

        if new_mesh_data_tuple is None:
            utils.report_message(self, 'ERROR', "Remeshing failed or was cancelled by core logic.")
            wm.progress_end()
            return {'CANCELLED'}

        # --- 3. Output Handling & Data Transfer ---
        # `new_mesh_data_tuple` should be something like (verts, edges, faces) or a new BMesh.
        # Let's assume it's (verts_list_of_tuples, faces_list_of_tuples_of_vert_indices)
        
        output_verts, output_faces = new_mesh_data_tuple # Unpack as needed

        if not output_verts or not output_faces:
            utils.report_message(self, 'ERROR', "Remeshing returned no valid mesh data.")
            wm.progress_end()
            return {'CANCELLED'}

        # Create new mesh data block
        new_mesh = bpy.data.meshes.new(name=f"{active_obj.data.name}_remesh_data")
        new_mesh.from_pydata(output_verts, [], output_faces) # Empty list for edges, from_pydata reconstructs
        new_mesh.update() # Calculate normals, etc.
        new_mesh.validate()

        if remesher_settings.non_destructive_mode:
            new_obj_name = active_obj.name + remesher_settings.output_suffix
            new_obj = bpy.data.objects.new(new_obj_name, new_mesh)
            context.collection.objects.link(new_obj)

            # Copy transform from original
            new_obj.matrix_world = active_obj.matrix_world

            # --- PROMPT FOR CODING AGENT (DATA TRANSFER IMPLEMENTATION) ---
            # TASK: Implement data transfer (UVs, Vertex Colors, Weights, Shape Keys, etc.).
            # DETAILS:
            #   - This is a complex topic. Requires mapping data from the old mesh to the new one.
            #   - Blender's "Data Transfer" modifier/operator logic can be a reference.
            #   - Methods:
            #     - Nearest face/vertex sampling.
            #     - Barycentric coordinate interpolation for UVs/VCs within original faces.
            #     - For shape keys, it's particularly challenging.
            #   - Use `remesher_settings.transfer_uvs`, etc. flags.
            #   - This logic would ideally live in `core_remesh_logic.py` or a dedicated `data_transfer.py`.
            # CURRENT_IMPLEMENTATION: No data transfer.
            # --- END PROMPT ---
            if remesher_settings.transfer_uvs: print("Data Transfer: UVs (STUB)")
            if remesher_settings.transfer_vertex_colors: print("Data Transfer: VCols (STUB)")
            # ... etc.

            # Select new, deselect old
            active_obj.select_set(False)
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj
            
            utils.report_message(self, 'INFO', f"Remeshed '{active_obj.name}' into new object '{new_obj.name}'.")
        else: # Destructive
            # --- PROMPT FOR CODING AGENT (DESTRUCTIVE OUTPUT AND UNDO) ---
            # TASK: Ensure destructive mode correctly replaces mesh data and handles undo.
            # DETAILS:
            #   - `active_obj.data = new_mesh` (or modify BMesh in place and update).
            #   - Make sure `bl_options = {'REGISTER', 'UNDO'}` correctly captures this.
            #     Sometimes, complex mesh data swaps require manual undo pushes or careful handling.
            #   - If in Edit Mode, the BMesh was modified, and `update_edit_mesh` handles it.
            # --- END PROMPT ---
            
            # If not in edit mode and bm was used:
            # active_obj.data.clear_geometry() # Clear old geometry before assigning new
            # active_obj.data.vertices = new_mesh.vertices # This is not direct assignment
            # active_obj.data.edges = new_mesh.edges
            # active_obj.data.polygons = new_mesh.polygons
            # A simpler way for object mode destructive:
            old_mesh_name = active_obj.data.name
            bpy.data.meshes.remove(active_obj.data) # Remove old mesh data block if not used by others
            active_obj.data = new_mesh
            new_mesh.name = old_mesh_name # Keep original mesh data name if possible

            utils.report_message(self, 'INFO', f"Remeshed '{active_obj.name}' destructively.")


        wm.progress_update(100)
        wm.progress_end()
        return {'FINISHED'}


class OBJECT_OT_AssignSelectedAsGuides(bpy.types.Operator):
    bl_idname = "object.assign_selected_as_guides"
    bl_label = "Assign Selected Curves as Guides"
    bl_description = "Assigns selected Curve objects to the Guide Curves collection property"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Needs an active object with remesher settings to assign to,
        # and at least one selected curve object.
        active_obj = context.active_object
        if not (active_obj and hasattr(active_obj, 'evolver_remesher_settings')):
            return False
        
        selected_curves = [obj for obj in context.selected_objects if obj.type == 'CURVE']
        return len(selected_curves) > 0

    def execute(self, context):
        active_obj = context.active_object
        rem_settings = active_obj.evolver_remesher_settings

        selected_curves = [obj for obj in context.selected_objects if obj.type == 'CURVE']

        # --- PROMPT FOR CODING AGENT (GUIDE CURVE COLLECTION HANDLING) ---
        # TASK: Implement robust handling for assigning guide curves.
        # DETAILS:
        #   - Option 1 (Use a dedicated Collection):
        #     - If `rem_settings.guide_curves_collection` is None, create a new collection (e.g., "EvolverGuides_[ObjectName]").
        #     - Unlink selected curves from their current collections (optional, or just link to new one).
        #     - Link selected curves to the `rem_settings.guide_curves_collection`.
        #   - Option 2 (Store a list of Pointers - not standard for UI):
        #     - This is harder to manage with Blender's property system for UI.
        #   - The `PointerProperty(type=bpy.types.Collection)` is good. User can pick an existing collection too.
        #     This operator could help by creating one and adding selected curves to it if none is set.
        # CURRENT_IMPLEMENTATION: Placeholder. Needs to interact with `rem_settings.guide_curves_collection`.
        # --- END PROMPT ---

        if not rem_settings.guide_curves_collection:
            # Create a new collection
            guide_col_name = f"EvolverGuides_{active_obj.name}"
            existing_collections = bpy.data.collections
            if guide_col_name in existing_collections:
                rem_settings.guide_curves_collection = existing_collections[guide_col_name]
            else:
                new_col = bpy.data.collections.new(guide_col_name)
                context.scene.collection.children.link(new_col) # Link to scene's main collection
                rem_settings.guide_curves_collection = new_col
            utils.report_message(self, 'INFO', f"Created/Set Guide Curve Collection: '{rem_settings.guide_curves_collection.name}'")

        # Add selected curves to this collection
        if rem_settings.guide_curves_collection:
            added_count = 0
            for curve_obj in selected_curves:
                if curve_obj.name not in rem_settings.guide_curves_collection.objects:
                    # Unlink from other collections if you want them exclusively here (optional)
                    # for col in bpy.data.collections:
                    #     if curve_obj.name in col.objects:
                    #         col.objects.unlink(curve_obj)
                    rem_settings.guide_curves_collection.objects.link(curve_obj)
                    added_count +=1
            utils.report_message(self, 'INFO', f"Assigned {added_count} selected curves to guide collection '{rem_settings.guide_curves_collection.name}'.")
        else:
            utils.report_message(self, 'ERROR', "Could not set or find guide curve collection.")
            return {'CANCELLED'}
            
        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_EvolverRemeshOperator)
    bpy.utils.register_class(OBJECT_OT_AssignSelectedAsGuides)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_AssignSelectedAsGuides)
    bpy.utils.unregister_class(OBJECT_OT_EvolverRemeshOperator)