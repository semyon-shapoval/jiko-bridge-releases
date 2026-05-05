"""
Blender scene helper utilities for integration tests.
Code by Semyon Shapoval, 2026
"""

import os
import importlib
from typing import Optional

import addon_utils
import bpy


class BlenderSceneHelper:
    """Helper class for managing Blender scene state in integration tests."""

    ADDON_NAME = "jiko_bridge_blend"

    def __init__(self):
        self.souce = bpy.context

    @property
    def source(self) -> bpy.types.Context:
        """Return the current Blender context."""
        return self.souce

    def import_module(self, module_name: str):
        """Import a module from the Jiko Bridge addon."""
        full_name = f"{self.ADDON_NAME}.{module_name}"
        return importlib.import_module(full_name)

    def call_command(self, operator: str):
        """Call command"""
        jiko_ops = getattr(bpy.ops, "jiko_bridge", None)
        if jiko_ops is None:
            raise RuntimeError("jiko_bridge operator should be registered in bpy.ops")
        result = getattr(jiko_ops, operator)()
        if result != {"FINISHED"}:
            raise RuntimeError(f"Operator {operator} should finish successfully.")

    @property
    def _view_layer(self) -> bpy.types.ViewLayer:
        """Return the active view layer, or None if not available."""
        view_layer = self.souce.view_layer
        if view_layer is None:
            raise RuntimeError("No active view layer found in the current Blender context.")
        return view_layer

    def _find_layer_collection(self, layer_collection, name):
        """Recursively search layer_collection tree for a collection by name."""
        if layer_collection.collection.name == name:
            return layer_collection
        for child in layer_collection.children:
            found = self._find_layer_collection(child, name)
            if found:
                return found
        return None

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

    def find_material_by_name(self, name) -> Optional[bpy.types.Material]:
        """Find a material in the current Blender file by name."""
        return bpy.data.materials.get(name)

    def find_container_by_name(self, name) -> Optional[bpy.types.Collection]:
        """Find a collection in the current Blender file by name."""
        return bpy.data.collections.get(name)

    def clear_selection(self):
        """Deselect all objects, reset the active layer collection, and clear Outliner selection."""
        # Сначала сбрасываем через ops
        bpy.ops.object.select_all(action="DESELECT")

        # Потом явно обнуляем активный объект
        self._view_layer.objects.active = None

        # Сбрасываем active_layer_collection на корневую коллекцию
        self._view_layer.active_layer_collection = self._view_layer.layer_collection

        self.update()

    def ensure_loaded(self, addon_name: str | None = None) -> None:
        """Enable a Blender addon by name and keep it loaded after reset."""
        addon_name = addon_name or self.ADDON_NAME
        enabled, _ = addon_utils.check(addon_name)
        if not enabled:
            addon_utils.enable(addon_name, default_set=True, persistent=True)

    def reset_scene(self, addon_name: str | None = None) -> None:
        """Reset Blender to a clean empty file for a fresh import test."""
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.ensure_loaded(addon_name)
        self.update()

    def save_document(self, filename: str) -> str:
        """Save the current Blender file into the integration test logs directory."""
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(logs_dir, exist_ok=True)
        path = os.path.join(logs_dir, f"{filename}.blend")
        bpy.ops.wm.save_mainfile(filepath=path)
        return path

    def select_objects(self, objects: list[bpy.types.Object | bpy.types.Collection]):
        """Select all objects in the given list."""
        self.clear_selection()

        for obj in objects:
            if isinstance(obj, bpy.types.Object):
                obj.select_set(True)
            if isinstance(obj, bpy.types.Collection):
                layer_collection = self._find_layer_collection(
                    self._view_layer.layer_collection,
                    obj.name,
                )

                self._view_layer.active_layer_collection = layer_collection

        self.update()

    def apply_material_to_object(self, obj: bpy.types.Object, mat: bpy.types.Material) -> bool:
        """Apply the given material to the given object if it's a mesh."""
        if isinstance(obj.data, bpy.types.Mesh):
            obj.data.materials.append(mat)
            return True
        return False

    def get_hierarchy(self, collection: bpy.types.Collection):
        """Return a parent map for all direct objects inside a collection."""
        hierarchy = {}
        for obj in collection.objects:
            norm_name = obj.name.split(".", 1)[0]
            norm_parent = obj.parent.name.split(".", 1)[0] if obj.parent else None
            hierarchy[norm_name] = norm_parent

        return hierarchy

    def get_instance_objects(self) -> list[bpy.types.Object]:
        """Return all collection instance objects in the current Blender scene."""
        return [
            obj
            for obj in bpy.data.objects
            if obj.instance_type == "COLLECTION" and obj.instance_collection is not None
        ]
