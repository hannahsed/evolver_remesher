bl_info = {
    "name": "Evolver Remesher",
    "author": "Your Name (with AI Assistant)",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),  # Minimum Blender version
    "location": "View3D > Sidebar > Evolver Tab | Object Properties > Evolver Remesher",
    "description": "Advanced remeshing tool with intelligent feature detection.",
    "warning": "This addon is in early development. Use with caution.",
    "doc_url": "",  # Link to your documentation
    "category": "Mesh",
}

import bpy

# Import order matters for registration/unregistration
from . import utils
from . import properties
from . import draw_handlers # Needs to be available for operators if they manage handlers
from . import core_auto_sharp # Core logic
from . import core_remesh_logic # Core logic
from . import operators_auto_sharp
from . import operators_main_remesh
from . import panels


modules = [
    utils,
    properties,
    draw_handlers,
    core_auto_sharp,
    core_remesh_logic,
    operators_auto_sharp,
    operators_main_remesh,
    panels,
]

def register():
    for module in modules:
        if hasattr(module, 'register'):
            module.register()
    
    # --- PROMPT FOR CODING AGENT ---
    # TASK: Add registration for any custom icons if you create an icons submodule.
    # Example:
    # from . import icons
    # icons.register()
    # --- END PROMPT ---

def unregister():
    for module in reversed(modules): # Unregister in reverse order
        if hasattr(module, 'unregister'):
            module.unregister()

    # --- PROMPT FOR CODING AGENT ---
    # TASK: Add unregistration for custom icons if implemented.
    # Example:
    # from . import icons
    # icons.unregister()
    # --- END PROMPT ---

if __name__ == "__main__":
    register()