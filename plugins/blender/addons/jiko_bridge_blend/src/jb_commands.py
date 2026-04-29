"""
Commands Module
Code by Semyon Shapoval, 2026
"""

import bpy


class JB_PT_Commands(bpy.types.Panel):  # pylint: disable=invalid-name
    """Main panel for Jiko Bridge commands."""

    bl_label = "Jiko Bridge"
    bl_idname = "JB_PT_MAIN"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jiko Bridge"

    def draw(self, _context: bpy.types.Context):
        layout = self.layout

        if not layout:
            return

        col = layout.column(align=True)
        col.operator("jiko_bridge.asset_import", text="Import Asset", icon="IMPORT")
        col.operator("jiko_bridge.asset_export", text="Export Asset", icon="EXPORT")
        col.separator()
        col.operator("jiko_bridge.reload", text="Reload Addon", icon="FILE_REFRESH")
