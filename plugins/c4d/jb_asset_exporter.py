import os

from jb_api import JB_API
from jb_utils import confirm
from jb_logger import get_logger
from scene.jb_scene import JBScene
from jb_asset_model import AssetInfo

logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBScene()

    def export_asset(self) -> None:
        asset_container = self.scene.get_selected_asset_container()
        if asset_container:
            self._update_asset(asset_container)
        else:
            self._create_new_asset(self.scene.get_selection())

    def _update_asset(self, container) -> None:
        assetInfo = AssetInfo.get_asset_info(container)
        if not assetInfo:
            logger.error(
                "Invalid asset information on container: %s", container.GetName()
            )
            return

        if not confirm(
            f"Update asset '{assetInfo.asset_name}'?\nThis will overwrite the existing file."
        ):
            return

        objects = self.scene.get_objects_recursive(container)
        if not objects:
            logger.error(
                "Container '%s' has no objects for export.", container.GetName()
            )
            return

        asset = self.api.get_asset(
            assetInfo.pack_name,
            assetInfo.asset_name,
            assetInfo.database_name,
            [assetInfo.asset_type],
        )
        if not asset or not asset.files:
            logger.error("Failed to fetch asset '%s'.", assetInfo.asset_name)
            return

        model_file = next(
            (
                f
                for f in asset.files
                if f.bridge_type == "model" and f.asset_type == assetInfo.asset_type
            ),
            None,
        )
        if not model_file:
            logger.error("No model file found for asset '%s'.", assetInfo.asset_name)
            return

        ext = os.path.splitext(model_file.file_path)[1]
        if not ext:
            logger.error(
                "Unable to determine export extension from file_path '%s' for '%s'.",
                model_file.file_path,
                assetInfo.asset_name,
            )
            return

        filepath = self.scene.export_with_temp(objects, ext)
        if not filepath:
            return

        if self.api.update_asset(
            filepath,
            asset.pack_name,
            asset.asset_name,
            model_file.asset_type,
            asset.database_name,
        ):
            logger.info("Asset '%s' updated successfully.", assetInfo.asset_name)
        else:
            logger.error("Failed to update asset '%s'.", assetInfo.asset_name)

    def _create_new_asset(self, objects: list) -> None:
        if not confirm(
            "Create new asset from selected objects? Go to Jiko Bridge app to finish setup."
        ):
            return

        filepath = self.scene.export_with_temp(objects, ".fbx")
        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset(filepath)
        if not asset:
            logger.error("Failed to create asset.")
            return

        container, _ = self.scene.get_or_create_asset_container(asset)
        self.scene.move_objects_to_container(objects, container)
        logger.info("Asset '%s' created.", asset.asset_name)
