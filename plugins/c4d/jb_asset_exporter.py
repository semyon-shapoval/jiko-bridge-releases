from genericpath import exists
import c4d
import time
import os

from jb_api import JB_API
from jb_helper import JB_Helpers


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.helpers = JB_Helpers()
        self.doc = c4d.documents.GetActiveDocument()
        self.cache_path = self._get_cache_path()

    def export_asset(self):
        selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

        if (len(selected_objects) == 1 
            and selected_objects[0].CheckType(c4d.Onull)
            and self.helpers.asset._validate_asset(selected_objects[0])):
            return self.update_asset(selected_objects[0])

        return self.prepare_asset(selected_objects)
    
    def _get_cache_path(self):
        server = self.api.get_server_data()
        if server:
            try:
                os.makedirs(server.cache_path, exist_ok=True)
            except Exception as e:
                print("Cannot create cache path:", server.cache_path, e)
                return None
            return server.cache_path
        return None

    def update_asset(self, obj):
        
        pack_name, asset_name = self.helpers.asset._get_asset_info(obj)
        if not pack_name or not asset_name:
            print(f"Invalid asset information: {pack_name}, {asset_name}")
            return None
        
        type = "Asset"
        objects = []
        self.helpers.structure.walk(obj, lambda x: objects.append(x))

        if objects and objects[0] is obj:
            objects.pop(0)

        for obj in objects:
            if obj.CheckType(c4d.Oinstance):
                type = "Layout"

        if type == "Asset":
            filepath = self._export_fbx(objects)
        elif type == "Layout":
            filepath = self._export_abc(objects)

        if filepath:
            success = self.api.update_asset(filepath, pack_name, asset_name)
            print(f"Asset {asset_name} updated successfully." if success else f"Failed {asset_name} to update asset.")

    def prepare_asset(self, objects):
        type = "Asset"
        for obj in objects:
            if obj.CheckType(c4d.Oinstance):
                type = "Layout"

        if type == "Asset":
            filepath = self._export_fbx(objects)
        elif type == "Layout":
            filepath = self._export_abc(objects)

        if filepath:
            asset = self.api.create_asset(filepath)
            root, root_exists = self.helpers.structure._get_or_create_asset(asset)
            self.helpers.structure._group_objects(objects, root)

    def _export_fbx(self, objects):
        fbx_filename = f"bridge_{int(time.time())}.fbx"
        if not self.cache_path:
            print("Cache path not found.")
            return None
        
        fbx_path = os.path.join(self.cache_path, fbx_filename)

        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

        plug = c4d.plugins.FindPlugin(c4d.FORMAT_FBX_EXPORT, c4d.PLUGINTYPE_SCENESAVER)

        data = {}
        if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            print("Failed to retrieve FBX private data from plugin.")
            print("Plugin data keys:", list(data.keys()))
            return None
        
        fbx_export = data.get("imexporter", None)
        if not fbx_export:
            print("FBX exporter interface not available in plugin data.")

        fbx_export[c4d.FBXEXPORT_SELECTION_ONLY] = True
        fbx_export[c4d.FBXEXPORT_ASCII] = False
        fbx_export[c4d.FBXEXPORT_SCALE] = 0.01

        if c4d.documents.SaveDocument(
            self.doc,
            fbx_path,
            c4d.SAVEDOCUMENTFLAGS_NONE,
            c4d.FORMAT_FBX_EXPORT,
        ):
            print(f"FBX exported: {fbx_path}")
            return fbx_path
        else:
            print("FBX export failed.")
            return None

    def _export_abc(self, objects):
        print("Exporting ABC:", objects)