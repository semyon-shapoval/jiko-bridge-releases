import addon_utils
import bpy

class BlenderSceneHelper:
    ADDON_NAME = "JikoBridgeBlend"

    def create_scene_object(
        self, name: str, parent: bpy.types.Object | None = None
    ) -> bpy.types.Object:
        bpy.ops.object.select_all(action="DESELECT")

        mesh = bpy.data.meshes.new(f"{name}Mesh")
        obj = bpy.data.objects.new(name, mesh)

        if parent is not None and parent.users_collection:
            for col in parent.users_collection:
                col.objects.link(obj)
        else:
            bpy.context.scene.collection.objects.link(obj)

        if parent is not None:
            obj.parent = parent
            obj.matrix_parent_inverse = obj.matrix_parent_inverse.copy()

        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.view_layer.update()

        return obj

    def find_layer_collection(self, layer_collection, name):
        if layer_collection.collection.name == name:
            return layer_collection
        for child in layer_collection.children:
            found = self.find_layer_collection(child, name)
            if found:
                return found
        return None

    def activate_collection(self, name):
        layer_collection = self.find_layer_collection(
            bpy.context.view_layer.layer_collection,
            name,
        )
        if layer_collection is not None:
            bpy.context.view_layer.active_layer_collection = layer_collection
        return layer_collection

    def clear_selection(self):
        bpy.context.view_layer.active_layer_collection = (
            bpy.context.view_layer.layer_collection
        )
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.update()

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
        bpy.context.view_layer.update()

    def select_objects(self, objects: list[bpy.types.Object]) -> None:
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.update()

    def get_hierarchy(self, collection: bpy.types.Collection):
        """Return a parent map for all direct objects inside a collection."""
        return {
            obj.name: obj.parent.name if obj.parent else None
            for obj in collection.objects
        }

    def normalize_hierarchy(
        self, hierarchy: dict[str, str | None]
    ) -> dict[str, str | None]:
        """Normalize object names by comparing base names before the first dot."""

        def normalize_name(name: str | None) -> str | None:
            if name is None:
                return None
            return name.split(".", 1)[0]

        return {
            normalize_name(name): normalize_name(parent)
            for name, parent in hierarchy.items()
        }

    def get_collection_instances(self) -> list[bpy.types.Object]:
        """Return all collection instance objects in the current Blender scene."""
        return [
            obj
            for obj in bpy.data.objects
            if obj.instance_type == "COLLECTION" and obj.instance_collection is not None
        ]
