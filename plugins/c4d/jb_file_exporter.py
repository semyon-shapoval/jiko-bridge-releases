import c4d
import time
import os
import tempfile
from typing import Optional


class JBFileExporter:
    def __init__(self):
        base = os.path.join(tempfile.gettempdir(), 'jiko-bridge')
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    def _generate_path(self, ext: str) -> str:
        filename = f"bridge_{int(time.time())}{ext}"
        return os.path.join(self.cache_path, filename)

    def export_file(self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], ext: str) -> Optional[str]:
        file_path = self._generate_path(ext)
        if ext == '.fbx':
            return self.export_fbx(doc, objects, file_path)
        elif ext == '.abc':
            return self.export_abc(doc, objects, file_path)
        elif ext == '.obj':
            return self.export_obj(doc, objects, file_path)
        elif ext == '.usd':
            return self.export_usd(doc, objects, file_path)
        else:
            print(f"Unsupported file extension: {ext}")
            return None

    def export_fbx(self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], file_path: str) -> Optional[str]:
        doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

        plug = c4d.plugins.FindPlugin(c4d.FORMAT_FBX_EXPORT, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("FBX exporter not found")
            return None

        data = {}
        if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            print("Failed to retrieve FBX private data from plugin.")
            return None

        fbx_export = data.get("imexporter", None)
        if not fbx_export:
            print("FBX exporter interface not available in plugin data.")
            return None

        fbx_export[c4d.FBXEXPORT_SELECTION_ONLY] = True
        fbx_export[c4d.FBXEXPORT_ASCII] = False
        fbx_export[c4d.FBXEXPORT_SCALE] = 0.01

        if c4d.documents.SaveDocument(doc, file_path, c4d.SAVEDOCUMENTFLAGS_NONE, c4d.FORMAT_FBX_EXPORT):
            print(f"FBX exported: {file_path}")
            return file_path
        else:
            print("FBX export failed.")
            return None

    def export_abc(self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], file_path: str) -> Optional[str]:
        doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

        plug = c4d.plugins.FindPlugin(1028082, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("Alembic exporter not found")
            return None

        flags = c4d.SAVEDOCUMENTFLAGS_DIALOGSALLOWED | c4d.SAVEDOCUMENTFLAGS_SELECTIONONLY
        if c4d.documents.SaveDocument(doc, file_path, flags, c4d.FORMAT_ABCEXPORT):
            print(f"Alembic exported: {file_path}")
            return file_path
        else:
            print("Alembic export failed")
            return None

    def export_obj(self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], file_path: str) -> Optional[str]:
        # TODO: implement OBJ export
        print("OBJ export not implemented yet")
        return None

    def export_usd(self, doc: c4d.documents.BaseDocument, objects: list[c4d.BaseObject], file_path: str) -> Optional[str]:
        # TODO: implement USD export
        print("USD export not implemented yet")
        return None