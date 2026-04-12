import sys
import os
import bpy

root_path = os.path.join(os.path.dirname(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

bl_info = {
    "name": "Jiko Bridge",
    "author": "JIKO",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar > Jiko Bridge",
    "description": "Jiko Bridge",
    "category": "3D View",
    "doc_url": "https://with-jiko.com",
    "tracker_url": "https://t.me/withjiko",
}

from .jb_commands import JB_PT_Commands, JB_OT_Reload
from .jb_asset_importer import JB_OT_AssetImport
from .jb_asset_exporter import JB_OT_AssetExport

classes = [
    JB_PT_Commands,
    JB_OT_Reload,
    JB_OT_AssetImport,
    JB_OT_AssetExport,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
