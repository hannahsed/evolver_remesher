import bpy
import bmesh
from contextlib import contextmanager

@contextmanager
def bmesh_from_obj(obj, mode='OBJECT', use_world_matrix=False):
    """Context manager for easy bmesh access from an object."""
    if obj is None or obj.type != 'MESH':
        # --- PROMPT FOR CODING AGENT ---
        # TASK: Raise a more specific custom exception or handle this error more gracefully upstream.
        # DETAILS: For now, it prints an error and yields None, which callers must check.
        # --- END PROMPT ---
        print(f"ERROR: {__name__} - Cannot get BMesh from non-mesh or None object: {obj}")
        yield None
        return

    bm = None
    original_mode = bpy.context.mode
    active_object_was = bpy.context.active_object
    selected_objects_were = bpy.context.selected_objects[:]

    try:
        if mode == 'EDIT' and obj.mode == 'EDIT':
            # bpy.ops.object.mode_set(mode='EDIT') # Already in edit mode
            bm = bmesh.from_edit_mesh(obj.data)
        elif mode == 'EDIT' and obj.mode != 'EDIT':
            # --- PROMPT FOR CODING AGENT ---
            # TASK: Review mode switching logic.
            # DETAILS: Forcing mode changes can be disruptive and have side effects.
            # Consider if it's better to operate on a copy in object mode if edit mode isn't active,
            # or clearly document that the operator requires edit mode.
            # For now, we'll switch, but this needs careful thought for UX.
            # --- END PROMPT ---
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
        else: # OBJECT mode or other
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            if use_world_matrix:
                bm.transform(obj.matrix_world)
        
        # Ensure lookup tables for faster access
        if bm:
            bm.verts.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
        
        yield bm

    finally:
        if bm:
            if mode == 'EDIT' and obj.mode == 'EDIT': # Was already in edit mode
                bmesh.update_edit_mesh(obj.data) # Necessary to see changes
                # Do not free bm from edit_mesh
            elif mode == 'EDIT' and original_mode != 'EDIT': # We switched to edit mode
                bmesh.update_edit_mesh(obj.data)
                bpy.ops.object.mode_set(mode=original_mode) # Switch back
                # Restore selection and active object
                bpy.context.view_layer.objects.active = active_object_was
                for sel_obj in bpy.data.objects: # More robust selection restoration
                    sel_obj.select_set(sel_obj in selected_objects_were)
            else: # OBJECT mode
                # If changes were made and need to be written back to obj.data:
                # bm.to_mesh(obj.data) # This is done by the caller usually
                bm.free()
        
        # --- PROMPT FOR CODING AGENT ---
        # TASK: Enhance the restoration of Blender's context.
        # DETAILS: Restoring active object and selection can be tricky. Ensure this
        #          part is robust, especially if the context manager is used within
        #          operators that might themselves alter selection.
        # --- END PROMPT ---

def get_selected_mesh_objects(context):
    """Returns a list of selected mesh objects, with the active one first if selected."""
    selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
    active = context.active_object
    if active and active.type == 'MESH' and active in selected:
        selected.remove(active)
        return [active] + selected
    elif active and active.type == 'MESH' and active not in selected:
        # If active is a mesh but not selected, process it if an option allows
        # For now, only return selected
        return selected
    return selected


def report_message(operator, level, message):
    """Helper for operator reporting."""
    print(f"EvolverRemesher ({level}): {message}") # Also print to console for debugging
    operator.report({level}, message)


# --- PROMPT FOR CODING AGENT ---
# TASK: Add more utility functions as needed.
# EXAMPLES:
#   - Functions for vector math if 'mathutils' is not sufficient or for specific common operations.
#   - Helper for getting custom data layers (UVs, vertex colors) from BMesh.
#   - Functions for checking mesh validity (manifold, etc.) if required by algorithms.
# --- END PROMPT ---

def register():
    pass # No classes to register in utils

def unregister():
    pass