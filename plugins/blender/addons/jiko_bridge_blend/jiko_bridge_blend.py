"""
Jiko Bridge - Blender Addon
Code by Semyon Shapoval, 2026
"""

import bpy
from .src.jb_commands import JB_PT_Commands
from .src.jb_asset_exporter import JbAssetExporter
from .src.jb_asset_importer import JbAssetImporter
from .src.jb_utils import reload_plugin_modules


class JB_OT_AssetImport(bpy.types.Operator):  # pylint: disable=invalid-name
    """Import asset from Jiko Bridge."""

    bl_idname = "jiko_bridge.asset_import"
    bl_label = "Import Asset"
    bl_description = "Import active asset from Jiko Bridge"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, _context):
        importer = JbAssetImporter(_context)
        importer.import_assets()
        return {"FINISHED"}


class JB_OT_AssetExport(bpy.types.Operator):  # pylint: disable=invalid-name
    """Export asset to Jiko Bridge."""

    bl_idname = "jiko_bridge.asset_export"
    bl_label = "Export Asset"
    bl_description = "Export selected objects as a new asset or update existing"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        exporter = JbAssetExporter(context)
        exporter.export_asset()
        return {"FINISHED"}


class JB_OT_Reload(bpy.types.Operator):  # pylint: disable=invalid-name
    """Reloads the Jiko Bridge addon."""

    bl_idname = "jiko_bridge.reload"
    bl_label = "Reload Addon"

    def execute(self, _context):
        reload_plugin_modules()
        return {"FINISHED"}


classes = [
    JB_PT_Commands,
    JB_OT_Reload,
    JB_OT_AssetExport,
    JB_OT_AssetImport,
]


def register():
    """Register addon classes."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister addon classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
