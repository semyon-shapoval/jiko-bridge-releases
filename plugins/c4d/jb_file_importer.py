import c4d

class JBFileImporter:
    def import_file(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        ext = self._get_ext(file_path)
        if ext == '.fbx':
            return self._import_fbx(doc, file_path)
        elif ext == '.abc':
            return self._import_alembic(doc, file_path)
        elif ext == '.obj':
            return self._import_obj(doc, file_path)
        elif ext == '.usd':
            return self._import_usd(doc, file_path)
        else:
            print(f"Unsupported file extension: {ext}")
            return False

    def _get_ext(self, file_path: str) -> str:
        from pathlib import Path
        return Path(file_path).suffix.lower()

    def _import_fbx(self, doc, file_path):
        plug = c4d.plugins.FindPlugin(1026370, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("FBX plugin not found")
            return False

        data = {}
        if plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            fbx_import = data.get("imexporter", None)
            if fbx_import:
                fbx_import[c4d.FBXEXPORT_CAMERAS] = True
                fbx_import[c4d.FBXEXPORT_LIGHTS] = True
                fbx_import[c4d.FBXEXPORT_MATERIALS] = True

        result = c4d.documents.MergeDocument(doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)
        if not result:
            print(f"Error importing FBX file: {file_path}")
        return result

    def _import_alembic(self, doc, file_path):
        plug = c4d.plugins.FindPlugin(1028082, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("Alembic plugin not found")
            return False

        result = c4d.documents.MergeDocument(doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)
        if not result:
            print(f"Error importing Alembic file: {file_path}")
        return result

    def _import_obj(self, doc, file_path):
        plug = c4d.plugins.FindPlugin(1030177, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("OBJ plugin not found")
            return False

        result = c4d.documents.MergeDocument(doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)
        if not result:
            print(f"Error importing OBJ file: {file_path}")
        return result

    def _import_usd(self, doc, file_path):
        plug = c4d.plugins.FindPlugin(1055178, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("USD plugin not found")
            return False

        result = c4d.documents.MergeDocument(doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)
        if not result:
            print(f"Error importing USD file: {file_path}")
        return result