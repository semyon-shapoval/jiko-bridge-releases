import bpy
from typing import Optional

from ..jb_asset_model import AssetModel
from ..jb_logger import get_logger
from .jb_scene_tree import JBTree

logger = get_logger(__name__)


class JBSceneSelect(JBTree):
    """Selection helpers for Blender.

    Inherits tree traversal from JBTree and implements the selection
    group of JBSceneBase.
    """

    def get_selection(self) -> list:
        """Return the currently selected objects."""
        return list(bpy.context.selected_objects)

    def get_selected_asset_containers(self) -> list:
        """Return asset collections from selected instance Empties + active collection."""
        selected_empties = [
            obj
            for obj in bpy.context.selected_objects
            if obj.instance_type == "COLLECTION" and obj.instance_collection
        ]
        containers = [
            obj.instance_collection
            for obj in selected_empties
            if AssetModel.from_collection(obj.instance_collection)
        ]
        active = self.get_active_asset_container()
        if active and active not in containers:
            containers.append(active)
        return containers

    def get_selected_asset_container(self) -> Optional[bpy.types.Collection]:
        """Return the single unambiguous asset container, or None."""
        active = self.get_active_asset_container()
        if active:
            return active
        instance_collections = [
            obj.instance_collection
            for obj in bpy.context.selected_objects
            if obj.instance_type == "COLLECTION"
            and obj.instance_collection
            and AssetModel.from_collection(obj.instance_collection)
        ]
        return instance_collections[0] if len(instance_collections) == 1 else None

    def get_active_asset_container(self) -> Optional[bpy.types.Collection]:
        """Return the active layer collection if it is an asset, else None."""
        try:
            layer_collection = bpy.context.view_layer.active_layer_collection
        except Exception:
            return None
        col = getattr(layer_collection, "collection", None)
        return col if col and AssetModel.from_collection(col) else None

    def confirm(self, message: str) -> bool:
        """Always returns True until a Blender dialog is implemented.

        TODO: implement a proper Blender invoke()/popup dialog.
        """
        return True
