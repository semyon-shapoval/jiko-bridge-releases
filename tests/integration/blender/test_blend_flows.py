import os
import sys
import uuid
import unittest
from typing import Optional
from unittest.mock import patch

import bpy

__package__ = "integration.blender"

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from ..helpers.api_helper import make_injected_active_asset, make_injected_create_asset
from ..helpers.logger import get_logger
from .scene_helper import BlenderSceneHelper

log = get_logger(__name__)

class TestBlenderJikoBridge(unittest.TestCase):
    @property
    def suffix(self) -> str:
        return uuid.uuid4().hex[:6]

    def setUp(self) -> None:
        log.info("Setting up Blender Jiko Bridge integration test.")
        self.scene = BlenderSceneHelper()
        self.scene.reset_scene()

        self.assertIn(self.scene.ADDON_NAME, bpy.context.preferences.addons)
        log.info("Addon '%s' is enabled in Blender preferences.", self.scene.ADDON_NAME)

        self.payload_1 = {
            "database_name": "test-local",
            "pack_name": "test",
            "asset_name": f"test_{self.suffix}",
            "asset_type": "model",
        }
        self.collection_name_1 = (
            f"Asset_{self.payload_1['pack_name']}_{self.payload_1['asset_name']}"
        )

        self.payload_2 = {
            "database_name": "test-local",
            "pack_name": "test",
            "asset_name": f"test_{self.suffix}",
            "asset_type": "model",
        }
        self.collection_name_2 = (
            f"Asset_{self.payload_2['pack_name']}_{self.payload_2['asset_name']}"
        )

    def export_new_flow(self, payload: dict[str, str], selected_objects=None):
        """Exports a new asset with the given payload and optional selected objects."""

        api_module = sys.modules.get("JikoBridgeBlend.jb_api")
        self.assertIsNotNone(api_module)

        original_create_asset = api_module.JB_API.create_asset
        payload_capture, injected_create_asset = make_injected_create_asset(
            payload, original_create_asset
        )

        if selected_objects is not None:
            self.scene.clear_selection()
            self.scene.select_objects(selected_objects)

        with patch.object(
            api_module.JB_API,
            "create_asset",
            autospec=True,
            side_effect=injected_create_asset,
        ):
            result = bpy.ops.jiko_bridge.asset_export()

        self.assertEqual(result, {"FINISHED"})
        return payload_capture

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
            result = bpy.ops.jiko_bridge.asset_export()

        self.assertEqual(result, {"FINISHED"})
        return expected_hierarchy

    def import_active_asset(
        self,
        payload: Optional[dict[str, str]] = None,
        count: int = 1,
    ):
        """Import active asset from payload one or more times."""
        self.scene.clear_selection()
        active_payload = payload or self.payload_1
        injected_active_asset = make_injected_active_asset(active_payload)

        api_module = sys.modules.get("JikoBridgeBlend.jb_api")
        self.assertIsNotNone(api_module)

        with patch.object(
            api_module.JB_API,
            "get_active_asset",
            autospec=True,
            side_effect=injected_active_asset,
        ) as get_active_asset_patch:
            result = None
            for _ in range(count):
                result = bpy.ops.jiko_bridge.asset_import()
                self.assertEqual(result, {"FINISHED"})

        return result, get_active_asset_patch

    def reimport_flow(self, asset_collection):
        """Reimport an asset collection or import active asset from payload."""
        active_layer_collection = self.scene.activate_collection(asset_collection.name)
        self.assertIsNotNone(active_layer_collection)

        result = bpy.ops.jiko_bridge.asset_import()
        self.assertEqual(result, {"FINISHED"})
        return result

    def instancing(self, payload: dict[str, str], count: int = 5):
        """Creates multiple instances of an asset by repeatedly importing the active asset."""

        result, get_active_asset_patch = self.import_active_asset(
            payload=payload, count=count
        )

        instances = self.scene.get_collection_instances()
        self.assertEqual(
            len(instances),
            count,
            f"{count} collection instances should be created in the scene",
        )
        return instances, get_active_asset_patch

    def test_full_flow(self) -> None:
        # Stage 1: Export new geometry asset
        parent = self.scene.create_scene_object("ExportParent")
        self.scene.create_scene_object("ExportChild", parent=parent)
        parent.select_set(True)

        log.info(
            "Starting export operator test with selected object '%s'.", parent.name
        )

        payload_capture = self.export_new_flow(self.payload_1)

        scene_collection = bpy.context.scene.collection
        self.assertFalse(
            scene_collection.objects,
            "Scene Collection should not have direct objects after export.",
        )

        # Stage 2: Update existing asset with added geometry, using selected collection
        asset_collection = bpy.data.collections.get(self.collection_name_1)
        self.assertIsNotNone(asset_collection)

        expected_hierarchy = self.update_flow(asset_collection, parent)
        self.assertIn("payload", payload_capture)

        # Stage 3: Reimport the updated collection asset
        self.reimport_flow(asset_collection)

        imported_hierarchy = self.scene.get_hierarchy(asset_collection)
        self.assertEqual(
            self.scene.normalize_hierarchy(imported_hierarchy),
            self.scene.normalize_hierarchy(expected_hierarchy),
        )

        # Stage 4: Create instances by importing active asset repeatedly
        instances, get_active_asset_patch = self.instancing(self.payload_1)
        self.assertEqual(get_active_asset_patch.call_count, 5)

        # Stage 5: Export the selected instances as a new asset
        self.export_new_flow(self.payload_2, selected_objects=instances)

        # Stage 6: Import in empty scene
        self.scene.reset_scene()

        self.assertIsNone(
            bpy.data.collections.get(self.collection_name_1),
            "Payload1 asset must not exist before payload2 import",
        )

        self.import_active_asset(payload=self.payload_2)

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
