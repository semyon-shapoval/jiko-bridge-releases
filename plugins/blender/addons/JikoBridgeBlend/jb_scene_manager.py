from contextlib import contextmanager
from typing import Optional

import bpy

from .jb_asset_model import AssetModel
from .jb_logger import get_logger

logger = get_logger(__name__)

JB_ASSETS_COLLECTION = "Assets"


class JBSceneManager:
    """Управляет объектами, коллекциями и инстансами в сцене Blender."""

    # ------------------------------------------------------------------
    # Temp scene (аналог temp_doc из C4D)
    # ------------------------------------------------------------------

    @contextmanager
    def temp_scene(self):
        """
        Создаёт временную сцену для подготовки экспорта.
        Пользователь её не видит. После выхода из контекста сцена и все
        созданные в ней объекты/меши гарантированно удаляются.
        """
        temp = bpy.data.scenes.new("_jb_temp_export")
        window = bpy.context.window_manager.windows[0]
        try:
            with bpy.context.temp_override(window=window, scene=temp):
                yield temp
        finally:
            for obj in list(temp.collection.all_objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            for mesh in [m for m in bpy.data.meshes if m.users == 0]:
                bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(temp)

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def get_or_create_root_collection(self) -> bpy.types.Collection:
        """Возвращает или создаёт корневую коллекцию JB_Assets."""
        col = bpy.data.collections.get(JB_ASSETS_COLLECTION)
        if not col:
            col = bpy.data.collections.new(JB_ASSETS_COLLECTION)
            bpy.context.scene.collection.children.link(col)
        return col

    def get_or_create_asset_collection(
        self,
        asset: AssetModel,
        target_collection: Optional[bpy.types.Collection] = None,
    ) -> tuple:
        """
        Возвращает (collection, existed).

        Если target_collection задан — переименовываем и назначаем метаданные на него.
        Иначе ищем по имени или создаём новый.
        """
        root = self.get_or_create_root_collection()
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"

        if target_collection:
            col = target_collection
            existed = col.name in bpy.data.collections
        else:
            col = bpy.data.collections.get(name)
            existed = col is not None
            if not col:
                col = bpy.data.collections.new(name)

        col.name = name
        self._set_asset_metadata(col, asset)

        # Линкуем в корневую коллекцию если ещё не там
        if name not in [c.name for c in root.children]:
            try:
                root.children.link(col)
            except RuntimeError:
                pass  # Уже залинкована

        # Считаем коллекцию пустой если в ней нет объектов
        if len(col.objects) == 0:
            existed = False

        return col, existed

    def _set_asset_metadata(self, col: bpy.types.Collection, asset: AssetModel) -> None:
        col["jb_pack_name"] = asset.pack_name or ""
        col["jb_asset_name"] = asset.asset_name or ""
        col["jb_asset_type"] = asset.asset_type or ""
        col["jb_database_name"] = asset.database_name or ""

    # ------------------------------------------------------------------
    # Objects inside collections
    # ------------------------------------------------------------------

    def move_objects_to_collection(
        self, objects: list, target: bpy.types.Collection
    ) -> None:
        """Перемещает объекты из их текущих коллекций в target."""
        for obj in objects:
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            target.objects.link(obj)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def remove_empty_from_collection(
        self, parent_collection: bpy.types.Collection
    ) -> None:
        """Удаляет объекты типа Empty из коллекции, исключая инстансы коллекций."""
        for obj in list(parent_collection.objects):
            if obj.type == "EMPTY" and obj.instance_type != "COLLECTION":
                bpy.data.objects.remove(obj, do_unlink=True)

        for child in parent_collection.children:
            self.remove_empty_from_collection(child)
