import bpy
from .jb_asset_importer import JB_AssetImporter
from .jb_asset_exporter import JB_AssetExporter
from .jb_commands import JB_PT_Commands, JB_OT_Reload

class JB_OT_AssetImport(bpy.types.Operator):
    bl_idname = "jiko_bridge.asset_import"
    bl_label = "Import Asset"
    bl_description = "Import active asset from Jiko Bridge"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        importer = JB_AssetImporter()
        importer.import_assets(context)
        return {"FINISHED"}

class JB_OT_AssetExport(bpy.types.Operator):
    bl_idname = "jiko_bridge.asset_export"
    bl_label = "Export Asset"
    bl_description = "Export selected objects as a new asset or update existing"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        exporter = JB_AssetExporter()
        exporter.export_asset(context)
        return {"FINISHED"}


classes = [
    JB_PT_Commands,
    JB_OT_Reload,
    JB_OT_AssetExport,
    JB_OT_AssetImport,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
