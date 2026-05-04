"""
Blender scene helper utilities for integration tests.
Code by Semyon Shapoval, 2026
"""

import os
from typing import Optional

import addon_utils
import bpy


class BlenderSceneHelper:
    """Helper class for managing Blender scene state in integration tests."""

    ADDON_NAME = "jiko_bridge_blend"

    def update(self):
        """Force Blender to update the scene and view layer."""
        view_layer = bpy.context.view_layer
        if view_layer:
            view_layer.update()

    def create_scene_object(
        self, name: str, parent: Optional[bpy.types.Object] = None
    ) -> bpy.types.Object:
        """Create a new cube primitive in the scene with the given name and parent."""
        bpy.ops.object.select_all(action="DESELECT")

        existing_objects = set(bpy.data.objects)
        bpy.ops.mesh.primitive_cube_add(size=2.0, enter_editmode=False, align="WORLD")

        obj = next((o for o in bpy.data.objects if o not in existing_objects), None)
        if obj is None:
            obj = bpy.context.object
        if obj is None:
            raise RuntimeError("Failed to create cube primitive")

        obj.name = name

        if parent is not None:
            if parent.users_collection:
                for col in parent.users_collection:
                    if obj.name not in col.objects:
                        col.objects.link(obj)

            obj.parent = parent
            obj.parent_type = "OBJECT"
            obj.matrix_parent_inverse = parent.matrix_world.inverted()

        obj.select_set(True)
        self.update()

        return obj

    def find_layer_collection(self, layer_collection, name):
        """Recursively search layer_collection tree for a collection by name."""
        if layer_collection.collection.name == name:
            return layer_collection
        for child in layer_collection.children:
            found = self.find_layer_collection(child, name)
            if found:
                return found
        return None

    def select_collection(self, name):
        """Find and select a collection by name."""
        view_layer = bpy.context.view_layer
        if view_layer is None:
            return None

        layer_collection = self.find_layer_collection(
            view_layer.layer_collection,
            name,
        )
        if layer_collection is None:
            return None

        view_layer.active_layer_collection = layer_collection
        return layer_collection

    def clear_selection(self):
        """Deselect all objects, reset the active layer collection, and clear Outliner selection."""
        view_layer = bpy.context.view_layer
        if view_layer is None:
            return

        # Сначала сбрасываем через ops
        bpy.ops.object.select_all(action="DESELECT")

        # Потом явно обнуляем активный объект
        view_layer.objects.active = None

        # Сбрасываем active_layer_collection на корневую коллекцию
        view_layer.active_layer_collection = view_layer.layer_collection

        self.update()

    def ensure_addon_enabled(self, addon_name: str | None = None) -> None:
        """Enable a Blender addon by name and keep it loaded after reset."""
        addon_name = addon_name or self.ADDON_NAME
        enabled, _ = addon_utils.check(addon_name)
        if not enabled:
            addon_utils.enable(addon_name, default_set=True, persistent=True)

    def reset_scene(self, addon_name: str | None = None) -> None:
        """Reset Blender to a clean empty file for a fresh import test."""
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.ensure_addon_enabled(addon_name)
        self.update()

    def save_document(self, filename: str) -> str:
        """Save the current Blender file into the integration test logs directory."""
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(logs_dir, exist_ok=True)
        path = os.path.join(logs_dir, f"{filename}.blend")
        bpy.ops.wm.save_mainfile(filepath=path)
        return path

    def select_objects(self, objects: list[bpy.types.Object]) -> None:
        """Select all objects in the given list."""
        for obj in objects:
            obj.select_set(True)
        self.update()

    def get_hierarchy(self, collection: bpy.types.Collection):
        """Return a parent map for all direct objects inside a collection."""
        hierarchy = {}
        for obj in collection.objects:
            norm_name = obj.name.split(".", 1)[0]
            norm_parent = obj.parent.name.split(".", 1)[0] if obj.parent else None
            hierarchy[norm_name] = norm_parent

        return hierarchy

    def get_collection_instances(self) -> list[bpy.types.Object]:
        """Return all collection instance objects in the current Blender scene."""
        return [
            obj
            for obj in bpy.data.objects
            if obj.instance_type == "COLLECTION" and obj.instance_collection is not None
        ]
