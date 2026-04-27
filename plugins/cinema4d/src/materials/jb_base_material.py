"""
Base class for material
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import c4d
import maxon


class JbBaseMaterial:
    """Base material class."""

    def nodespace_id(self) -> Optional[str]:
        """Returns the node space ID for this material type, or None if not applicable."""
        raise NotImplementedError

    def create(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
    ) -> c4d.BaseMaterial:
        """Create a new material."""
        raise NotImplementedError

    def apply_channel(self, material: c4d.BaseMaterial, channel: str, path: str) -> None:
        """Apply a texture channel to the material."""
        raise NotImplementedError

    def build_graph(self, material: c4d.BaseMaterial):
        """Rebuild the material's node graph."""
        space = self.nodespace_id()

        if space is None:
            return material

        node_mat = material.GetNodeMaterialReference()
        if node_mat is None:
            return material

        if not node_mat.HasSpace(maxon.Id(space)):
            node_mat.AddGraph(maxon.Id(space))

        return material
