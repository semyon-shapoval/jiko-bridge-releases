"""
Integration tests for Blender Jiko Bridge addon
Code by Semyon Shapoval, 2026
"""

import importlib
import os
import sys
import uuid
import unittest
from unittest.mock import patch

import bpy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# pylint: disable=wrong-import-position
from tests.integration.helpers.api_helper import (
    make_injected_active_asset,
    make_injected_create_asset,
)
from tests.integration.helpers.logger import get_logger
from tests.integration.blender.scene_helper import BlenderSceneHelper
from plugins.blender.addons.jiko_bridge_blend.src.jb_types import AssetModel, AssetFile

log = get_logger(__name__)


class TestBlenderJikoBridge(unittest.TestCase):
    """Integration tests for Blender Jiko Bridge addon."""

    @property
    def suffix(self) -> str:
        """Return a short unique suffix for asset names."""
        return uuid.uuid4().hex[:6]

    def _call_jiko_command(self, operator: str):
        jiko_ops = getattr(bpy.ops, "jiko_bridge", None)
        self.assertIsNotNone(jiko_ops, "jiko_bridge operator should be registered in bpy.ops")
        result = getattr(jiko_ops, operator)()
        self.assertEqual(result, {"FINISHED"}, f"Operator {operator} should finish successfully.")
        return result

    def setUp(self) -> None:
        log.info("Setting up Blender Jiko Bridge integration test.")
        self.scene = BlenderSceneHelper()
        self.scene.reset_scene()

        prefs = bpy.context.preferences
        addons = prefs.addons if prefs else []
        self.assertIn(self.scene.ADDON_NAME, addons)

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

    def export_new_flow(self, asset_model: AssetModel, selected_objects=None):
        """Exports a new asset with the given AssetModel and optional selected objects."""

        api_module = importlib.import_module("jiko_bridge_blend.src.jb_api")

        original_create_asset = api_module.JbAPI.create_asset
        asset_capture, injected_create_asset = make_injected_create_asset(
            asset_model, original_create_asset
        )

        if selected_objects is not None:
            self.scene.clear_selection()
            self.scene.select_objects(selected_objects)

        with patch.object(
            api_module.JbAPI,
            "create_asset",
            autospec=True,
            side_effect=injected_create_asset,
        ):
            result = self._call_jiko_command("asset_export")

        self.assertEqual(result, {"FINISHED"})
        return asset_capture

    def update_flow(self, asset_collection, parent):
        """Updates an existing asset with new geometry."""

        self.scene.create_scene_object("UpdateChild", parent=parent)
        expected_hierarchy = self.scene.get_hierarchy(asset_collection)

        window = bpy.context.window_manager.windows[0]
        screen = window.screen
        area = next((a for a in screen.areas if a.type == "VIEW_3D"), screen.areas[0])
        region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])

        self.scene.clear_selection()
        active_layer_collection = self.scene.activate_collection(asset_collection.name)
        self.assertIsNotNone(active_layer_collection)

        with bpy.context.temp_override(window=window, area=area, region=region):
            result = self._call_jiko_command("asset_export")

        self.assertEqual(result, {"FINISHED"})
        return expected_hierarchy

    def import_active_asset(
        self,
        asset_model: AssetModel,
        count: int = 1,
    ):
        """Import active asset from AssetModel one or more times."""
        self.scene.clear_selection()
        active_asset = asset_model
        injected_active_asset = make_injected_active_asset(active_asset)

        api_module = importlib.import_module("jiko_bridge_blend.src.jb_api")

        with patch.object(
            api_module.JbAPI,
            "get_active_asset",
            autospec=True,
            side_effect=injected_active_asset,
        ) as get_active_asset_patch:
            result = None
            for _ in range(count):
                result = self._call_jiko_command("asset_import")
                self.assertEqual(result, {"FINISHED"})

        return result, get_active_asset_patch

    def reimport_flow(self, asset_collection):
        """Reimport an asset collection or import active asset from AssetModel."""
        active_layer_collection = self.scene.activate_collection(asset_collection.name)
        self.assertIsNotNone(active_layer_collection)

        result = self._call_jiko_command("asset_import")
        self.assertEqual(result, {"FINISHED"})
        return result

    def instancing(self, asset_model: AssetModel, count: int = 5):
        """Creates multiple instances of an asset by repeatedly importing the active asset."""

        _, get_active_asset_patch = self.import_active_asset(asset_model=asset_model, count=count)

        instances = self.scene.get_collection_instances()
        self.assertEqual(
            len(instances),
            count,
            f"{count} collection instances should be created in the scene",
        )
        return instances, get_active_asset_patch

    def test_full_flow(self) -> None:
        """Test the complete Jiko Bridge asset lifecycle in Blender."""
        # Stage 1: Export new geometry asset
        parent = self.scene.create_scene_object("ExportParent")
        self.scene.create_scene_object("ExportChild", parent=parent)
        parent.select_set(True)

        log.info("Starting export operator test with selected object '%s'.", parent.name)

        asset_capture = self.export_new_flow(self.asset_1)
        scene = bpy.context.scene
        scene_collection = scene.collection if scene else None
        self.assertFalse(
            scene_collection.objects if scene_collection else [],
            "Scene Collection should not have direct objects after export.",
        )

        # Stage 2: Update existing asset with added geometry, using selected collection
        asset_collection = bpy.data.collections.get(self.collection_name_1)
        self.assertIsNotNone(asset_collection)

        expected_hierarchy = self.update_flow(asset_collection, parent)
        self.assertIn("asset", asset_capture)

        # Stage 3: Reimport the updated collection asset
        self.reimport_flow(asset_collection)

        imported_hierarchy = self.scene.get_hierarchy(asset_collection)
        self.assertEqual(
            imported_hierarchy,
            expected_hierarchy,
        )

        # Stage 4: Create instances by importing active asset repeatedly
        instances, get_active_asset_patch = self.instancing(self.asset_1)
        self.assertEqual(get_active_asset_patch.call_count, 5)

        # Stage 5: Export the selected instances as a new asset
        self.export_new_flow(self.asset_2, selected_objects=instances)

        # Stage 6: Import in empty scene
        self.scene.reset_scene()

        self.assertIsNone(
            bpy.data.collections.get(self.collection_name_1),
            "Payload1 asset must not exist before payload2 import",
        )

        self.import_active_asset(asset_model=self.asset_2)
        saved_path = self.scene.save_document("test_blend_flows_end")
        self.assertTrue(
            os.path.exists(saved_path),
            f"Saved blend file should exist at {saved_path}",
        )

        self.assertIsNotNone(
            bpy.data.collections.get(self.collection_name_2),
            "Payload2 asset should be imported into the empty scene",
        )
        self.assertIsNotNone(
            bpy.data.collections.get(self.collection_name_1),
            "Linked payload1 asset should also be imported after payload2 import",
        )


if __name__ == "__main__":
    unittest.main(argv=["test_blend_importer"], exit=True)
