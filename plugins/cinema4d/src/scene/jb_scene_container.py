"""
Scene container management for Cinema 4D.
Code by Semyon Shapoval, 2026
"""
from typing import Optional

import c4d

from src import JbContainer, AssetFile, AssetModel, AssetInfo
from src.scene import JbSceneSelect


class JbSceneContainer(JbSceneSelect):
    """Container and asset management: null objects, user data, collections."""

    def get_or_create_null(
        self, doc: c4d.documents.BaseDocument, name: str
    ) -> tuple[JbContainer, bool]:
        """Ищет или создаёт Null-объект с заданным именем и иконкой."""
        obj = doc.SearchObject(name)
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

    def _ensure_protection_tag(self, obj: JbContainer) -> None:
        if obj is None:
            return

        if obj.GetTags() is not None:
            for tag in obj.GetTags():
                try:
                    if tag.GetType() == c4d.Tprotection:
                        return
                except (AttributeError, TypeError):
                    continue

        try:
            protection_tag = c4d.BaseTag(c4d.Tprotection)
            if protection_tag is not None:
                obj.InsertTag(protection_tag)
        except (AttributeError, TypeError):
            pass

    def get_or_create_asset_container(
        self, asset: AssetModel, file: Optional[AssetFile]
    ) -> tuple[JbContainer, bool]:
        """Get or create an asset container null with user data from the asset and file."""
        doc = self.doc

        root_null, _ = self.get_or_create_null(doc, "Assets")
        self._ensure_protection_tag(root_null)

        asset_null, asset_existed = self.get_or_create_null(
            doc, f"Asset_{asset.pack_name}_{asset.asset_name}"
        )

        asset_null.InsertUnder(root_null)
        self._ensure_protection_tag(asset_null)

        self.set_user_data(asset_null, "databaseName", asset.database_name)
        self.set_user_data(asset_null, "packName", asset.pack_name)
        self.set_user_data(asset_null, "assetName", asset.asset_name)
        if file:
            self.set_user_data(asset_null, "assetType", file.asset_type)

        if len(asset_null.GetChildren()) == 0:
            asset_existed = False

        return asset_null, asset_existed

    def set_user_data(self, obj: JbContainer, name: str, value: str | None) -> None:
        """Set a user data field on the given object, creating it if necessary."""
        if value is None:
            value = ""

        for key, bc in obj.GetUserDataContainer() or []:
            if bc[c4d.DESC_NAME] == name:
                obj[key] = value
                return

        bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_SHORT_NAME] = name
        bc[c4d.DESC_DEFAULT] = value

        element = obj.AddUserData(bc)
        if element is not None:
            obj[element] = value

    def copy_user_data(self, src: JbContainer, dst: JbContainer) -> None:
        """Copy all user data fields from src to dst."""
        for key, bc in src.GetUserDataContainer():
            name = bc[c4d.DESC_NAME]
            value = src[key]
            self.set_user_data(dst, name, value)

    def cleanup_empty_objects(self, parent: JbContainer) -> None:
        """Удаляет пустые Null-объекты внутри parent."""
        for obj in parent.GetChildren():
            if (
                obj.GetType() in (c4d.Onull, c4d.Oalembicgenerator)
                and len(obj.GetChildren()) == 0
            ):
                obj.Remove()

    def filter_container_from_objects(
        self, objects: list[JbContainer]
    ) -> list[JbContainer]:
        """Filter out non-container objects from the given list."""
        return [
            obj
            for obj in objects
            if obj.CheckType(c4d.Onull) and AssetInfo.from_user_data(obj) is not None
        ]

    def get_objects_recursive(self, container: JbContainer) -> list:
        """Unified API: direct children of asset null (isolated_doc handles depth)."""
        return container.GetChildren()

    def clear_container(self, container: JbContainer) -> None:
        """Unified API: remove all children from asset null."""
        for child in container.GetChildren():
            child.Remove()

    def move_objects_to_container(self, objects: list, container: JbContainer) -> None:
        """Unified API: re-parents objects under asset null."""
        for obj in objects:
            obj.Remove()
            obj.InsertUnder(container)
