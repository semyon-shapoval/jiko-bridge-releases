"""
Selection helpers for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

import c4d
from src import get_logger, AssetInfo
from src.scene import JbSceneTree

logger = get_logger(__name__)


class JbSceneSelect(JbSceneTree):
    """Selection helpers for Cinema 4D.

    Inherits tree traversal from JbSceneTree and implements the selection
    group of JbSceneBase.
    """

    def get_selection(self):
        """Return the currently selected objects."""
        return self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

    def get_selection_mateials(self):
        """Return the currently selected materials."""
        return self.doc.GetActiveMaterials()

    def get_selected_asset_containers(self, objects: list[c4d.BaseObject]):
        """Return all selected asset nulls."""
        return [
            obj
            for obj in objects
            if obj.CheckType(c4d.Onull) and AssetInfo.from_user_data(obj)
        ]

    def get_selected_asset_container(self):
        """Return the single selected asset null, or None."""
        selected = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        if (
            len(selected) == 1
            and selected[0].CheckType(c4d.Onull)
            and AssetInfo.from_user_data(selected[0])
        ):
            return selected[0]
        return None
