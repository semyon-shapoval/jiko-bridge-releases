import c4d

from jb_api import JB_API
from jb_helper import JB_Helpers
from jb_file_exporter import JBFileExporter


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.helpers = JB_Helpers()
        self.file_exporter = JBFileExporter()
        self.doc = c4d.documents.GetActiveDocument()

    def export_asset(self):
        selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

        if (len(selected_objects) == 1
            and selected_objects[0].CheckType(c4d.Onull)
            and self.helpers.asset._validate_asset(selected_objects[0])):
            return self.update_asset(selected_objects[0])

        return self.prepare_asset(selected_objects)

    def update_asset(self, obj: c4d.BaseObject):
        pack_name, asset_name, asset_type = self.helpers.asset._get_asset_info(obj)
        if not pack_name or not asset_name or not asset_type:
            print(f"Invalid asset information: {pack_name}, {asset_name}, {asset_type}")
            return None

        objects = []
        self.helpers.structure.walk(obj, lambda x: objects.append(x))
        if objects and objects[0] is obj:
            objects.pop(0)

        ext = self._detect_ext(objects)
        filepath = self.file_exporter.export_file(self.doc, objects, ext)

        if filepath:
            success = self.api.update_asset(filepath, pack_name, asset_name)
            print(f"Asset {asset_name} updated successfully." if success else f"Failed {asset_name} to update asset.")

    def prepare_asset(self, objects: list[c4d.BaseObject]):
        ext = self._detect_ext(objects)
        filepath = self.file_exporter.export_file(self.doc, objects, ext)

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

    def _detect_ext(self, objects: list[c4d.BaseObject]) -> str:
        for obj in objects:
            if obj.CheckType(c4d.Oinstance):
                return '.abc'
        return '.fbx'