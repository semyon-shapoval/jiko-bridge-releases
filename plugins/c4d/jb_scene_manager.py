import re
import c4d
from jb_asset_model import AssetModel
from contextlib import contextmanager
from jb_tree import JBTree


class JBSceneManager:
    def __init__(self):
        self.tree = JBTree()

    @contextmanager
    def temp_doc(self, debug: bool = False):
        """Создаёт временный документ и гарантированно уничтожает его после использования."""
        tmp_doc = c4d.documents.BaseDocument()

        """ unit_scale = c4d.UnitScaleData()
        unit_scale.SetUnitScale(1.0, c4d.DOCUMENT_UNIT_CM)
        tmp_doc[c4d.DOCUMENT_DOCUNIT] = unit_scale """

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
    def isolated_doc(self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], debug: bool = True):
        """Создаёт изолированный документ с объектами и их материалами."""
        isolated = c4d.documents.IsolateObjects(doc, objects)

        unit_scale = c4d.UnitScaleData()
        unit_scale.SetUnitScale(0.01, c4d.DOCUMENT_UNIT_M)
        isolated[c4d.DOCUMENT_DOCUNIT] = unit_scale

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

    def rescale_cm_to_m(self, doc: c4d.documents.BaseDocument) -> None:
        """Масштабирует все объекты документа из CM в M (делит на 100)."""
        factor = 0.01

        for obj in self.tree.get_all_objects(doc):
            ml = obj.GetMl()
            ml.off *= factor
            obj.SetMl(ml)

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
