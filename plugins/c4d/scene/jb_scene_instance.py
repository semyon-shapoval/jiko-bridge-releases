import c4d

from jb_logger import get_logger

from jb_asset_model import AssetInfo
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
            if not obj.IsInstanceOf(c4d.Opolygon):
                continue
            if obj.GetPointCount() != 4:
                continue

            info = None
            for tag in obj.GetTags():
                if tag.CheckType(c4d.Ttexture):
                    material = (
                        tag[c4d.TEXTURETAG_MATERIAL]
                        if tag.GetType() == c4d.Ttexture
                        else None
                    )
                    if material:
                        info = AssetInfo.from_placeholder_name(material.GetName())
                        if info:
                            break
            if not info:
                continue
            result.append(
                {
                    "pack_name": info.pack_name,
                    "asset_name": info.asset_name,
                    "matrix": obj.GetMg(),
                }
            )
            obj.Remove()
        return result

    # ------------------------------------------------------------------
    # Internal — placeholder creation / instance replacement
    # ------------------------------------------------------------------

    def _replace_instances_with_placeholders(
        self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject]
    ) -> None:
        if not objects:
            return

        for obj in objects:
            if not obj.CheckType(c4d.Oinstance):
                continue
            info = AssetInfo.get_asset_info(obj)
            if not info:
                continue
            placeholder = self._create_placeholder(doc, info.pack_name, info.asset_name)
            placeholder.SetMg(obj.GetMg())
            placeholder.InsertBefore(obj)
            obj.Remove()

    def _create_placeholder(
        self,
        doc: c4d.documents.BaseDocument,
        pack_name: str,
        asset_name: str,
    ):
        material_type = getattr(c4d, "Mmaterial", None)
        material = (
            c4d.BaseMaterial(material_type)
            if material_type is not None
            else c4d.BaseMaterial()
        )
        material.SetName(f"{pack_name}__{asset_name}")
        doc.InsertMaterial(material)

        obj = c4d.BaseObject(c4d.Oplane)
        obj.SetName(f"{pack_name}__{asset_name}")
        obj[c4d.PRIM_PLANE_WIDTH] = 100
        obj[c4d.PRIM_PLANE_HEIGHT] = 100
        obj[c4d.PRIM_PLANE_SUBW] = 1
        obj[c4d.PRIM_PLANE_SUBH] = 1

        tag = obj.MakeTag(c4d.Ttexture)
        if tag is not None:
            try:
                tag[c4d.TEXTURETAG_MATERIAL] = material
            except Exception:
                # Fallback for older/newer C4D API variants.
                if hasattr(tag, "SetMaterial"):
                    tag.SetMaterial(material)
        return obj
