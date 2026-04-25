import os
import sys
import c4d
import uuid
import unittest
from typing import Optional
from unittest.mock import patch

__package__ = "integration.c4d"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ..helpers.logger import get_logger
from .scene_helper import C4DSceneHelper
from ..helpers.api_helper import make_injected_active_asset, make_injected_create_asset
from ..helpers.asset_helper import create_dummy_texture, create_material_direct

log = get_logger(__name__)


class TestC4DJikoBridge(unittest.TestCase):
    JIKO_BRIDGE_ID = 1096086

    @property
    def suffix(self) -> str:
        return uuid.uuid4().hex[:6]

    def setUp(self) -> None:
        log.info("Setting up C4D Jiko Bridge integration test.")
        self.scene = C4DSceneHelper()
        self.scene.reset_scene()
        self.commands = self._get_loaded_commands()

        self.payload_1 = {
            "databaseName": "test-local",
            "packName": "test",
            "assetName": f"test_{self.suffix}",
            "files": [{"assetType": "model"}],
        }
        self.collection_name_1 = (
            f"Asset_{self.payload_1['packName']}_{self.payload_1['assetName']}"
        )

        self.payload_2 = {
            "databaseName": "test-local",
            "packName": "test",
            "assetName": f"test_{self.suffix}",
            "files": [{"assetType": "model"}],
        }
        self.collection_name_2 = (
            f"Asset_{self.payload_2['packName']}_{self.payload_2['assetName']}"
        )

        self.payload_3 = {
            "databaseName": "test-local",
            "packName": "test",
            "assetName": f"test_{self.suffix}",
            "files": [{"assetType": "basecolor"}],
        }

    def _assert_plugin_loaded(self) -> None:
        plugin = c4d.plugins.FindPlugin(self.JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND)
        self.assertIsNotNone(
            plugin,
            "Jiko Bridge command plugin is not loaded in C4D. Ensure the C4D plugin is loaded before running the integration test.",
        )
        self.assertIsNotNone(
            sys.modules.get("jb_commands"),
            "Plugin module 'jb_commands' is not loaded by C4D.",
        )
        self.assertIsNotNone(
            sys.modules.get("jb_api"),
            "Plugin module 'jb_api' is not loaded by C4D.",
        )

    def _get_loaded_commands(self):
        self._assert_plugin_loaded()
        jb_commands = sys.modules.get("jb_commands")
        self.assertIsNotNone(jb_commands)
        return jb_commands.JB_Commands(c4d.documents.GetActiveDocument())

    def tearDown(self) -> None:
        try:
            path = self.scene.save_document(f"test_c4d_flows_teardown")

            if not path:
                log.error("Failed to save C4D document during tearDown.")
                return

            os.startfile(path)
            log.info("Saved C4D document for diagnostics: %s", path)
        except Exception as save_exc:
            log.error("Failed to save C4D document during tearDown: %s", save_exc)

    def export_new_flow(self, payload: dict[str, str], selected_objects=None):
        api_module = sys.modules.get("jb_api")
        self.assertIsNotNone(api_module)

        asset_export_api = self.commands._commands.asset_export.api
        original_create_asset = asset_export_api.create_asset
        payload_capture, injected_create_asset = make_injected_create_asset(
            payload, original_create_asset
        )

        log.info("Exporting new asset with payload: %s", payload)

        if selected_objects is not None:
            self.scene.clear_selection()
            self.scene.select_objects(selected_objects)

        with patch.object(
            asset_export_api,
            "create_asset",
            side_effect=injected_create_asset,
        ):
            self.commands.export_asset()

        return payload_capture

    def update_flow(self, asset_container, parent):
        self.scene.create_scene_object("UpdateChild", parent=parent)
        expected_hierarchy = self.scene.get_hierarchy(asset_container)

        self.scene.clear_selection()
        self.scene.activate_object(asset_container)

        asset_export_api = self.commands._commands.asset_export.api
        self.assertIsNotNone(asset_export_api)

        with patch.object(
            asset_export_api,
            "update_asset",
            autospec=True,
            return_value={"success": True},
        ) as update_asset_patch:
            self.commands.export_asset()

        self.assertTrue(update_asset_patch.called)
        return expected_hierarchy

    def import_active_asset(
        self,
        payload: Optional[dict[str, str]] = None,
        count: int = 1,
    ):
        self.scene.clear_selection()

        active_payload = payload or self.payload_1
        injected_active_asset = make_injected_active_asset(active_payload)

        asset_import_api = self.commands._commands.asset_import.api
        self.assertIsNotNone(asset_import_api)

        with patch.object(
            asset_import_api,
            "get_active_asset",
            side_effect=injected_active_asset,
        ) as get_active_asset_patch:
            result = None
            for _ in range(count):
                self.commands.import_asset()
                result = True

        return result, get_active_asset_patch

    def reimport_flow(self, asset_container):
        self.scene.clear_selection()
        self.scene.activate_object(asset_container)
        self.commands.import_asset()

    def instancing(self, payload: dict[str, str], count: int = 5):
        result, get_active_asset_patch = self.import_active_asset(
            payload=payload, count=count
        )

        instances = self.scene.get_instance_objects()
        self.assertEqual(
            len(instances),
            count,
            f"{count} instance objects should be created in the scene",
        )
        return instances, get_active_asset_patch

    def test_full_flow(self) -> None:
        parent = self.scene.create_scene_object("ExportParent")
        self.scene.create_scene_object("ExportChild", parent=parent)
        self.scene.activate_object(parent)

        payload_capture = self.export_new_flow(self.payload_1)

        asset_container = self.scene.find_object_by_name(self.collection_name_1)
        self.assertIsNotNone(asset_container)
        self.assertIn("payload", payload_capture)

        expected_hierarchy = self.update_flow(asset_container, parent)
        self.reimport_flow(asset_container)

        imported_hierarchy = self.scene.get_hierarchy(asset_container)
        self.assertEqual(
            self.scene.normalize_hierarchy(imported_hierarchy),
            self.scene.normalize_hierarchy(expected_hierarchy),
        )

        instances, get_active_asset_patch = self.instancing(self.payload_1)
        self.assertEqual(get_active_asset_patch.call_count, 5)

        self.export_new_flow(self.payload_2, selected_objects=instances)

        self.scene.save_document(f"test_c4d_flows_before_reset")

        self.scene.reset_scene()

        self.assertIsNone(
            self.scene.find_object_by_name(self.collection_name_1),
            "Payload1 asset must not exist before payload2 import",
        )

        self.import_active_asset(payload=self.payload_2)

        self.assertIsNotNone(
            self.scene.find_object_by_name(self.collection_name_2),
            "Payload2 asset should be imported into the empty scene",
        )
        self.assertIsNotNone(
            self.scene.find_object_by_name(self.collection_name_1),
            "Linked payload1 asset should also be imported after payload2 import",
        )

        # Material import flow
        texture_path = create_dummy_texture(f"dummy_{self.payload_3['assetName']}.png")
        self.assertTrue(os.path.exists(texture_path), "Dummy texture file must exist")

        asset = create_material_direct(self.payload_3, texture_path)
        self.assertIsNotNone(asset, "Asset should be created in Jiko Bridge")

        material = self.import_material_asset(self.payload_3)
        self.assertIsNotNone(
            material,
            f"Material '{self.payload_3['assetName']}' should exist after import",
        )

        mesh = self.scene.create_scene_object("MaterialTestMesh")
        tag = self.scene.apply_material_to_object(mesh, material)
        self.assertIsNotNone(tag, "Texture tag should be created on the mesh")

        material = self.reimport_material_asset(self.payload_3)
        self.assertIsNotNone(material, "Material must still exist after reimport")

        texture_result = self.scene.get_material_texture_path(material)
        self.assertIsNotNone(
            texture_result,
            "Material color channel should have a bitmap shader after reimport",
        )
        self.assertTrue(
            texture_result, "Bitmap shader filename must not be empty after reimport"
        )
        log.info("Texture path after reimport: %s", texture_result)

    def import_material_asset(self, payload: dict):
        asset_import_api = self.commands._commands.asset_import.api
        with patch.object(
            asset_import_api,
            "get_active_asset",
            side_effect=make_injected_active_asset(payload),
        ):
            self.commands.import_asset()
        material = self.scene.find_material_by_name(payload["assetName"])
        log.info("Material imported: %s", material.GetName() if material else None)
        return material


if __name__ == "__main__":
    unittest.main(argv=["test_c4d_importer"], exit=True)
