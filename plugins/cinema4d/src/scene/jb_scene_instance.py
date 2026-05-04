"""
Instance and placeholder management for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import c4d

from src.scene.jb_scene_container import JbSceneContainer
from src.jb_types import AssetModel, JbObject


class JbSceneInstance(JbSceneContainer):
    """Instance and placeholder management for Cinema 4D."""

    def create_instance(self, container, name):
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = container
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
        for key, bc in container.GetUserDataContainer():
            self._set_user_data(instance, bc[c4d.DESC_NAME], container[key])
        self.source.InsertObject(instance)
        instance.SetBit(c4d.BIT_ACTIVE)
        return instance

    def get_asset_from_placeholder(self, obj) -> Optional[AssetModel]:
        if not obj.IsInstanceOf(c4d.Opolygon):
            return None
        if obj.GetPointCount() != 4:
            return None

        asset_model = None
        for tag in obj.GetTags():
            if tag.CheckType(c4d.Ttexture):
                material = tag[c4d.TEXTURETAG_MATERIAL] if tag.GetType() == c4d.Ttexture else None
                if material:
                    asset_model = AssetModel.from_string(material.GetName())
                    if asset_model:
                        break

        if not asset_model:
            return None

        return asset_model

    def replace_instances_with_placeholders(self, objects, source) -> list[JbObject]:
        if not objects:
            return []

        new_objects = []

        for obj in objects:
            if not obj.CheckType(c4d.Oinstance):
                continue
            info = self.get_asset_data_from_container(obj)
            if not info:
                continue
            placeholder = self.create_placeholder(
                info,
                obj.GetMg(),
                source,
            )
            placeholder.InsertBefore(obj)
            obj.Remove()
            new_objects.append(placeholder)

        return new_objects

    def create_placeholder(self, asset_model, transform, source) -> JbObject:
        pack_name = asset_model.pack_name
        asset_name = asset_model.asset_name

        material = c4d.BaseMaterial()
        material.SetName(f"{pack_name}__{asset_name}")

        source.InsertMaterial(material)

        obj = c4d.BaseObject(c4d.Oplane)

        obj.SetMg(transform)

        obj.SetName(f"{pack_name}__{asset_name}")
        obj[c4d.PRIM_PLANE_WIDTH] = 100
        obj[c4d.PRIM_PLANE_HEIGHT] = 100
        obj[c4d.PRIM_PLANE_SUBW] = 1
        obj[c4d.PRIM_PLANE_SUBH] = 1

        tag = obj.MakeTag(c4d.Ttexture)
        if tag is not None:
            try:
                tag[c4d.TEXTURETAG_MATERIAL] = material
            except (TypeError, AttributeError):
                if hasattr(tag, "SetMaterial"):
                    tag.SetMaterial(material)
        return obj
