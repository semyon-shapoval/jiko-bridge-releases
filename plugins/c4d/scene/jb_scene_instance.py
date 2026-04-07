from __future__ import annotations

import c4d

from jb_logger import get_logger

from jb_asset_model import AssetModel
from scene.jb_scene_select import JBSceneSelect

logger = get_logger(__name__)


class JBSceneInstance(JBSceneSelect):
    """Instance and placeholder management for Cinema 4D.

    Inherits selection helpers from JBSceneSelect and implements the
    instance / placeholder group of JBSceneBase.
    """

    # ------------------------------------------------------------------
    # Instance management
    # ------------------------------------------------------------------

    def has_instances(self, objects: list) -> bool:
        return any(o.CheckType(c4d.Oinstance) for o in objects)

    def create_instance(self, asset_container, name: str):
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = asset_container
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
        for key, bc in asset_container.GetUserDataContainer():
            self.set_user_data(instance, bc[c4d.DESC_NAME], asset_container[key])
        self.doc.InsertObject(instance)
        instance.SetBit(c4d.BIT_ACTIVE)
        return instance

    def set_instance_transform(self, instance, matrix) -> None:
        instance.SetMg(matrix)

    def add_instance_to_container(self, instance, container) -> None:
        instance.InsertUnder(container)

    # ------------------------------------------------------------------
    # Placeholder extraction
    # ------------------------------------------------------------------

    def extract_placeholders(self, container) -> list:
        result = []
        for obj in self.get_children(container):
            info = None
            for t in obj.GetTags():
                info = AssetModel.from_placeholder_name(t.GetName())
                if info:
                    break
            if not info:
                continue
            result.append(
                {
                    "pack_name": info["pack_name"],
                    "asset_name": info["asset_name"],
                    "matrix": obj.GetMg(),
                }
            )
            obj.Remove()
        return result

    # ------------------------------------------------------------------
    # Internal — placeholder creation / instance replacement
    # ------------------------------------------------------------------

    def _replace_instances_with_placeholders(self, root) -> None:
        if root is None:
            return
        for instance in self.get_children(root):
            if not instance.CheckType(c4d.Oinstance):
                continue
            info = AssetModel.from_c4d_object(instance)
            if not info or not info.pack_name or not info.asset_name:
                continue
            placeholder = self._create_placeholder(info.pack_name, info.asset_name)
            placeholder.SetMg(instance.GetMg())
            placeholder.InsertBefore(instance)
            instance.Remove()

    def _create_placeholder(self, pack_name: str, asset_name: str):
        obj = c4d.BaseObject(c4d.Oplane)
        obj.SetName(f"{pack_name}__{asset_name}")
        obj[c4d.PRIM_PLANE_WIDTH] = 100
        obj[c4d.PRIM_PLANE_HEIGHT] = 100
        obj[c4d.PRIM_PLANE_SUBW] = 1
        obj[c4d.PRIM_PLANE_SUBH] = 1
        tag = obj.MakeTag(c4d.Tpolygonselection)
        tag.SetName(f"{pack_name}__{asset_name}")
        tag.GetBaseSelect().SelectAll(1)
        return obj
