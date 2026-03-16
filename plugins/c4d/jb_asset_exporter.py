import c4d
import time
import os
import tempfile

from jb_api import JB_API
from jb_helper import JB_Helpers

class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.helpers = JB_Helpers()
        self.doc = c4d.documents.GetActiveDocument()
        base = os.path.join(tempfile.gettempdir(), 'jiko-bridge')
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    def export_asset(self):
        selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

        if (len(selected_objects) == 1 
            and selected_objects[0].CheckType(c4d.Onull)
            and self.helpers.asset._validate_asset(selected_objects[0])):
            return self.update_asset(selected_objects[0])

        return self.prepare_asset(selected_objects)
    

    def update_asset(self, obj):
        
        pack_name, asset_name, asset_type = self.helpers.asset._get_asset_info(obj)
        if not pack_name or not asset_name or not asset_type:
            print(f"Invalid asset information: {pack_name}, {asset_name}, {asset_type}")
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
            c4d.StatusSetText("Jiko Bridge: creating asset, please wait...")
            c4d.StatusSetBar(0) 
            c4d.gui.SetMousePointer(c4d.MOUSE_BUSY)
            
            try:
                asset = self.api.create_asset(filepath)
            finally:
                c4d.gui.SetMousePointer(c4d.MOUSE_NORMAL)
                c4d.StatusClear()

            if not asset:
                print(f"Failed to create asset for '{filepath}' (create_asset returned None).")
                return None

            root, root_exists = self.helpers.structure._get_or_create_asset(asset)
            if root is None:
                print(f"Failed to create or find root object for asset: {asset}")
                return None

            self.helpers.structure._group_objects(objects, root)

    def _export_fbx(self, objects):
        fbx_filename = f"bridge_{int(time.time())}.fbx"
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
            return None
        
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
        abc_filename = f"bridge_{int(time.time())}.abc"
        abc_path = os.path.join(self.cache_path, abc_filename)

        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

        plug = c4d.plugins.FindPlugin(1028082, c4d.PLUGINTYPE_SCENESAVER)  # Alembic
        if not plug:
            print("Alembic exporter not found")
            return None

        flags = c4d.SAVEDOCUMENTFLAGS_DIALOGSALLOWED | c4d.SAVEDOCUMENTFLAGS_SELECTIONONLY
        if c4d.documents.SaveDocument(self.doc, abc_path, flags, c4d.FORMAT_ABCEXPORT):
            print(f"Alembic exported: {abc_path}")
            return abc_path
        else:
            print("Alembic export failed")
            return None