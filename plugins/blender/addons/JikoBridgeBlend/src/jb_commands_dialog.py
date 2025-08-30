import bpy

class JB_PT_Panel(bpy.types.Panel):
    bl_label = "Jiko Bridge"
    bl_idname = "JB_Commands_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Jiko Bridge"

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)

        col.operator("jiko_bridge.asset_import", text="Import")
