import re
import c4d
from jb_asset_model import AssetModel
from contextlib import contextmanager


class JBSceneManager:
    @contextmanager
    def temp_doc(self, debug: bool = False):
        """Создаёт временный документ и гарантированно уничтожает его после использования."""
        tmp_doc = c4d.documents.BaseDocument()
        try:
            yield tmp_doc
        finally:
            if debug:
                c4d.documents.InsertBaseDocument(tmp_doc)
                c4d.documents.SetActiveDocument(tmp_doc)
                c4d.EventAdd()
            else:
                c4d.documents.KillDocument(tmp_doc)

    def walk(self, obj: c4d.BaseObject | None, fn):
        if obj is None:
            return

        if isinstance(obj, (list, tuple)):
            for o in obj:
                self.walk(o, fn)
            return

        fn(obj)
        child = obj.GetDown()
        while child:
            self.walk(child, fn)
            child = child.GetNext()

    def get_children(self, obj) -> list[c4d.BaseObject]:
        """Возвращает плоский список всех объектов в иерархии obj."""
        result = []
        self.walk(obj, result.append)
        return result

    def get_all_objects(self, doc: c4d.documents.BaseDocument) -> list[c4d.BaseObject]:
        result = []
        obj = doc.GetFirstObject()
        while obj:
            self.walk(obj, result.append)
            obj = obj.GetNext()
        return result

    def get_top_objects(self, doc: c4d.documents.BaseDocument) -> list[c4d.BaseObject]:
        """Возвращает список корневых объектов документа."""
        result = []
        obj = doc.GetFirstObject()
        while obj:
            result.append(obj)
            obj = obj.GetNext()
        return result

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

    def transfer_from_doc(
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

    def set_selection(
        self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject]
    ) -> None:
        """Снимает выделение и выделяет переданные объекты."""
        doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

    def create_instance(
        self,
        doc: c4d.documents.BaseDocument,
        link: c4d.BaseObject,
        name: str,
        parent: c4d.BaseObject = None,
    ) -> c4d.BaseObject:
        """Создаёт Oinstance, вставляет в сцену и опционально под parent."""
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = link
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1

        for key, bc in link.GetUserDataContainer():
            self.set_user_data(instance, bc[c4d.DESC_NAME], link[key])

        doc.InsertObject(instance)
        if parent:
            instance.InsertUnder(parent)
        instance.SetBit(c4d.BIT_ACTIVE)
        return instance

    def create_placeholder(self, pack_name: str, asset_name: str) -> c4d.BaseObject:
        """Создаёт плейсхолдер в виде полигона с тегом выделения, содержащим имя ассета. Используется для layout-а."""
        obj = c4d.BaseObject(c4d.Oplane)
        obj.SetName(f"{pack_name}__{asset_name}")
        obj[c4d.PRIM_PLANE_WIDTH] = 100
        obj[c4d.PRIM_PLANE_HEIGHT] = 100
        obj[c4d.PRIM_PLANE_SUBW] = 1
        obj[c4d.PRIM_PLANE_SUBH] = 1

        tag = obj.MakeTag(c4d.Tpolygonselection)
        tag.SetName(f"{pack_name}__{asset_name}")

        selection = tag.GetBaseSelect()
        selection.SelectAll(1)

        return obj

    def extract_layout_placeholders(
        self, doc: c4d.documents.BaseDocument, layout_null: c4d.BaseObject
    ) -> list[dict]:
        objs = self.get_children(layout_null)
        self.set_selection(doc, objs)
        patterns = [
            re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$"),
            re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$"),
        ]
        result = []

        for obj in objs:
            match = next(
                (
                    m
                    for t in obj.GetTags()
                    for p in patterns
                    if (m := p.match(t.GetName()))
                ),
                None,
            )
            if not match:
                continue

            result.append(
                {
                    "pack_name": match.group("pack"),
                    "asset_name": match.group("asset"),
                    "matrix": obj.GetMg(),
                }
            )
            obj.Remove()

        return result

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
