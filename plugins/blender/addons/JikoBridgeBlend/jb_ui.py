import sys
import bpy


class JB_PT_Commands(bpy.types.Panel):
    bl_label = "Jiko Bridge"
    bl_idname = "JB_PT_MAIN"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jiko Bridge"

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        col = layout.column(align=True)
        col.operator("jiko_bridge.asset_import", text="Import Asset", icon="IMPORT")
        col.operator("jiko_bridge.asset_export", text="Export Asset", icon="EXPORT")
        col.separator()
        col.operator("jiko_bridge.reload", text="Reload Addon", icon="FILE_REFRESH")


class JB_OT_Reload(bpy.types.Operator):
    bl_idname = "jiko_bridge.reload"
    bl_label = "Reload Addon"

    def execute(self, context):
        import addon_utils

        addon_utils.disable("JikoBridgeBlend")
        to_remove = [k for k in sys.modules if "JikoBridgeBlend" in k]
        for k in to_remove:
            del sys.modules[k]
        addon_utils.enable("JikoBridgeBlend")
        return {"FINISHED"}
