import bpy

from .jb_api import JB_API
from .jb_asset_model import AssetModel
from .jb_scene_manager import JBSceneManager
from .jb_logger import get_logger

logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBSceneManager()

    def export_asset(self) -> None:
        asset_container = self.scene.get_selected_asset_container()
        if asset_container:
            self._update_asset(asset_container)
        else:
            self._create_new_asset(self.scene.get_selection())

    def _update_asset(self, container) -> None:
        asset = self.scene.get_asset_info(container)
        if not asset:
            logger.error("Invalid asset information on container: %s", container.name)
            return

        if not self.scene.confirm(
            f"Update asset '{asset.asset_name}'?\nThis will overwrite the existing file."
        ):
            return

        objects = self.scene.get_objects_recursive(container)
        if not objects:
            logger.error("Container '%s' has no objects for export.", container.name)
            return

        ext = self._detect_ext(objects)
        filepath = self.scene.export_to_temp_file(objects, ext)
        if not filepath:
            return

        if self.api.update_asset(
            filepath,
            asset.pack_name,
            asset.asset_name,
            asset.asset_type,
            asset.database_name,
        ):
            logger.info("Asset '%s' updated successfully.", asset.asset_name)
        else:
            logger.error("Failed to update asset '%s'.", asset.asset_name)

    def _create_new_asset(self, objects: list) -> None:
        if not self.scene.confirm(
            "Create new asset from selected objects? Go to Jiko Bridge app to finish setup."
        ):
            return

        ext = self._detect_ext(objects)
        filepath = self.scene.export_to_temp_file(objects, ext)
        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset(filepath)
        if not asset:
            logger.error("Failed to create asset.")
            return

        container, _ = self.scene.get_or_create_asset(asset)
        self.scene.move_objects_to_container(objects, container)
        logger.info("Asset '%s' created.", asset.asset_name)

    def _detect_ext(self, objects: list) -> str:
        return ".abc" if self.scene.has_instances(objects) else ".fbx"


class JB_OT_AssetExport(bpy.types.Operator):
    bl_idname = "jiko_bridge.asset_export"
    bl_label = "Export Asset"
    bl_description = "Export selected objects as a new asset or update existing"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        exporter = JB_AssetExporter()
        exporter.export_asset()
        return {"FINISHED"}
