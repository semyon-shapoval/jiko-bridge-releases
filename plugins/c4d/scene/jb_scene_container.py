import c4d
from typing import Optional

from jb_asset_model import AssetModel
from scene.jb_scene_temp import JBSceneTemp
from jb_types import JbContainer


class JBSceneContainer(JBSceneTemp):
    """Container and asset management: null objects, user data, collections."""

    # ------------------------------------------------------------------
    # Null helpers
    # ------------------------------------------------------------------

    def get_or_create_null(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
        target: JbContainer = None,
    ) -> tuple[JbContainer, bool]:
        """Ищет или создаёт Null-объект с заданным именем и иконкой."""
        obj = target or doc.SearchObject(name)
        existed = obj is not None

        if not existed:
            obj = c4d.BaseObject(c4d.Onull)
            doc.InsertObject(obj)

        obj.SetName(name)
        obj[c4d.ID_BASELIST_ICON_FILE] = "12499"
        obj[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = (
            c4d.ID_BASELIST_ICON_COLORIZE_MODE_CUSTOM
        )
        obj[c4d.ID_BASELIST_ICON_COLOR] = c4d.Vector(0.071, 0.949, 0.85)

        return obj, existed

    def get_or_create_container(
        self,
        doc: c4d.documents.BaseDocument,
        asset: AssetModel,
        target: JbContainer = None,
    ) -> tuple[JbContainer, bool]:
        root_null, _ = self.get_or_create_null(doc, "Assets")

        asset_null, asset_existed = self.get_or_create_null(
            doc, f"Asset_{asset.pack_name}_{asset.asset_name}", target
        )

        asset_null.InsertUnder(root_null)

        self.set_user_data(asset_null, "pack_name", asset.pack_name)
        self.set_user_data(asset_null, "asset_name", asset.asset_name)
        self.set_user_data(asset_null, "asset_type", asset.asset_type)
        self.set_user_data(asset_null, "database_name", asset.database_name)

        if len(asset_null.GetChildren()) == 0:
            asset_existed = False

        return asset_null, asset_existed

    # ------------------------------------------------------------------
    # User data
    # ------------------------------------------------------------------

    def set_user_data(self, obj: JbContainer, name: str, value: str) -> None:
        for key, bc in obj.GetUserDataContainer():
            if bc[c4d.DESC_NAME] == name:
                obj[key] = value
                return

        bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_SHORT_NAME] = name
        bc[c4d.DESC_DEFAULT] = value

        element = obj.AddUserData(bc)
        if element:
            obj[element] = value

    def copy_user_data(self, src: JbContainer, dst: JbContainer) -> None:
        for key, bc in src.GetUserDataContainer():
            name = bc[c4d.DESC_NAME]
            value = src[key]
            self.set_user_data(dst, name, value)

    def remove_empty_nulls(self, parent: JbContainer) -> None:
        """Удаляет пустые Null-объекты внутри parent."""
        for obj in parent.GetChildren():
            if (
                obj.GetType() in (c4d.Onull, c4d.Oalembicgenerator)
                and len(obj.GetChildren()) == 0
            ):
                obj.Remove()

    # ------------------------------------------------------------------
    # Unified API
    # ------------------------------------------------------------------

    def get_or_create_asset_container(
        self, asset: AssetModel, target: JbContainer = None
    ) -> tuple[JbContainer, bool]:
        """Unified API: wraps get_or_create_asset using internal doc property."""
        return self.get_or_create_container(self.doc, asset, target)

    def get_asset_info(self, container: JbContainer) -> Optional[AssetModel]:
        """Unified API: reads AssetModel from a C4D null's user data."""
        return AssetModel.from_c4d_object(container)

    def get_objects_recursive(self, container: JbContainer) -> list:
        """Unified API: direct children of asset null (isolated_doc handles depth)."""
        return container.GetChildren()

    def clear_container(self, container: JbContainer) -> None:
        """Unified API: remove all children from asset null."""
        for child in container.GetChildren():
            child.Remove()

    def cleanup_empty_objects(self, container: JbContainer) -> None:
        """Unified API: alias for remove_empty_nulls."""
        self.remove_empty_nulls(container)

    def move_objects_to_container(self, objects: list, container: JbContainer) -> None:
        """Unified API: re-parents objects under asset null."""
        for obj in objects:
            obj.Remove()
            obj.InsertUnder(container)
