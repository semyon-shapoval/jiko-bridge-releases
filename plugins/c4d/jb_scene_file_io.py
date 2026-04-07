import c4d
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from jb_logger import get_logger
from jb_scene_instance import JBSceneInstance

logger = get_logger(__name__)


class JBSceneFileIO(JBSceneInstance):
    """File import/export layer in the scene hierarchy.

    Provides DCC-specific import and export methods that operate on C4D documents.
    Sits between JBSceneInstance and JBSceneManager in the chain:

        JBSceneBase → JBTree → JBSceneSelect → JBSceneInstance
            → JBSceneFileIO → JBSceneManager
    """

    def __init__(self):
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _find_plugin(
        self, plugin_id: int, plugin_type: int
    ) -> Optional[c4d.plugins.BasePlugin]:
        plug = c4d.plugins.FindPlugin(plugin_id, plugin_type)
        if not plug:
            logger.error("Plugin %d not found", plugin_id)
        return plug

    def _get_imexporter(self, plug: c4d.plugins.BasePlugin) -> Optional[object]:
        data = {}
        if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            logger.error("Failed to retrieve private data from plugin")
            return None
        imexporter = data.get("imexporter")
        if not imexporter:
            logger.error("imexporter not available in plugin data")
        return imexporter

    def _merge_document(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        t = time.time()
        result = c4d.documents.MergeDocument(
            doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
        )
        logger.info("Import took %.3fs: %s", time.time() - t, file_path)
        return result

    def _save_document(
        self, doc: c4d.documents.BaseDocument, file_path: str, format_id: int
    ) -> bool:
        t = time.time()
        result = c4d.documents.SaveDocument(
            doc, file_path, c4d.SAVEDOCUMENTFLAGS_NONE, format_id
        )
        logger.info("Export took %.3fs: %s", time.time() - t, file_path)
        return result

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def import_file(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        handler = {
            ".fbx": self._import_fbx,
            ".abc": self._import_alembic,
            ".obj": self._import_obj,
            ".usd": self._import_usd,
        }.get(ext)

        if not handler:
            logger.error("Unsupported file extension: %s", ext)
            return False

        return handler(doc, file_path)

    def _import_fbx(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_FBX_IMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.FBXIMPORT_CAMERAS] = True
            imex[c4d.FBXIMPORT_LIGHTS] = True

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("FBX import failed: %s", file_path)
        return result

    def _import_alembic(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_ABCIMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        imex = self._get_imexporter(plug)
        if imex:
            scale_data = c4d.UnitScaleData()
            scale_data.SetUnitScale(100, c4d.DOCUMENT_UNIT_CM)
            imex[c4d.ABCIMPORT_SCALE] = scale_data
            imex[c4d.ABCIMPORT_FACESETS] = True

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("Alembic import failed: %s", file_path)
        return result

    def _import_obj(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_OBJ2IMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("OBJ import failed: %s", file_path)
        return result

    def _import_usd(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_USDIMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("USD import failed: %s", file_path)
        return result

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _generate_path(self, ext: str) -> str:
        filename = f"tmp_{int(time.time())}{ext}"
        return os.path.join(self.cache_path, filename)

    def _select_all(self, doc: c4d.documents.BaseDocument) -> None:
        for obj in self.get_all_objects(doc):
            obj.SetBit(c4d.BIT_ACTIVE)

    def export_file(self, doc: c4d.documents.BaseDocument, ext: str) -> Optional[str]:
        file_path = self._generate_path(ext)
        handler = {
            ".fbx": self._export_fbx,
            ".abc": self._export_alembic,
            ".obj": self._export_obj,
            ".usd": self._export_usd,
        }.get(ext)

        if not handler:
            logger.error("Unsupported export extension: %s", ext)
            return None

        self._select_all(doc)
        return handler(doc, file_path)

    def _export_fbx(
        self, doc: c4d.documents.BaseDocument, file_path: str
    ) -> Optional[str]:
        plug = self._find_plugin(c4d.FORMAT_FBX_EXPORT, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            return None

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.FBXEXPORT_SELECTION_ONLY] = True
            imex[c4d.FBXEXPORT_ASCII] = False
            imex[c4d.FBXEXPORT_SCALE] = 0.01

        if not self._save_document(doc, file_path, c4d.FORMAT_FBX_EXPORT):
            logger.error("FBX export failed")
            return None

        logger.info("FBX exported: %s", file_path)
        return file_path

    def _export_alembic(
        self, doc: c4d.documents.BaseDocument, file_path: str
    ) -> Optional[str]:
        plug = self._find_plugin(c4d.FORMAT_ABCEXPORT, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            return None

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.ABCEXPORT_SELECTION_ONLY] = True
            scale_data = c4d.UnitScaleData()
            scale_data.SetUnitScale(0.01, c4d.DOCUMENT_UNIT_CM)
            imex[c4d.ABCEXPORT_SCALE] = scale_data

        if not self._save_document(doc, file_path, c4d.FORMAT_ABCEXPORT):
            logger.error("Alembic export failed")
            return None

        logger.info("Alembic exported: %s", file_path)
        return file_path

    def _export_obj(
        self, doc: c4d.documents.BaseDocument, file_path: str
    ) -> Optional[str]:
        # TODO: implement OBJ export
        logger.warning("OBJ export not implemented yet")
        return None

    def _export_usd(
        self, doc: c4d.documents.BaseDocument, file_path: str
    ) -> Optional[str]:
        # TODO: implement USD export
        logger.warning("USD export not implemented yet")
        return None
