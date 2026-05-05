"""
Integration tests for Jiko Bridge
Code by Semyon Shapoval, 2026
"""

import os
import sys
import uuid
import unittest
from unittest.mock import patch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, root_dir)


# pylint: disable=wrong-import-position disable=import-error
from plugins.cinema4d.src.jb_types import AssetModel, AssetFile
from tests.integration.cinema4d.c4d_scene_helper import C4DSceneHelper
from tests.integration.jb_utils import (
    make_injected_create_asset,
    get_logger,
)

log = get_logger(__name__)


class TestC4DJikoBridge(unittest.TestCase):
    """Integration tests for Jiko Bridge."""

    @property
    def suffix(self) -> str:
        """Return a short unique suffix for asset names."""
        return uuid.uuid4().hex[:6]

    def setUp(self) -> None:
        log.info("Setting up Jiko Bridge integration test.")
        self.scene = C4DSceneHelper()
        self.scene.reset_scene()

        self.scene.ensure_loaded()
        self.asset_1 = AssetModel(
            database_name="test-local",
            pack_name="test",
            asset_name=f"test_{self.suffix}",
            files=[AssetFile(asset_type="model", bridge_type="model")],
        )
        self.collection_name_1 = f"Asset_{self.asset_1.pack_name}_{self.asset_1.asset_name}"

        self.asset_2 = AssetModel(
            database_name="test-local",
            pack_name="test",
            asset_name=f"test_{self.suffix}",
            files=[AssetFile(asset_type="model", bridge_type="model")],
        )
        self.collection_name_2 = f"Asset_{self.asset_2.pack_name}_{self.asset_2.asset_name}"

        self.asset_mat_1 = AssetModel(
            database_name="test-local",
            pack_name="test",
            asset_name="test_mat",
            files=[AssetFile(asset_type="basecolor", bridge_type="material")],
        )
        self.material_name_1 = f"{self.asset_mat_1.pack_name}__{self.asset_mat_1.asset_name}"

    def tearDown(self) -> None:
        try:
            path = self.scene.save_document("test_flows_teardown")

            if not path:
                log.error("Failed to save during tearDown.")
                return

            log.info("Saved for diagnostics: %s", path)
        except RuntimeError as exc:
            log.error("Failed to save tearDown: %s", exc)

    def export_flow(self, asset_model: AssetModel):
        """Exports a new asset."""
        api_module = self.scene.import_module("src.jb_api")
        self.assertIsNotNone(api_module)

        original_create_asset = api_module.JbAPI.create_asset
        asset_capture, injected_create_asset = make_injected_create_asset(
            asset_model, original_create_asset
        )

        with patch.object(
            api_module.JbAPI,
            "create_asset",
            autospec=True,
            side_effect=injected_create_asset,
        ):
            self.scene.call_command("export_asset")

        return asset_capture

    def update_flow(self, container):
        """Updates an existing asset."""

        self.scene.select_objects([container])

        exporter_module = self.scene.import_module("src.jb_asset_exporter")
        exporter = exporter_module.JbAssetExporter(self.scene.source)
        export_message = exporter.export_message()
        self.assertIn("update", export_message.lower(), "Export message should mention update")

        self.scene.call_command("export_asset")

    def import_active_asset(
        self,
        asset_model: AssetModel,
        count: int = 1,
    ):
        """Import active asset to the scene"""
        self.scene.clear_selection()

        api_module = self.scene.import_module("src.jb_api")

        def injected_active_asset(*_args, **_kwargs):
            api = api_module.JbAPI()
            return api.get_asset(asset_model)

        importer_module = self.scene.import_module("src.jb_asset_importer")
        importer = importer_module.JbAssetImporter(self.scene.source)
        import_message = importer.import_message()
        self.assertIn(
            "active asset",
            import_message.lower(),
            "Import message should mention active asset",
        )

        with patch.object(
            api_module.JbAPI,
            "get_active_asset",
            autospec=True,
            side_effect=injected_active_asset,
        ) as get_active_asset_patch:
            for _ in range(count):
                self.scene.call_command("import_asset")

        return get_active_asset_patch

    def reimport_flow(self, container):
        """Reimport asset container."""
        self.scene.select_objects([container])
        self.scene.call_command("import_asset")

    def instancing(self, asset_model: AssetModel, count: int = 5):
        """Create multiple instances of the active asset."""
        get_active_asset_patch = self.import_active_asset(asset_model=asset_model, count=count)

        instances = self.scene.get_instance_objects()
        self.assertEqual(
            len(instances),
            count,
            f"{count} instances should be created in the scene",
        )
        return instances, get_active_asset_patch

    def test_full_flow(self) -> None:
        """Test the flows of Jiko Bridge."""
        # Stage 1: Export new geometry asset
        parent = self.scene.create_scene_object("ExportParent")
        self.scene.create_scene_object("ExportChild", parent=parent)

        self.import_active_asset(asset_model=self.asset_mat_1)
        mat = self.scene.find_material_by_name(self.material_name_1)
        assert mat is not None, "Material should be imported successfully"

        self.scene.apply_material_to_object(parent, mat)

        self.scene.select_objects([parent])
        asset_capture = self.export_flow(self.asset_1)
        self.assertIn("asset", asset_capture)

        # Stage 2: Update existing asset with added geometry, using selected collection
        asset_container = self.scene.find_container_by_name(self.collection_name_1)
        assert asset_container is not None, "Exported asset collection should be found in the scene"

        self.scene.create_scene_object("UpdateChild", parent=parent)
        expected_hierarchy = self.scene.get_hierarchy(asset_container)

        self.update_flow(asset_container)

        # Stage 3: Reimport the updated collection asset
        self.reimport_flow(asset_container)

        imported_hierarchy = self.scene.get_hierarchy(asset_container)
        self.assertEqual(
            imported_hierarchy,
            expected_hierarchy,
        )

        # Stage 4: Create instances by importing active asset repeatedly
        instances, get_active_asset_patch = self.instancing(self.asset_1)
        self.assertEqual(get_active_asset_patch.call_count, 5)

        self.scene.select_objects(instances)
        assert (
            len(instances) == 5
        ), f"Instance count should be 5, current count: {len(instances)}"

        self.scene.save_document("test_full_flow_after_instances")

        # Stage 5: Export the selected instances as a new asset
        self.export_flow(self.asset_2)

        # Stage 6: Import in empty scene
        self.scene.reset_scene()

        self.assertIsNone(
            self.scene.find_container_by_name(self.collection_name_1),
            "Payload1 asset must not exist before payload2 import",
        )

        self.import_active_asset(asset_model=self.asset_2)

        self.assertIsNotNone(
            self.scene.find_container_by_name(self.collection_name_2),
            "Payload2 asset should be imported into the empty scene",
        )
        self.assertIsNotNone(
            self.scene.find_container_by_name(self.collection_name_1),
            "Linked payload1 asset should also be imported after payload2 import",
        )


if __name__ == "__main__":
    unittest.main(argv=["test_importer"], exit=True)
