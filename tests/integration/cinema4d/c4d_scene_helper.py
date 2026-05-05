"""
Helper class for managing Cinema 4D scenes during integration tests.
Code by Semyon Shapoval, 2026
"""

import os
import importlib
from typing import Optional

import c4d


class C4DSceneHelper:
    """Utility class for Cinema 4D scenes in tests."""

    JIKO_BRIDGE_ID = 1096086

    def __init__(self):
        self.doc = c4d.documents.GetActiveDocument()

    @property
    def source(self) -> c4d.documents.BaseDocument:
        """Return the current Cinema 4D document."""
        return self.doc

    def import_module(self, module_name: str):
        """Import a module from the Jiko Bridge addon."""
        return importlib.import_module(module_name)

    def call_command(self, operator: str):
        """Call a Jiko Bridge command by name."""
        try:
            ops = importlib.import_module("src.jb_commands")
        except ImportError as e:
            raise RuntimeError("jiko_bridge operator should be registered") from e
        commands = getattr(ops, "JbCommands")(self.source)
        if not hasattr(commands, operator):
            raise RuntimeError(f"Operator {operator} should be defined in JbCommands")
        result = getattr(commands, operator)()
        return result

    def ensure_loaded(self) -> None:
        """Check if the Jiko Bridge plugin is loaded in Cinema 4D."""
        plugin = c4d.plugins.FindPlugin(self.JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND)
        if plugin is None:
            raise RuntimeError("Jiko Bridge plugin is not loaded in Cinema 4D.")

    def create_scene_object(
        self, name: str, parent: c4d.BaseObject | None = None
    ) -> c4d.BaseObject:
        """Create a new scene object with the given name and optional parent."""
        obj = c4d.BaseObject(c4d.Ocube)
        obj.SetName(name)
        if parent is not None:
            obj.InsertUnder(parent)
        else:
            self.doc.InsertObject(obj)
        obj.SetBit(c4d.BIT_ACTIVE)
        c4d.EventAdd()
        return obj

    def find_container_by_name(self, name: str) -> Optional[c4d.BaseObject]:
        """Find a container object in the scene by its name."""
        return self.doc.SearchObject(name)

    def select_objects(self, objects: list[c4d.BaseObject]) -> None:
        """Select the given list of objects in the scene."""
        self.clear_selection()

        if not objects:
            return

        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

        c4d.EventAdd()

    def clear_selection(self) -> None:
        """Clear the current selection in the scene."""
        active = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        for obj in active:
            obj.DelBit(c4d.BIT_ACTIVE)
        self.doc.SetActiveObject(None, c4d.SELECTION_NEW)
        c4d.EventAdd()

    def get_hierarchy(self, container: c4d.BaseObject) -> dict[str, str | None]:
        """Return a dictionary mapping object names to their parent names."""
        result: dict[str, str | None] = {}

        def normalize_name(name: str) -> str:
            return name.split(".", 1)[0]

        for obj in container.GetChildren():
            parent = obj.GetUp()
            norm_name = normalize_name(obj.GetName())
            norm_parent = normalize_name(parent.GetName()) if parent else None
            result[norm_name] = norm_parent
        return result

    def get_instance_objects(self) -> list[c4d.BaseObject]:
        """Return a list of all instance objects in the scene."""
        result: list[c4d.BaseObject] = []
        obj = self.doc.GetFirstObject()
        while obj:
            if obj.CheckType(c4d.Oinstance):
                result.append(obj)
            obj = obj.GetNext()
        return result

    def save_document(self, filename: str) -> Optional[str]:
        """Save the current document."""
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(logs_dir, exist_ok=True)

        if not filename.lower().endswith(".c4d"):
            filename = f"{filename}.c4d"

        path = os.path.normpath(os.path.join(logs_dir, filename))

        result = c4d.documents.SaveDocument(
            self.source,
            path,
            c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,
            c4d.FORMAT_C4DEXPORT,
        )

        if not result:
            return None

        return path

    # pylint: disable=duplicate-code
    def find_material_by_name(self, name: str) -> Optional[c4d.BaseMaterial]:
        """Find a material in the scene by its name."""
        mat = self.source.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None

    def apply_material_to_object(self, obj: c4d.BaseObject, material: c4d.BaseMaterial) -> bool:
        """Apply the given material to the specified object."""
        tag = c4d.BaseTag(c4d.Ttexture)
        tag[c4d.TEXTURETAG_MATERIAL] = material
        obj.InsertTag(tag)
        c4d.EventAdd()
        return True

    def reset_scene(self) -> None:
        """Reset the scene by closing the current document and creating a new one."""
        current = c4d.documents.GetActiveDocument()
        if current is not None:
            c4d.documents.KillDocument(current)
        new_doc = c4d.documents.BaseDocument()
        c4d.documents.InsertBaseDocument(new_doc)
        c4d.documents.SetActiveDocument(new_doc)
        self.doc = new_doc
        c4d.EventAdd()
