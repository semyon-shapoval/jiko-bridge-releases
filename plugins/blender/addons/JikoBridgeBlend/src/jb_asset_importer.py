import bpy

from .jb_api import JB_API

class JB_OT_AssetImport(bpy.types.Operator):
    bl_idname = "jiko_bridge.asset_import"
    bl_label = "Import Asset"
    bl_description = "Import Asset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        api = JB_API()

        asset = api.get_active_asset()

        if asset:
            bpy.ops.import_scene.fbx(filepath=asset.asset_path)
            return {'FINISHED'}

        return {'CANCELLED'}
