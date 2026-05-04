"""
Asset exporter for Jiko Bridge
Code by Semyon Shapoval, 2026
"""

from pathlib import Path

from src.jb_api import JbAPI
from src.jb_types import JbSource, AssetModel, AssetFile
from src.scene.jb_scene import JbScene
from src.jb_utils import get_logger
from src.jb_protocols import JbAssetExporterProtocol

logger = get_logger(__name__)


class JbAssetExporter(JbAssetExporterProtocol):
    """Export asset class"""

    def __init__(self, source: JbSource):
        self.api = JbAPI()
        self.scene = JbScene(source)

    def export_asset(self) -> None:
        """Export the selected asset or create a new one."""
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            for container in asset_containers:
                self._update_asset(container)
        else:
            self._create_new_asset(selected_objects)

    def export_message(self) -> str:
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            return "Update existing assets?\n" f"{len(asset_containers)} asset(s) will be updated"

        if selected_objects:
            return (
                "No asset containers found in selection. "
                f"Create new asset with {len(selected_objects)} object(s)?"
            )

        return "Export Blender project."

    def _collect_data(self):
        selected_objects = self.scene.walk(self.scene.get_selection())
        asset_containers = self.scene.get_containers_from_objects(selected_objects)
        return selected_objects, asset_containers

    def _update_asset(self, container) -> None:
        asset_model = self.scene.get_asset_data_from_container(container)
        if not asset_model:
            logger.error("Invalid asset information")
            return

        asset = self.api.get_asset(asset_model)
        if not asset or not asset.files or not asset.pack_name or not asset.asset_name:
            logger.error("Failed to fetch asset '%s'.", asset_model.asset_name)
            return

        if len(asset.files) != 1:
            logger.error(
                "Asset '%s' has %d files. Expected exactly 1 file for update.",
                asset_model.asset_name,
                len(asset.files),
            )
            return

        file = asset.files[0]
        if not file.filepath:
            logger.error(
                "Filepath missing for asset '%s'. Cannot export.",
                asset_model.asset_name,
            )
            return

        ext = Path(file.filepath.lower()).suffix
        if not ext:
            logger.error(
                "Unable to determine export extension from filepath '%s' for '%s'.",
                file.filepath,
                asset_model.asset_name,
            )
            return

        filepath = self.scene.export_with_temp([container], ext)

        if not filepath:
            return

        asset.files = [
            AssetFile(filepath=filepath, asset_type=file.asset_type, bridge_type=file.bridge_type)
        ]

        self.api.update_asset(asset)

    def _create_new_asset(self, objects) -> None:
        filepath = self.scene.export_with_temp(objects, ".fbx")
        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset(AssetModel(files=[AssetFile(filepath=filepath)]))

        if not asset or not asset.files:
            logger.error("No asset found for filepath '%s'", filepath)
            return

        for file in asset.files:
            container, _ = self.scene.get_or_create_asset_container(asset, file)
            self.scene.move_objects_to_container(objects, container)
            logger.info("Asset '%s' created with type '%s'.", asset.asset_name, file.asset_type)
