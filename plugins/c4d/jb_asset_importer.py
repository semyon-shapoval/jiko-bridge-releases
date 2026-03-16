import re
import c4d

from jb_helper import JB_Helpers
from jb_api import JB_API, AssetModel
from jb_material_importer import JBMaterialImporter
from jb_file_importer import JBFileImporter

class JB_AssetImporter:
    def __init__(self):
        self.api = JB_API()
        self.helpers = JB_Helpers()
        self.material_import = JBMaterialImporter()
        self.file_importer = JBFileImporter()

        self.doc = c4d.documents.GetActiveDocument()

    def import_asset(self, asset: AssetModel = None) -> bool:
        if not asset:
            selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
            override = False

            for obj in selected_objects:
                if (obj.CheckType(c4d.Onull)
                    and self.helpers.asset._validate_asset(obj)):
                    asset = self._override_model(obj)
                    override = True

            if not override:
                return self._import_active_asset()

            return True

        return self._create_model(asset)

    def _import_active_asset(self):
        asset = self.api.get_active_asset()

        if not asset:
            return c4d.gui.MessageDialog("Could not get active asset")

        if asset.bridge_type == "model":
            return self._create_model(asset)
        elif asset.bridge_type == "material":
            return self.material_import.import_material(asset)
        else:
            return c4d.gui.MessageDialog(f"Unsupported bridge type: {asset.bridge_type}")

    def _override_model(self, obj):
        pack_name, asset_name, asset_type = self.helpers.asset._get_asset_info(obj)
        asset = self.api.get_asset(pack_name, asset_name)

        if not asset:
            return None

        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        objects = []
        self.helpers.structure.walk(obj, lambda x: objects.append(x))

        for obj in objects:
            obj.Remove()

        self._create_model(asset)
        return asset

    def _create_model(self, asset: AssetModel) -> bool:
        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        asset_null, asset_exists = self.helpers.structure._get_or_create_asset(asset)
        objects_before = self.helpers.structure._get_objects()

        if not asset_null:
            print("Failed to create asset null")
            return False

        if asset_exists:
            self._create_instance(self.doc, asset_null, asset.asset_name)
            return True

        result = self.file_importer.import_file(self.doc, asset.asset_path)

        if result:
            new_objects = self.helpers.structure._get_objects(objects_before)
            self.helpers.structure._group_objects(new_objects, asset_null)
            
            if asset.bridge_type == "layout":
                self._convert_layout(self.doc, asset_null)

        return True

    def _create_instance(self, doc, link, name, parent=None):
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = link
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1

        doc.InsertObject(instance)
        instance.SetBit(c4d.BIT_ACTIVE)

        if parent:
            instance.InsertUnder(parent)

        return instance

    def _convert_layout(self, doc: c4d.documents.BaseDocument, layout_null: c4d.BaseObject):
        objs = []
        self.helpers.structure.walk(layout_null, lambda x: objs.append(x))

        doc.SetActiveObject(None, c4d.SELECTION_NEW)
        for obj in objs:
            obj.SetBit(c4d.BIT_ACTIVE)
        c4d.CallCommand(12236)

        pattern = re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$")

        assets = {}
        for obj in objs:
            if not obj.CheckType(c4d.Opolygon):
                continue

            tag = None
            for t in obj.GetTags():
                if t.CheckType(c4d.Tpolygonselection):
                    tag = t
                    break

            if not tag:
                continue

            tag_name = tag.GetName()
            match = pattern.match(tag_name)
            if not match:
                continue

            pack_name = match.group("pack")
            asset_name = match.group("asset")
            key = f"{pack_name}/{asset_name}"

            if key not in assets:
                assets[key] = self.api.get_asset(pack_name, asset_name)

            asset = assets[key]
            asset_null, _ = self.helpers.structure._get_or_create_asset(asset)
            instance = self._create_instance(doc, asset_null, asset.asset_name)
            mg = obj.GetUp().GetMg()
            instance.SetMg(mg)
            instance.InsertUnder(layout_null)

            obj.Remove()

        for key, asset in assets.items():
            self.import_asset(asset)