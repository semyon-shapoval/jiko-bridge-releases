"""
Base integration test flows for Jiko Bridge.
Code by Semyon Shapoval, 2026
"""

import os
import sys
import uuid
import unittest
import importlib.util
from typing import Any
from unittest.mock import patch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, root_dir)

# pylint: disable=wrong-import-position disable=import-error

from tests.integration.scene.base_scene import BaseScene
from tests.integration.utils import get_logger, make_injected_create_asset

if importlib.util.find_spec("c4d") is not None:
    from tests.integration.scene.c4d_scene import Scene
elif importlib.util.find_spec("bpy") is not None:
    from tests.integration.scene.blend_scene import Scene  # type: ignore[assignment]
else:
    raise ImportError("Environment not supported.")


if importlib.util.find_spec("c4d") is not None:
    from plugins.cinema4d.src.jb_types import AssetModel, AssetFile
elif importlib.util.find_spec("bpy") is not None:
    from plugins.blender.addons.jiko_bridge_blend.src.jb_types import (  # type: ignore[assignment]
        AssetModel,
        AssetFile,
    )
else:
    raise ImportError("Environment not supported.")

log = get_logger(__name__)


class BaseJikoBridgeTests(unittest.TestCase):
    """Abstract base class with all shared Jiko Bridge test flows."""

    @property
    def suffix(self) -> str:
        """Unique suffix for asset names."""
        return uuid.uuid4().hex[:6]

    def _make_scene(self) -> BaseScene:
        """Return a configured scene helper instance."""
        return Scene()

    def setUp(self) -> None:
        log.info("Setting up Jiko Bridge integration test.")
        self.scene = self._make_scene()
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

    def export_flow(self, asset_model: Any) -> Any:
        """Export new asset."""
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

    def update_flow(self, container: Any) -> None:
        """Update existing asset."""
        self.scene.select_objects([container])

        exporter_module = self.scene.import_module("src.jb_asset_exporter")
        exporter = exporter_module.JbAssetExporter(self.scene.source)
        export_message = exporter.export_message()
        self.assertIn("update", export_message.lower())

        self.scene.call_command("export_asset")

    def import_active_asset(self, asset_model: Any, count: int = 1):
        """Import active asset"""
        self.scene.clear_selection()

        api_module = self.scene.import_module("src.jb_api")

        def injected_active_asset(*_args: Any, **_kwargs: Any) -> Any:
            return api_module.JbAPI().get_asset(asset_model)

        importer_module = self.scene.import_module("src.jb_asset_importer")
        importer = importer_module.JbAssetImporter(self.scene.source)
        import_message = importer.import_message()
        self.assertIn("active asset", import_message.lower())

        with patch.object(
            api_module.JbAPI,
            "get_active_asset",
            autospec=True,
            side_effect=injected_active_asset,
        ) as patch_obj:
            for _ in range(count):
                self.scene.call_command("import_asset")

        return patch_obj

    def reimport_flow(self, container: Any) -> None:
        """Reimport asset."""
        self.scene.select_objects([container])
        self.scene.call_command("import_asset")

    def instancing(self, asset_model: Any, count: int = 5):
        """Instance by importing the same asset multiple times."""
        patch_obj = self.import_active_asset(asset_model=asset_model, count=count)
        instances = self.scene.get_instance_objects()
        self.assertEqual(len(instances), count)
        return instances, patch_obj

    def test_full_flow(self) -> None:
        """Test the full flow of Jiko Bridge"""
        parent = self.scene.create_scene_object("ExportParent")
        self.scene.create_scene_object("ExportChild", parent=parent)

        self.scene.create_scene_material(self.material_name_1)

        self.import_active_asset(asset_model=self.asset_mat_1)
        mat = self.scene.find_material_by_name(self.material_name_1)
        assert mat is not None, "Material should be imported successfully"


        materials = self.scene.get_all_materials()
        assert (
            len(materials) == 1
        ), f"Active import should remove duplicates material ({len(materials)} found)"

        self.scene.apply_material_to_object(parent, mat)
        self.scene.select_objects([parent])
        asset_capture = self.export_flow(self.asset_1)
        self.assertIn("asset", asset_capture)

        asset_container = self.scene.find_container_by_name(self.collection_name_1)
        assert asset_container is not None, "Exported asset container should be found in the scene"

        self.scene.create_scene_object("UpdateChild", parent=parent)
        expected_hierarchy = self.scene.get_hierarchy(asset_container)

        self.update_flow(asset_container)
        self.reimport_flow(asset_container)
        self.assertEqual(self.scene.get_hierarchy(asset_container), expected_hierarchy)

        instances, patch_obj = self.instancing(self.asset_1)
        self.assertEqual(patch_obj.call_count, 5)

        self.scene.select_objects(instances)
        self.export_flow(self.asset_2)

        self.scene.reset_scene()
        self.assertIsNone(self.scene.find_container_by_name(self.collection_name_1))
        self.import_active_asset(asset_model=self.asset_2)
        self.assertIsNotNone(self.scene.find_container_by_name(self.collection_name_2))
        self.assertIsNotNone(self.scene.find_container_by_name(self.collection_name_1))


if __name__ == "__main__":
    unittest.main(argv=["tests_flows"], exit=True)
