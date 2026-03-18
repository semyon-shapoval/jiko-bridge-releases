import time
import c4d

from jb_logger import get_logger
from jb_api import JB_API
from jb_asset_model import AssetModel
from jb_scene_manager import JBSceneManager
from jb_file_exporter import JBFileExporter
from jb_utils import busy_cursor

logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBSceneManager()
        self.file_exporter = JBFileExporter()

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        return c4d.documents.GetActiveDocument()

    def export_asset(self) -> None:
        selected = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

        if self._is_single_asset_null(selected):
            self._update_asset(selected[0])
        else:
            self._create_new_asset(selected)

    def _update_asset(self, obj: c4d.BaseObject) -> None:
        asset = AssetModel.from_c4d_object(obj)
        if not asset:
            logger.error("Invalid asset information on object: %s", obj.GetName())
            return

        if not c4d.gui.QuestionDialog(
            f"Update asset '{asset.asset_name}'?\nThis will overwrite the existing file."
        ):
            return

        ext = self._detect_ext(self.scene.tree.get_children(obj))
        filepath = self.export_with_placeholder(obj, ext)
        if not filepath:
            return

        if self.api.update_asset(
            filepath, asset.pack_name, asset.asset_name,
            asset.asset_type, asset.database_name,
        ):
            logger.info("Asset '%s' updated successfully.", asset.asset_name)
        else:
            logger.error("Failed to update asset '%s'.", asset.asset_name)

    def _create_new_asset(self, objects: list[c4d.BaseObject]) -> None:
        if not c4d.gui.QuestionDialog("Create new asset from selected objects? Go to Jiko Bridge app to finish setup."):
            return
        
        doc = self.doc
        ext = self._detect_ext(objects)

        tmp_null = self._build_temp_null(doc, objects)
        filepath = self.export_with_placeholder(tmp_null, ext)

        if not filepath:
            logger.error("Export failed — removing temporary null.")
            tmp_null.Remove()
            return

        with busy_cursor("Jiko Bridge: creating asset, please wait..."):
            asset = self.api.create_asset(filepath)

        if not asset:
            logger.error("Failed to create asset for '%s'.", filepath)
            tmp_null.Remove()
            return

        self.scene.get_or_create_asset(doc, asset, target=tmp_null)

    def _build_temp_null(
        self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject]
    ) -> c4d.BaseObject:
        null = c4d.BaseObject(c4d.Onull)
        null.SetName(f"temp_asset_{int(time.time())}")
        doc.InsertObject(null)
        for obj in objects:
            obj.GetClone().InsertUnder(null)
        return null


    def export_with_placeholder(self, obj: c4d.BaseObject, ext: str) -> str | None:
        self._sync_instance_user_data(obj)

        with self.scene.temp_doc() as tmp_doc:
            clone = obj.GetClone()
            tmp_doc.InsertObject(clone)
            self._replace_instances_with_placeholders(clone)
            return self.file_exporter.export_file(
                tmp_doc, clone.GetChildren(), ext
            )

    def _sync_instance_user_data(self, obj: c4d.BaseObject) -> None:
        for child in self.scene.tree.get_children(obj):
            if not child.CheckType(c4d.Oinstance):
                continue
            linked = child[c4d.INSTANCEOBJECT_LINK]
            if linked:
                self.scene.copy_user_data(linked, child)

    def _replace_instances_with_placeholders(self, root: c4d.BaseObject) -> None:
        for instance in self.scene.tree.get_children(root):
            if not instance.CheckType(c4d.Oinstance):
                continue

            info = AssetModel.from_c4d_object(instance)
            if not info or not info.pack_name or not info.asset_name:
                continue

            placeholder = self.scene.create_placeholder(info.pack_name, info.asset_name)
            placeholder.SetMg(instance.GetMg())
            placeholder.InsertBefore(instance)
            instance.Remove()

    def _is_single_asset_null(self, objects: list[c4d.BaseObject]) -> bool:
        return (
            len(objects) == 1
            and objects[0].CheckType(c4d.Onull)
            and bool(AssetModel.from_c4d_object(objects[0]))
        )

    def _has_instances(self, objects: list[c4d.BaseObject]) -> bool:
        return any(o.CheckType(c4d.Oinstance) for o in objects)

    def _detect_ext(self, objects: list[c4d.BaseObject]) -> str:
        return ".abc" if self._has_instances(objects) else ".fbx"