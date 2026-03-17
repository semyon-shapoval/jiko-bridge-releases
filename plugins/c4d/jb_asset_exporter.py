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

        return self.prepare_asset(selected_objects)

    def update_asset(self, obj: c4d.BaseObject):
        asset_info = AssetModel.from_c4d_object(obj)
        if not asset_info:
            logger.error("Invalid asset information")
            return None

        pack_name = asset_info.pack_name
        asset_name = asset_info.asset_name

        objects = self.scene.get_children(obj)
        if objects and objects[0] is obj:
            objects.pop(0)

        ext = self._detect_ext(objects)
        filepath = self.file_exporter.export_file(self.doc, objects, ext)

        if filepath:
            success = self.api.update_asset(
                filepath, pack_name, asset_name, asset_info.database_name or ""
            )
            if success:
                logger.info("Asset %s updated successfully.", asset_name)
            else:
                logger.error("Failed %s to update asset.", asset_name)

    def prepare_asset(self, objects: list[c4d.BaseObject]):
        doc = self.doc
        ext = self._detect_ext(objects)

        tmp_name = f"temp_asset_{int(time.time())}"
        tmp_null = c4d.BaseObject(c4d.Onull)
        tmp_null.SetName(tmp_name)
        doc.InsertObject(tmp_null)
        self.scene.group_objects(objects, tmp_null)

        if ext == ".abc":
            with self.scene.temp_doc() as tmp_doc:
                self.scene.replace_asset_nulls_with_placeholders(tmp_doc, objects)
                export_null = tmp_doc.SearchObject(tmp_name)
                export_objects = export_null.GetChildren() if export_null else []
                file_path = self.file_exporter._generate_path(".abc")
                filepath = self.file_exporter.export_abc(tmp_doc, export_objects, file_path)
        else:
            filepath = self.file_exporter.export_file(doc, objects, ext)

        if not filepath:
            logger.error("Export failed, objects remain in temp null.")
            self.scene.mark_as_error(tmp_null)
            return None

        c4d.StatusSetText("Jiko Bridge: creating asset, please wait...")
        c4d.gui.SetMousePointer(c4d.MOUSE_BUSY)
        try:
            asset = self.api.create_asset(filepath)
        finally:
            c4d.gui.SetMousePointer(c4d.MOUSE_NORMAL)
            c4d.StatusClear()

        if not asset:
            logger.error(
                "Failed to create asset for '%s', objects remain in temp null.",
                filepath,
            )
            self.scene.mark_as_error(tmp_null)
            return None

        self.scene.get_or_create_asset(doc, asset, target=tmp_null)

    def _detect_ext(self, objects: list[c4d.BaseObject]) -> str:
        for obj in self.scene.get_children(objects):
            if obj.CheckType(c4d.Oinstance):
                return ".abc"
        return ".fbx"
