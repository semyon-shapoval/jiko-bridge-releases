"""
Scene tree traversal and querying.
Code by Semyon Shapoval, 2026
"""

import c4d

from src.jb_protocols import JbSceneABC
from src.jb_types import JbData, JbObject, JbMaterial


class JbSceneObjects(JbSceneABC):
    """Traversal and querying of Cinema 4D object hierarchies."""

    def get_selection(self, select_type="objects") -> list[JbObject | JbMaterial]:
        if select_type == "objects":
            return self.source.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        if select_type == "materials":
            return self.source.GetActiveMaterials()
        return []

    def walk(self, root) -> list[JbData]:
        if not root:
            return []
        return list(self._walk(root))

    def _walk(self, root):
        if root is None:
            return

        if isinstance(root, (list, tuple)):
            for o in root:
                yield from self._walk(o)
            return

        yield root
        child = root.GetDown()
        while child:
            yield from self._walk(child)
            child = child.GetNext()

    def get_materials_from_objects(self, objects) -> list[JbMaterial]:
        materials = []

        for obj in objects:
            if not obj.IsInstanceOf(c4d.Opolygon):
                continue

            for tag in obj.GetTags():
                if not tag.CheckType(c4d.Ttexture):
                    continue

                material = tag[c4d.TEXTURETAG_MATERIAL]
                if material:
                    materials.append(material)

        return materials

    def copy_object_transform(self, obj, target_obj) -> None:
        obj.SetMg(target_obj.GetMg())

    def remove_object(self, obj) -> None:
        obj.Remove()

    def _set_protection_tag(self, obj: c4d.BaseObject) -> None:
        if obj is None:
            return

        if obj.GetTags() is not None:
            for tag in obj.GetTags():
                try:
                    if tag.GetType() == c4d.Tprotection:
                        return
                except (AttributeError, TypeError):
                    continue

        try:
            protection_tag = c4d.BaseTag(c4d.Tprotection)
            if protection_tag is not None:
                obj.InsertTag(protection_tag)
        except (AttributeError, TypeError):
            pass

    def _set_user_data(
        self,
        obj: c4d.BaseObject,
        name: str,
        value: str | None,
    ) -> None:
        if value is None:
            value = ""

        for key, bc in obj.GetUserDataContainer() or []:
            if bc[c4d.DESC_NAME] == name:
                obj[key] = value
                return

        bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_SHORT_NAME] = name
        bc[c4d.DESC_DEFAULT] = value

        element = obj.AddUserData(bc)
        if element is not None:
            obj[element] = value
