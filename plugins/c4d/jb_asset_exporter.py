import time
import c4d

from jb_logger import get_logger
from jb_api import JB_API
from jb_asset_model import AssetModel
from jb_scene_manager import JBSceneManager
from jb_file_exporter import JBFileExporter


logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBSceneManager()
        self.file_exporter = JBFileExporter()

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        return c4d.documents.GetActiveDocument()

    def export_asset(self):
        selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

        if (
            len(selected_objects) == 1
            and selected_objects[0].CheckType(c4d.Onull)
            and AssetModel.from_c4d_object(selected_objects[0])
        ):
            return self.update_asset(selected_objects[0])

        return self.create_new_asset(selected_objects)

    def update_asset(self, obj: c4d.BaseObject):
        asset = AssetModel.from_c4d_object(obj)
        if not asset:
            logger.error("Invalid asset information")
            return None

        if not c4d.gui.QuestionDialog(
            f"Update asset '{asset.asset_name}'?\nThis will overwrite the existing file."
        ):
            return None

        objects = self.scene.get_children(obj)
        if objects and objects[0] is obj:
            objects.pop(0)

        ext = self._detect_ext(objects)
        filepath = self.export_with_placeholder(obj, ext)

        if filepath:
            success = self.api.update_asset(
                filepath,
                asset.pack_name,
                asset.asset_name,
                asset.asset_type,
                asset.database_name,
            )
            if success:
                logger.info("Asset %s updated successfully.", asset.asset_name)
            else:
                logger.error("Failed %s to update asset.", asset.asset_name)

    def create_new_asset(self, objects: list[c4d.BaseObject]):
        doc = self.doc
        ext = self._detect_ext(objects)

        tmp_name = f"temp_asset_{int(time.time())}"
        tmp_null = c4d.BaseObject(c4d.Onull)
        tmp_null.SetName(tmp_name)
        doc.InsertObject(tmp_null)

        for obj in objects:
            clone = obj.GetClone()
            clone.InsertUnder(tmp_null)

        filepath = self.export_with_placeholder(tmp_null, ext)

        if not filepath:
            logger.error("Export failed.")
            tmp_null.Remove()
            return None

        c4d.StatusSetText("Jiko Bridge: creating asset, please wait...")
        c4d.gui.SetMousePointer(c4d.MOUSE_BUSY)

        try:
            asset = self.api.create_asset(filepath)
        finally:
            c4d.gui.SetMousePointer(c4d.MOUSE_NORMAL)
            c4d.StatusClear()

        if not asset:
            logger.error("Failed to create asset for '%s'.", filepath)
            tmp_null.Remove()
            return None

        self.scene.get_or_create_asset(doc, asset, target=tmp_null)

    def export_with_placeholder(
        self,
        obj: c4d.BaseObject,
        ext: str,
    ) -> str | None:
        for child in self.scene.get_children(obj):
            if not child.CheckType(c4d.Oinstance):
                continue
            linked = child[c4d.INSTANCEOBJECT_LINK]
            if not linked:
                continue
            self.scene.copy_user_data(linked, child)

        with self.scene.temp_doc() as tmp_doc:
            clone = obj.GetClone()
            tmp_doc.InsertObject(clone)

            for instance in self.scene.get_children(clone):
                if not instance.CheckType(c4d.Oinstance):
                    continue
                asset_info = AssetModel.from_c4d_object(instance)
                if (
                    not asset_info
                    or not asset_info.pack_name
                    or not asset_info.asset_name
                ):
                    continue

                placeholder = self.scene.create_placeholder(
                    asset_info.pack_name, asset_info.asset_name
                )
                placeholder.SetMg(instance.GetMg())
                placeholder.InsertBefore(instance)
                instance.Remove()

            export_objects = clone.GetChildren()
            return self.file_exporter.export_file(tmp_doc, export_objects, ext)

    def _has_instances(self, objects: list[c4d.BaseObject]) -> bool:
        return any(o.CheckType(c4d.Oinstance) for o in self.scene.get_children(objects))

    def _detect_ext(self, objects: list[c4d.BaseObject]) -> str:
        return ".abc" if self._has_instances(objects) else ".fbx"
