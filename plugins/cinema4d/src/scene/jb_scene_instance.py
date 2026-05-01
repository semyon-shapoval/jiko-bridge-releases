"""
Instance and placeholder management for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

import c4d

from src.scene.jb_scene_container import JbSceneContainer
from src.jb_types import AssetInfo, JbObject
from src.jb_protocols import JbPlaceholderInfo


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

    def extract_placeholders(self, container) -> list[JbPlaceholderInfo]:
        result = []
        for obj in self.get_objects(container, "children"):
            if not obj.IsInstanceOf(c4d.Opolygon):
                continue
            if obj.GetPointCount() != 4:
                continue

            info = None
            for tag in obj.GetTags():
                if tag.CheckType(c4d.Ttexture):
                    material = (
                        tag[c4d.TEXTURETAG_MATERIAL] if tag.GetType() == c4d.Ttexture else None
                    )
                    if material:
                        info = AssetInfo.from_string(material.GetName())
                        if info:
                            break
            if not info:
                continue
            result.append(
                JbPlaceholderInfo(
                    pack=info.pack_name,
                    asset=info.asset_name,
                    transform=obj.GetMg(),
                )
            )
            obj.Remove()
        return result

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
                JbPlaceholderInfo(
                    asset=info.asset_name,
                    pack=info.pack_name,
                    transform=obj.GetMg(),
                ),
                source,
            )
            placeholder.InsertBefore(obj)
            obj.Remove()
            new_objects.append(placeholder)

        return new_objects

    def create_placeholder(self, placeholder_info, source) -> JbObject:
        pack_name = placeholder_info["pack"]
        asset_name = placeholder_info["asset"]
        transform = placeholder_info["transform"]

        material = c4d.BaseMaterial()
        material.SetName(f"{placeholder_info}__{placeholder_info.asset_name}")

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
