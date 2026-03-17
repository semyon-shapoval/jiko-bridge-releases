import c4d
import time
import os
import tempfile
from typing import Optional

from jb_logger import get_logger
from jb_scene_manager import JBSceneManager


logger = get_logger(__name__)


class JBFileExporter:
    def __init__(self):
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base
        self.scene = JBSceneManager()

    def _generate_path(self, ext: str) -> str:
        filename = f"bridge_{int(time.time())}{ext}"
        return os.path.join(self.cache_path, filename)

    def export_file(
        self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], ext: str
    ) -> Optional[str]:
        file_path = self._generate_path(ext)
        if ext == ".fbx":
            return self.export_fbx(doc, objects, file_path)
        elif ext == ".abc":
            return self.export_abc(doc, objects, file_path)
        elif ext == ".obj":
            return self.export_obj(doc, objects, file_path)
        elif ext == ".usd":
            return self.export_usd(doc, objects, file_path)
        else:
            logger.error("Unsupported file extension: %s", ext)
            return None

    def export_fbx(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        self.scene.set_selection(doc, objects)

        plug = c4d.plugins.FindPlugin(c4d.FORMAT_FBX_EXPORT, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            logger.error("FBX exporter not found")
            return None

        data = {}
        if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            logger.error("Failed to retrieve FBX private data from plugin.")
            return None

        fbx_export = data.get("imexporter", None)
        if not fbx_export:
            logger.error("FBX exporter interface not available in plugin data.")
            return None

        fbx_export[c4d.FBXEXPORT_SELECTION_ONLY] = True
        fbx_export[c4d.FBXEXPORT_ASCII] = False
        fbx_export[c4d.FBXEXPORT_SCALE] = 0.01

        if c4d.documents.SaveDocument(
            doc, file_path, c4d.SAVEDOCUMENTFLAGS_NONE, c4d.FORMAT_FBX_EXPORT
        ):
            logger.info("FBX exported: %s", file_path)
            return file_path
        else:
            logger.error("FBX export failed.")
            return None

    def export_abc(self, doc, objects, file_path):
        if objects:
            self.scene.set_selection(doc, objects)

        plug = c4d.plugins.FindPlugin(1028082, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            logger.error("Alembic exporter not found")
            return None

        data = {}
        if plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            abc_export = data.get("imexporter", None)
            if abc_export is not None and objects:
                abc_export[c4d.ABCEXPORT_SELECTION_ONLY] = True

        if c4d.documents.SaveDocument(
            doc, file_path, c4d.SAVEDOCUMENTFLAGS_NONE, c4d.FORMAT_ABCEXPORT
        ):
            logger.info("Alembic exported: %s", file_path)
            return file_path
        else:
            logger.error("Alembic export failed")
            return None

    def export_obj(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        # TODO: implement OBJ export
        logger.warning("OBJ export not implemented yet")
        return None

    def export_usd(
        self,
        doc: c4d.documents.BaseDocument,
        objects: list[c4d.BaseObject],
        file_path: str,
    ) -> Optional[str]:
        # TODO: implement USD export
        logger.warning("USD export not implemented yet")
        return None
