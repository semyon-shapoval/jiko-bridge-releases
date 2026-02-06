import re
import c4d

from jb_api import JB_API
from jb_helper import JB_Helpers
from jb_material_importer import JBMaterialImporter

class JB_AssetImporter:
    def __init__(self):
        self.api = JB_API()
        self.helpers = JB_Helpers()
        self.material_import = JBMaterialImporter()

        self.doc = c4d.documents.GetActiveDocument()

    def import_asset(self, asset = None) -> bool:
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
        
        if asset.asset_type == "MODEL":
            return self._create_model(asset)
        elif asset.asset_type == "MATERIAL":
            return self.material_import.import_material(asset)

    def _override_model(self, obj):
        pack_name, asset_name = self.helpers.asset._get_asset_info(obj)
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
        

    def _create_model(self, asset):
        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        asset_null, asset_exists = self.helpers.structure._get_or_create_asset(asset)
        objects_before = self.helpers.structure._get_objects()
        
        if not asset_null:
            print("Failed to create asset null")
            return False

        if asset_exists:
            return self._create_instance(self.doc, asset_null, asset.asset_name)

        ext = asset.ext

        if ext == '.fbx':
            result = self._import_fbx(self.doc, asset.asset_path)
        elif ext == '.abc':
            result = self._import_alembic(self.doc, asset.asset_path)
        else:
            return False


        if result:
            new_objects = self.helpers.structure._get_objects(objects_before)

            if ext == ".abc":
                self._convert_layout(self.doc, new_objects, asset_null)
            elif ext == '.fbx':
                self.helpers.structure._group_objects(new_objects, asset_null)

        return True

    def _create_instance(
            self, 
            doc: c4d.documents.BaseDocument, 
            link: c4d.BaseObject, 
            name: str
        ) -> c4d.BaseObject:
        """Create an instance of the asset null object."""
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = link
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1

        doc.InsertObject(instance)
        instance.SetBit(c4d.BIT_ACTIVE)

        layout_null, _ = self.helpers.structure._get_or_create_null("Layout")
        instance.InsertUnder(layout_null)

        return instance

    def _convert_layout(self, doc, new_objects, layout_null):
        objs = []
        self.helpers.structure.walk(new_objects, lambda x: objs.append(x))

        doc.SetActiveObject(None, c4d.SELECTION_NEW)

        for obj in objs: obj.SetBit(c4d.BIT_ACTIVE)
        c4d.CallCommand(12236)

        pattern = re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$")

        assets = {}
        for obj in objs:
            tag = None

            if obj.CheckType(c4d.Opolygon):
                for tag in obj.GetTags():
                    if tag.CheckType(c4d.Tpolygonselection):
                        tag = tag
                        break

            if tag:
                tag_name = tag.GetName()
                match = pattern.match(tag_name)
                if match:
                    pack_name = match.group("pack")
                    asset_name = match.group("asset")
                    key = f"{pack_name}/{asset_name}"
                    if key not in assets:
                        assets[key] = self.api.get_asset(pack_name, asset_name)

                    asset = assets[key]

                    asset_null, asset_exists = self.helpers.structure._get_or_create_asset(asset)
                    instance = self._create_instance(doc, asset_null, asset.asset_name)
                    mg = obj.GetUp().GetMg()
                    instance.SetMg(mg)
                    instance.InsertUnder(layout_null)
            
        for obj in reversed(objs):
            obj.InsertUnder(doc)
            obj.Remove()

        for key, asset in assets.items():
            self.import_asset(asset)

    
    def _import_fbx(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        """Import FBX file"""
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
        
        if result:
            return True
        else:
            print(f"Error importing FBX file: {file_path}")
            return False
    
    def _import_alembic(self, doc: c4d.documents.BaseDocument, file_path: str) -> bool:
        """Import Alembic file""" 
        plug = c4d.plugins.FindPlugin(1028082, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            print("Alembic plugin not found")
            return False
        
        result = c4d.documents.MergeDocument(doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS)
        
        if result:
            return True
        else:
            print(f"Error importing Alembic file: {file_path}")
            return False
