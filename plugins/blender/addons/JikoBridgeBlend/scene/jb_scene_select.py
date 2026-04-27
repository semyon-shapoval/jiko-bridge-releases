import bpy
from typing import Optional

from ..src.jb_asset_model import AssetModel
from ..src.jb_logger import get_logger
from .jb_scene_tree import JBSceneTree

logger = get_logger(__name__)


class JBSceneSelect(JBSceneTree):
    """Selection helpers for Blender.

    Inherits tree traversal from JBSceneTree and implements the selection
    group of JBSceneBase.
    """

    def _get_context(self, context=None):
        if context is not None:
            return context
        return bpy.context

    def _get_selected_objects(self, ctx) -> list:
        if hasattr(ctx, "selected_objects"):
            return list(ctx.selected_objects)
        return list(bpy.context.view_layer.objects.selected)

    def _expand_selection(
        self, objects: list[bpy.types.Object]
    ) -> list[bpy.types.Object]:
        """Return selected objects plus all child objects recursively."""
        expanded: list[bpy.types.Object] = []
        seen = set()

        def add_tree(obj: bpy.types.Object) -> None:
            if obj in seen:
                return
            seen.add(obj)
            expanded.append(obj)
            for child in obj.children:
                add_tree(child)

        for obj in objects:
            add_tree(obj)

        return expanded

    def get_selected_objects(self, context=None, child: bool = False) -> list:
        """Return the currently selected objects."""
        ctx = self._get_context(context)
        objects = self._get_selected_objects(ctx)
        if child:
            objects = self._expand_selection(objects)

        return objects
    
    def get_material_from_selected_objects(self, context=None) -> list:
        """Return materials from selected objects."""
        ctx = self._get_context(context)
        objects = self._get_selected_objects(ctx)
        return self.get_selected_materials(ctx, objects)

    def get_selected_materials(self, context=None, objects=None) -> list:
        """Return materials from selected objects and material slots."""
        ctx = self._get_context(context)
        if objects is None:
            objects = self.get_selected_objects(ctx)
        materials = set()
        for obj in objects:
            if hasattr(obj.data, "materials"):
                for mat in obj.data.materials:
                    if mat is not None:
                        materials.add(mat)
        if hasattr(ctx, "selected_materials"):
            for mat in ctx.selected_materials:
                if mat is not None:
                    materials.add(mat)
        return list(materials)

    def get_selected_asset_containers(self, context=None) -> list:
        """Return asset collections from selected instance Empties + active collection."""
        ctx = self._get_context(context)
        selected_empties = [
            obj
            for obj in self._get_selected_objects(ctx)
            if obj.instance_type == "COLLECTION" and obj.instance_collection
        ]
        containers = [
            obj.instance_collection
            for obj in selected_empties
            if AssetModel.from_collection(obj.instance_collection)
        ]
        active = self.get_active_asset_container(context)
        if active and active not in containers:
            containers.append(active)
        return containers

    def get_selected_asset_container(
        self, context=None
    ) -> Optional[bpy.types.Collection]:
        """Return the single unambiguous asset container, or None."""
        active = self.get_active_asset_container(context)
        if active:
            return active
        ctx = self._get_context(context)
        instance_collections = [
            obj.instance_collection
            for obj in self._get_selected_objects(ctx)
            if obj.instance_type == "COLLECTION"
            and obj.instance_collection
            and AssetModel.from_collection(obj.instance_collection)
        ]
        return instance_collections[0] if len(instance_collections) == 1 else None

    def get_active_asset_container(
        self, context=None
    ) -> Optional[bpy.types.Collection]:
        """Return the active layer collection if it is an asset, else None."""
        ctx = self._get_context(context)
        try:
            view_layer = ctx.view_layer
            layer_collection = view_layer.active_layer_collection
        except Exception:
            return None
        col = layer_collection.collection
        return col if col and AssetModel.from_collection(col) else None

    def confirm(self, message: str) -> bool:
        """Always returns True until a Blender dialog is implemented.

        TODO: implement a proper Blender invoke()/popup dialog.
        """
        return True
