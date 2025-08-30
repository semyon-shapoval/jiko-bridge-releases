import bpy

from .jb_commands_dialog import JB_PT_Panel
from .jb_asset_importer import JB_OT_AssetImport

classes = [
    JB_PT_Panel,
    JB_OT_AssetImport
]
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
