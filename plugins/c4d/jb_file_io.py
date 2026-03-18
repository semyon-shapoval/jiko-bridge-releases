import c4d
import time
import os
import tempfile
from pathlib import Path
from typing import Optional

from jb_logger import get_logger

logger = get_logger(__name__)


class BaseFileIO:
    def _find_plugin(self, plugin_id: int) -> Optional[c4d.BasePlugin]:
        plug = c4d.plugins.FindPlugin(plugin_id, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            logger.error("Plugin %d not found", plugin_id)
        return plug

    def _get_imexporter(self, plug: c4d.BasePlugin) -> Optional[object]:
        data = {}
        if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            logger.error("Failed to retrieve private data from plugin")
            return None
        imexporter = data.get("imexporter")
        if not imexporter:
            logger.error("imexporter not available in plugin data")
        return imexporter

    def _merge_document(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        return c4d.documents.MergeDocument(
            doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
        )

    def _save_document(
        self, doc: c4d.documents.BaseDocument, file_path: str, format_id: int
    ) -> bool:
        return c4d.documents.SaveDocument(
            doc, file_path, c4d.SAVEDOCUMENTFLAGS_NONE, format_id
        )


class JBFileImporter(BaseFileIO):
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
        plug = self._find_plugin(c4d.FORMAT_FBX_EXPORT)
        if not plug:
            return False

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.FBXEXPORT_CAMERAS] = True
            imex[c4d.FBXEXPORT_LIGHTS] = True
            imex[c4d.FBXEXPORT_MATERIALS] = True

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("FBX import failed: %s", file_path)
        return result

    def _import_alembic(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_ABCEXPORT)
        if not plug:
            return False

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.ABCIMPORT_SCALE] = 1
            imex[c4d.ABCIMPORT_FACESETS] = True

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("Alembic import failed: %s", file_path)
        return result

    def _import_obj(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_OBJ2IMPORT)
        if not plug:
            return False

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("OBJ import failed: %s", file_path)
        return result

    def _import_usd(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_USDIMPORT)
        if not plug:
            return False

        result = self._merge_document(doc, file_path)
        if not result:
            logger.error("USD import failed: %s", file_path)
        return result


class JBFileExporter(BaseFileIO):
    def __init__(self):
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    def export_file(
        self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], ext: str
    ) -> Optional[str]:
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

        return handler(doc, objects, file_path)

    def _generate_path(self, ext: str) -> str:
        filename = f"tmp_{int(time.time())}{ext}"
        return os.path.join(self.cache_path, filename)

    def _set_selection(
        self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject]
    ) -> None:
        doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

    def _export_fbx(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        self._set_selection(doc, objects)

        plug = self._find_plugin(c4d.FORMAT_FBX_EXPORT)
        if not plug:
            return None

        imex = self._get_imexporter(plug)
        if not imex:
            return None

        imex[c4d.FBXEXPORT_SELECTION_ONLY] = True
        imex[c4d.FBXEXPORT_ASCII] = False
        imex[c4d.FBXEXPORT_SCALE] = 0.01

        if not self._save_document(doc, file_path, c4d.FORMAT_FBX_EXPORT):
            logger.error("FBX export failed")
            return None

        logger.info("FBX exported: %s", file_path)
        return file_path

    def _export_alembic(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        self._set_selection(doc, objects)

        plug = self._find_plugin(1028082)
        if not plug:
            return None

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.ABCEXPORT_SELECTION_ONLY] = True

        if not self._save_document(doc, file_path, c4d.FORMAT_ABCEXPORT):
            logger.error("Alembic export failed")
            return None

        logger.info("Alembic exported: %s", file_path)
        return file_path

    def _export_obj(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        # TODO: implement OBJ export
        logger.warning("OBJ export not implemented yet")
        return None

    def _export_usd(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        # TODO: implement USD export
        logger.warning("USD export not implemented yet")
        return None