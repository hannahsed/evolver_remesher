import bpy
from . import properties # For settings classes

class EVOLVER_PT_MainPanel(bpy.types.Panel):
    bl_label = "Evolver Remesher"
    bl_idname = "OBJECT_PT_evolver_remesher_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Evolver" # Tab name in the N-Panel

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.object
        
        if not obj or not hasattr(obj, 'evolver_remesher_settings'):
            layout.label(text="No mesh object selected or settings not initialized.")
            # --- PROMPT FOR CODING AGENT (SETTINGS INITIALIZATION) ---
            # TASK: Ensure evolver_remesher_settings are initialized if missing.
            # DETAILS: Sometimes PointerProperties can be None. A button or automatic
            #          initialization on first draw might be needed if an object is selected
            #          but its settings property is somehow missing (shouldn't happen if registered).
            # --- END PROMPT ---
            return

        settings = obj.evolver_remesher_settings
        auto_sharp_settings = context.scene.evolver_auto_sharp_settings # Global auto-sharp settings

        # --- Main Remesh Operator ---
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("object.evolver_remesh_operator", text="Evolver Remesh", icon='MOD_REMESH')
        
        # --- Target Resolution ---
        box = layout.box()
        box.label(text="Target Resolution:")
        box.prop(settings, "target_mode", text="") # No label, already clear from section
        
        if settings.target_mode == 'POLYCOUNT':
            row = box.row(align=True)
            row.prop(settings, "polycount_is_percentage", text="Relative")
            if settings.polycount_is_percentage:
                row.prop(settings, "polycount_percentage", text="Factor")
            else:
                row.prop(settings, "polycount_absolute", text="Count")
        elif settings.target_mode == 'EDGE_LENGTH':
            box.prop(settings, "avg_edge_length")
        elif settings.target_mode == 'VOXEL_SIZE':
            box.prop(settings, "voxel_size_absolute")

        # --- Feature Definition (Main Remesher) ---
        box = layout.box()
        col = box.column()
        col.label(text="Feature Preservation (Remesher):")
        col.prop(settings, "main_auto_detect_angle", text="Sharp Angle")
        col.prop(settings, "use_marked_sharp")
        
        row = col.row(align=True)
        row.prop(settings, "use_marked_crease")
        sub = row.row(align=True)
        sub.enabled = settings.use_marked_crease
        sub.prop(settings, "crease_threshold", text="Min")
        
        col.prop(settings, "use_marked_seam")
        
        row = col.row(align=True)
        row.prop(settings, "use_bevel_weights_remesher") # Use the renamed property
        sub = row.row(align=True)
        sub.enabled = settings.use_bevel_weights_remesher
        sub.prop(settings, "bevel_weight_threshold_remesher", text="Min") # Renamed
        
        col.prop(settings, "hard_edge_strictness")

        # --- Auto Mark Sharp Edges Sub-Panel / Section ---
        auto_sharp_box = layout.box()
        row = auto_sharp_box.row()
        row.label(text="Auto-Mark Sharp Edges:")
        # --- PROMPT FOR CODING AGENT (AUTO-SHARP UI PLACEMENT) ---
        # TASK: Decide if Auto-Sharp settings are in their own collapsible sub-panel or always visible.
        # DETAILS: The architectural plan (3.5) lists many parameters.
        #          A sub-panel or a modal operator invoked by a button might be cleaner.
        #          For now, direct properties from scene.evolver_auto_sharp_settings.
        # --- END PROMPT ---
        if auto_sharp_settings:
            auto_sharp_box.prop(auto_sharp_settings, "auto_sharp_primary_angle")
            auto_sharp_box.prop(auto_sharp_settings, "auto_sharp_use_curvature")
            if auto_sharp_settings.auto_sharp_use_curvature:
                auto_sharp_box.prop(auto_sharp_settings, "auto_sharp_curvature_sensitivity", slider=True)
            
            col = auto_sharp_box.column(align=True)
            col.label(text="Consider Existing Data:")
            col.prop(auto_sharp_settings, "auto_sharp_use_existing_sharps", text="Blender Sharps")
            row = col.row(align=True)
            row.prop(auto_sharp_settings, "auto_sharp_use_existing_creases", text="Blender Creases")
            sub_row = row.row(align=True)
            sub_row.enabled = auto_sharp_settings.auto_sharp_use_existing_creases
            sub_row.prop(auto_sharp_settings, "auto_sharp_min_crease_value", text="Min")

            col.prop(auto_sharp_settings, "auto_sharp_use_existing_seams", text="Blender Seams")
            row = col.row(align=True)
            row.prop(auto_sharp_settings, "auto_sharp_use_bevel_weights", text="Blender Bevel Weights")
            sub_row = row.row(align=True)
            sub_row.enabled = auto_sharp_settings.auto_sharp_use_bevel_weights
            sub_row.prop(auto_sharp_settings, "auto_sharp_min_bevel_weight", text="Min")

            auto_sharp_box.prop(auto_sharp_settings, "auto_sharp_preserve_uv_boundaries")
            auto_sharp_box.prop(auto_sharp_settings, "auto_sharp_min_feature_length")

            row = auto_sharp_box.row(align=True)
            row.operator("object.evolver_auto_detect_preview_sharps", text="Preview Sharps", icon='HIDE_OFF')
            row.operator("object.evolver_auto_apply_sharps", text="Apply Sharps", icon='CHECKMARK')
            row.operator("object.evolver_clear_preview_sharps", text="", icon='X') # Clear Preview
        else:
            auto_sharp_box.label(text="Auto-Sharp settings not available.")

        # --- Output Topology ---
        box = layout.box()
        box.label(text="Output Topology:")
        box.prop(settings, "quad_dominance", slider=True)
        box.prop(settings, "attempt_pure_quads")

        # --- Edge Flow Control ---
        box = layout.box()
        box.label(text="Edge Flow & Symmetry:")
        box.prop(settings, "curvature_influence", slider=True)
        col = box.column(align=True)
        col.label(text="Symmetry Axes:")
        row = col.row(align=True)
        row.prop(settings, "symmetry_x", text="X", toggle=True)
        row.prop(settings, "symmetry_y", text="Y", toggle=True)
        row.prop(settings, "symmetry_z", text="Z", toggle=True)
        
        col.separator()
        col.label(text="Guide Curves:")
        col.prop(settings, "guide_curves_collection", text="") # Show selected collection
        col.operator("object.assign_selected_as_guides", text="Assign Selected as Guides", icon='CURVE_PATH')

        # --- Detail & Quality ---
        box = layout.box()
        box.label(text="Detail & Quality:")
        box.prop(settings, "detail_capture_bias", slider=True)
        box.prop(settings, "quality_preset") # Update function needs to be implemented
        if settings.quality_preset == 'CUSTOM':
            box.prop(settings, "max_quad_aspect_ratio")
            box.prop(settings, "relaxation_iterations")
        
        # --- Data Transfer ---
        box = layout.box()
        box.label(text="Data Transfer:")
        col = box.column(align=True)
        col.prop(settings, "transfer_uvs")
        col.prop(settings, "transfer_vertex_colors")
        col.prop(settings, "transfer_vertex_groups")
        # col.prop(settings, "transfer_custom_normals") # Marked experimental
        # col.prop(settings, "transfer_shape_keys") # Marked experimental

        # --- Advanced Options ---
        layout.prop(settings, "show_advanced_options", toggle=True, icon='TRIA_DOWN' if settings.show_advanced_options else 'TRIA_RIGHT')
        if settings.show_advanced_options:
            adv_box = layout.box()
            adv_box.label(text="Advanced:")
            adv_box.prop(settings, "preserve_uv_island_boundaries_remesher") # Renamed property
            
            adv_box.prop(settings, "use_adaptive_density_map")
            if settings.use_adaptive_density_map:
                sub_box = adv_box.box()
                sub_box.prop(settings, "density_map_type", text="Map Type")
                if settings.density_map_type == 'VERTEX_GROUP':
                    sub_box.prop_search(settings, "density_vertex_group", obj, "vertex_groups", text="Group")
                elif settings.density_map_type == 'VERTEX_COLOR':
                    sub_box.prop_search(settings, "density_vertex_color_layer", obj.data, "vertex_colors", text="Layer")
            
            adv_box.prop(settings, "boundary_handling")
            adv_box.prop(settings, "non_destructive_mode")
            if settings.non_destructive_mode:
                adv_box.prop(settings, "output_suffix")

class EVOLVER_PT_ObjectPropertiesPanel(bpy.types.Panel):
    bl_label = "Evolver Remesher"
    bl_idname = "OBJECT_PT_evolver_remesher_object_props"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object" # Show in Object Properties tab

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def draw(self, context):
        # Re-use the main panel's draw method for consistency.
        # This avoids duplicating UI code.
        # The main panel needs to be careful not to assume it's always in VIEW_3D.
        # For now, this should work as EVOLVER_PT_MainPanel uses `layout = self.layout`.
        EVOLVER_PT_MainPanel.draw(self, context)
        # --- PROMPT FOR CODING AGENT (PANEL DRAW REFACTOR) ---
        # TASK: Refactor panel drawing logic to avoid direct calls like `EVOLVER_PT_MainPanel.draw()`.
        # DETAILS:
        #   - Create a common drawing function `def draw_evolver_ui(layout, context):`
        #     that both panels can call.
        #   - This makes the UI code more modular and maintainable.
        #   - The common function would take `layout` and `context` as arguments.
        # --- END PROMPT ---


def register():
    bpy.utils.register_class(EVOLVER_PT_MainPanel)
    bpy.utils.register_class(EVOLVER_PT_ObjectPropertiesPanel)

def unregister():
    bpy.utils.unregister_class(EVOLVER_PT_ObjectPropertiesPanel)
    bpy.utils.unregister_class(EVOLVER_PT_MainPanel)