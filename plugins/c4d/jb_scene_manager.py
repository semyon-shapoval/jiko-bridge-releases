import c4d
from contextlib import contextmanager
from typing import Optional

from jb_asset_model import AssetModel
from jb_scene_file_io import JBSceneFileIO
from jb_logger import get_logger


logger = get_logger(__name__)


class JBSceneManager(JBSceneFileIO):
    # ------------------------------------------------------------------
    # Active document property
    # ------------------------------------------------------------------

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        return c4d.documents.GetActiveDocument()

    @contextmanager
    def temp_doc(self, unit_scale: int = c4d.DOCUMENT_UNIT_CM, debug: bool = False):
        """Создаёт временный документ и гарантированно уничтожает его после использования."""
        tmp_doc = c4d.documents.BaseDocument()

        unit_scale_data = c4d.UnitScaleData()
        unit_scale_data.SetUnitScale(1, unit_scale)
        tmp_doc[c4d.DOCUMENT_DOCUNIT] = unit_scale_data

        try:
            yield tmp_doc
        finally:
            if debug:
                c4d.documents.InsertBaseDocument(tmp_doc)
                c4d.documents.SetActiveDocument(tmp_doc)
                c4d.EventAdd()
            else:
                c4d.documents.KillDocument(tmp_doc)

    @contextmanager
    def isolated_doc(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        unit_scale: int = c4d.DOCUMENT_UNIT_CM,
        debug: bool = False,
    ):
        """Создаёт изолированный документ с объектами и их материалами."""
        isolated = c4d.documents.IsolateObjects(doc, objects)

        unit_scale_data = c4d.UnitScaleData()
        unit_scale_data.SetUnitScale(1, unit_scale)
        isolated[c4d.DOCUMENT_DOCUNIT] = unit_scale_data

        if not isolated:
            yield None
            return

        try:
            yield isolated
        finally:
            if debug:
                c4d.documents.InsertBaseDocument(isolated)
                c4d.documents.SetActiveDocument(isolated)
                c4d.EventAdd()
            else:
                c4d.documents.KillDocument(isolated)

    def copy_objects_from_doc(
        self,
        src: c4d.documents.BaseDocument,
        dst: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        parent: c4d.BaseObject,
    ) -> None:
        """Переносит материалы и объекты из src в dst, вставляя объекты под parent."""
        mat = src.GetFirstMaterial()
        while mat:
            next_mat = mat.GetNext()
            mat.Remove()
            dst.InsertMaterial(mat)
            mat = next_mat

        for obj in objects:
            obj.Remove()
            dst.InsertObject(obj)
            obj.InsertUnder(parent)
            obj.SetBit(c4d.BIT_ACTIVE)

    def project_scale(
        self, doc: c4d.documents.BaseDocument, factor: float = 0.01
    ) -> None:
        """Масштабирует сцену:
        - точки полигональных объектов (меш не деформируется, Scale остаётся 1)
        - позиции всех объектов (относительные, не трогая Rotation и Scale)
        """

        for obj in self.get_all_objects(doc):
            if obj.IsInstanceOf(c4d.Opolygon):
                points = obj.GetAllPoints()
                if points:
                    obj.SetAllPoints([p * factor for p in points])
                    obj.Message(c4d.MSG_UPDATE)

            pos = obj.GetRelPos()
            obj.SetRelPos(pos * factor)

    def get_or_create_null(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
        target: c4d.BaseObject = None,
    ) -> tuple[c4d.BaseObject, bool]:
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

    def get_or_create_asset(
        self,
        doc: c4d.documents.BaseDocument,
        asset: AssetModel,
        target: c4d.BaseObject = None,
    ) -> tuple[c4d.BaseObject, bool]:
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

    def set_user_data(self, obj: c4d.BaseObject, name: str, value: str) -> None:
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

    def copy_user_data(self, src: c4d.BaseObject, dst: c4d.BaseObject) -> None:
        for key, bc in src.GetUserDataContainer():
            name = bc[c4d.DESC_NAME]
            value = src[key]
            self.set_user_data(dst, name, value)

    def remove_empty_nulls(self, parent: c4d.BaseObject) -> None:
        """Удаляет пустые Null-объекты внутри parent."""
        for obj in parent.GetChildren():
            if (
                obj.GetType() in (c4d.Onull, c4d.Oalembicgenerator)
                and len(obj.GetChildren()) == 0
            ):
                obj.Remove()

    def make_editable_recursive(
        self,
        obj: c4d.BaseObject | None,
        doc: c4d.documents.BaseDocument,
    ) -> None:
        if obj is None:
            return

        # Сохраняем соседей и родителя до конвертации — после они могут стать невалидными
        next_obj = obj.GetNext()
        parent = obj.GetUp()

        # Сначала рекурсивно обходим детей
        self.make_editable_recursive(obj.GetDown(), doc)

        if not obj.IsAlive() or obj.IsInstanceOf(c4d.Opolygon):
            self.make_editable_recursive(next_obj, doc)
            return

        result = c4d.utils.SendModelingCommand(
            command=c4d.MCOMMAND_MAKEEDITABLE,
            list=[obj],
            mode=c4d.MODELINGCOMMANDMODE_ALL,
            doc=doc,
        )

        if isinstance(result, list):
            for new_obj in reversed(result):
                if parent:
                    new_obj.InsertUnder(parent)
                else:
                    doc.InsertObject(new_obj)

        self.make_editable_recursive(next_obj, doc)

    # ------------------------------------------------------------------
    # Unified API — used by shared importer / exporter
    # ------------------------------------------------------------------

    def get_or_create_asset_container(self, asset: AssetModel, target=None) -> tuple:
        """Unified API: wraps get_or_create_asset using internal doc property."""
        return self.get_or_create_asset(self.doc, asset, target)

    def get_asset_info(self, container) -> Optional[AssetModel]:
        """Unified API: reads AssetModel from a C4D null's user data."""
        return AssetModel.from_c4d_object(container)

    def get_objects_recursive(self, container) -> list:
        """Unified API: direct children of asset null (isolated_doc handles depth)."""
        return container.GetChildren()

    def clear_container(self, container) -> None:
        """Unified API: remove all children from asset null."""
        for child in container.GetChildren():
            child.Remove()

    def cleanup_empty_objects(self, container) -> None:
        """Unified API: alias for remove_empty_nulls."""
        self.remove_empty_nulls(container)

    def move_objects_to_container(self, objects: list, container) -> None:
        """Unified API: re-parents objects under asset null."""
        for obj in objects:
            obj.Remove()
            obj.InsertUnder(container)

    def import_file_to_container(self, file_path: str, container) -> None:
        """Unified API: import file and place objects under container."""
        with self.temp_doc() as tmp_doc:
            if not self.import_file(tmp_doc, file_path):
                logger.warning("No objects imported for file: %s", file_path)
                return
            root_objects = self.get_top_objects(tmp_doc)
            if not root_objects:
                logger.warning("No objects found after import: %s", file_path)
                return
            self.project_scale(tmp_doc, 1)
            self.copy_objects_from_doc(tmp_doc, self.doc, root_objects, container)

    def export_to_temp_file(self, objects: list, ext: str) -> Optional[str]:
        """Unified API: export objects to temp file, replacing instances with placeholders."""
        for obj in objects:
            if obj.CheckType(c4d.Oinstance):
                linked = obj[c4d.INSTANCEOBJECT_LINK]
                if linked:
                    self.copy_user_data(linked, obj)

        with self.isolated_doc(
            self.doc, objects, unit_scale=c4d.DOCUMENT_UNIT_M, debug=False
        ) as tmp_doc:
            if tmp_doc is None:
                return None
            self._replace_instances_with_placeholders(tmp_doc.GetFirstObject())
            tmp_doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            self.make_editable_recursive(tmp_doc.GetFirstObject(), tmp_doc)
            self.project_scale(tmp_doc, 0.01)
            return self.export_file(tmp_doc, ext)
