import c4d
import os

from typing import Optional


class C4DSceneHelper:
    def __init__(self):
        self.doc = c4d.documents.GetActiveDocument()

    def create_scene_object(
        self, name: str, parent: c4d.BaseObject | None = None
    ) -> c4d.BaseObject:
        obj = c4d.BaseObject(c4d.Ocube)
        obj.SetName(name)
        if parent is not None:
            obj.InsertUnder(parent)
        else:
            self.doc.InsertObject(obj)
        obj.SetBit(c4d.BIT_ACTIVE)
        c4d.EventAdd()
        return obj

    def find_object_by_name(self, name: str) -> Optional[c4d.BaseObject]:
        return self.doc.SearchObject(name)

    def activate_object(self, obj: c4d.BaseObject) -> None:
        self.clear_selection()
        self.doc.SetActiveObject(obj, c4d.SELECTION_NEW)
        obj.SetBit(c4d.BIT_ACTIVE)
        c4d.EventAdd()

    def select_objects(self, objects: list[c4d.BaseObject]) -> None:
        if not objects:
            return

        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)
            self.doc.SetActiveObject(obj, c4d.SELECTION_ADD)
        c4d.EventAdd()

    def clear_selection(self) -> None:
        active = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        for obj in active:
            obj.DelBit(c4d.BIT_ACTIVE)
        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        c4d.EventAdd()

    def get_hierarchy(self, container: c4d.BaseObject) -> dict[str, str | None]:
        result: dict[str, str | None] = {}
        for obj in container.GetChildren():
            parent = obj.GetUp()
            result[obj.GetName()] = parent.GetName() if parent else None
        return result

    def normalize_hierarchy(
        self, hierarchy: dict[str, str | None]
    ) -> dict[str, str | None]:
        def normalize_name(name: str | None) -> str | None:
            if name is None:
                return None
            return name.split(".", 1)[0]

        return {
            normalize_name(name): normalize_name(parent)
            for name, parent in hierarchy.items()
        }

    def get_instance_objects(self) -> list[c4d.BaseObject]:
        result: list[c4d.BaseObject] = []
        obj = self.doc.GetFirstObject()
        while obj:
            if obj.CheckType(c4d.Oinstance):
                result.append(obj)
            obj = obj.GetNext()
        return result

    def save_document(self, filename: str) -> Optional[str]:
        current_doc = c4d.documents.GetActiveDocument()
        if current_doc is None:
            return

        logs_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        )
        os.makedirs(logs_dir, exist_ok=True)

        if not filename.lower().endswith(".c4d"):
            filename = f"{filename}.c4d"

        path = os.path.normpath(os.path.join(logs_dir, filename))

        result = c4d.documents.SaveDocument(
            current_doc,
            path,
            c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,
            c4d.FORMAT_C4DEXPORT,
        )

        if not result:
            return None

        return path

    def reset_scene(self) -> None:
        current = c4d.documents.GetActiveDocument()
        if current is not None:
            c4d.documents.KillDocument(current)
        new_doc = c4d.documents.BaseDocument()
        c4d.documents.InsertBaseDocument(new_doc)
        c4d.documents.SetActiveDocument(new_doc)
        self.doc = new_doc
        c4d.EventAdd()
