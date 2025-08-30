import c4d


class JB_Helpers:
    def __init__(self):
        self.asset = JB_AssetHelper()
        self.structure = JB_StructureHelper()

class JB_AssetHelper:
    def __init__(self, doc = None):
        if not doc:
            doc = c4d.documents.GetActiveDocument()
        self.doc = doc

    def _get_asset_info(self, obj):
        if not obj:
            return None, None

        pack_name, asset_name = None, None

        containers = obj.GetUserDataContainer()
        if containers:
            for key, bc in containers:
                bc_name = bc[c4d.DESC_NAME]
                if bc_name == "pack_name":
                    pack_name = obj[key]
                elif bc_name == "asset_name":
                    asset_name = obj[key]

        return pack_name, asset_name

    def _validate_asset(self, obj):
        pack_name, asset_name = self._get_asset_info(obj)

        if asset_name and pack_name:
            return True
        
        return False

class JB_StructureHelper:
    def __init__(self, doc = None):
        if not doc:
            doc = c4d.documents.GetActiveDocument()
        self.doc = doc
        self.asset = JB_AssetHelper(doc)

    def walk(self, obj, fn):
        if obj is None:
            return

        if isinstance(obj, (list, tuple)):
            for o in obj:
                self.walk(o, fn)
            return
        
        fn(obj)
        child = obj.GetDown()
        while child:
            self.walk(child, fn)
            child = child.GetNext()

    def _is_asset(self, doc):
        selected_objects = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

        if (len(selected_objects) == 1 
            and selected_objects[0].CheckType(c4d.Onull)
            and self.asset._validate_asset(selected_objects[0])):
            return True, selected_objects
        else:
            return False, selected_objects

    def _get_or_create_null(self, name: str, color_type: str = None):
        obj_exists = True
        if color_type is None: color_type = name

        if color_type == "Assets":
            color = c4d.Vector(0.071, 0.949, 0.859)
        elif color_type == "Layout":
            color = c4d.Vector(0.949, 0.071, 0.859)
        else:
            color = c4d.Vector(0.5, 0.5, 0.5)

        obj = self.doc.SearchObject(name)
        if not obj:
            obj_exists = False
            obj = c4d.BaseObject(c4d.Onull)
            obj.SetName(name)
            self.doc.InsertObject(obj)
        
        obj[c4d.ID_BASELIST_ICON_FILE] = "12499"
        obj[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = c4d.ID_BASELIST_ICON_COLORIZE_MODE_CUSTOM
        obj[c4d.ID_BASELIST_ICON_COLOR] = color

        return obj, obj_exists
    
    def _get_or_create_asset(self, asset):
        def add_user_data(obj: c4d.BaseObject, name: str, default_value: str) -> None:
            containers = obj.GetUserDataContainer()
            if containers:
                for key, bc in containers:
                    bc_name = bc[c4d.DESC_NAME]
                    if bc_name == name:
                        obj[key] = default_value
                        return

            bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
            bc[c4d.DESC_NAME] = name
            bc[c4d.DESC_SHORT_NAME] = name
            bc[c4d.DESC_DEFAULT] = default_value

            element = obj.AddUserData(bc)
            if element:
                obj[element] = default_value

        root_null, _ = self._get_or_create_null(asset.type)

        asset_null, asset_exists = self._get_or_create_null(
            f"Asset_{asset.pack_name}_{asset.asset_name}", asset.type)

        asset_null.InsertUnder(root_null)

        add_user_data(asset_null, "asset_name", asset.asset_name)
        add_user_data(asset_null, "pack_name", asset.pack_name)

        if len(asset_null.GetChildren()) == 0:
            asset_exists = False

        return asset_null, asset_exists

    def _group_objects(
            self, 
            objects: list[c4d.BaseObject], 
            target: c4d.BaseObject):
        """Group objects under the target object."""
        for obj in objects:
            obj.InsertUnder(target)
            obj.SetBit(c4d.BIT_ACTIVE)

    def _get_objects(self, objects_mask = None):
        objects = []
        obj = self.doc.GetFirstObject()
        if objects_mask:
            while obj:
                if obj not in objects_mask:
                    objects.append(obj)
                obj = obj.GetNext()
        else:
            while obj:
                objects.append(obj)
                obj = obj.GetNext()

        return objects
