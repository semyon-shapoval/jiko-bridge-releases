import c4d
from typing import Optional

from jb_logger import get_logger
from jb_utils import confirm as _confirm

from jb_asset_model import AssetModel
from scene.jb_scene_tree import JBTree

logger = get_logger(__name__)


class JBSceneSelect(JBTree):
    """Selection helpers for Cinema 4D.

    Inherits tree traversal from JBTree and implements the selection
    group of JBSceneBase.
    """

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        return c4d.documents.GetActiveDocument()

    def get_selection(self) -> list:
        """Return the currently selected objects."""
        return self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)

    def get_selected_asset_containers(self) -> list:
        """Return all selected asset nulls."""
        return [
            obj
            for obj in self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
            if obj.CheckType(c4d.Onull) and AssetModel.from_c4d_object(obj)
        ]

    def get_selected_asset_container(self) -> Optional[c4d.BaseObject]:
        """Return the single selected asset null, or None."""
        selected = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        if (
            len(selected) == 1
            and selected[0].CheckType(c4d.Onull)
            and AssetModel.from_c4d_object(selected[0])
        ):
            return selected[0]
        return None

    def confirm(self, message: str) -> bool:
        """Show a C4D confirmation dialog."""
        return _confirm(message)
