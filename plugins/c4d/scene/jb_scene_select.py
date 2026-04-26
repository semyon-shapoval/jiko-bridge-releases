import c4d
from typing import Optional

from jb_logger import get_logger

from jb_asset_model import AssetInfo
from scene.jb_scene_tree import JBTree

logger = get_logger(__name__)


class JBSceneSelect(JBTree):
    """Selection helpers for Cinema 4D.

    Inherits tree traversal from JBTree and implements the selection
    group of JBSceneBase.
    """

    def get_selection(self) -> list:
        """Return the currently selected objects."""
        return self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
    
    def get_selection_mateials(self) -> list:
        """Return the currently selected materials."""
        return self.doc.GetActiveMaterials()

    def get_selected_asset_containers(self, objects: list) -> list:
        """Return all selected asset nulls."""
        return [
            obj
            for obj in objects
            if obj.CheckType(c4d.Onull) and AssetInfo.get_asset_info(obj)
        ]

    def get_selected_asset_container(self) -> Optional[c4d.BaseObject]:
        """Return the single selected asset null, or None."""
        selected = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        if (
            len(selected) == 1
            and selected[0].CheckType(c4d.Onull)
            and AssetInfo.get_asset_info(selected[0])
        ):
            return selected[0]
        return None
