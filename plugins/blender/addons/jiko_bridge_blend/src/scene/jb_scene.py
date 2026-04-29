"""
Scene management for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import bpy
from .jb_material_importer import JBMaterialImporter
from .jb_scene_temp import JBSceneTemp
from ..jb_utils import get_logger

logger = get_logger(__name__)


class JbScene(JBSceneTemp, JBMaterialImporter):
    """High-level operations for the active Blender scene."""

    def import_with_temp(self, file_path: str, target: bpy.types.Collection) -> None:
        """Import file into temp scene, then copy to target collection."""
        with self.temp_scene(debug=False) as temp:
            if not self.import_file(file_path):
                logger.warning("No objects imported for file: %s", file_path)
                return
            root_objects = self.get_objects("top", temp.collection)
            if not root_objects:
                logger.warning("No root objects found in imported scene for file: %s", file_path)
                return
            self.copy_recursive(root_objects, target)

    def export_with_temp(
        self,
        src: bpy.types.Collection | list[bpy.types.Object],
        ext: str,
    ) -> Optional[str]:
        """Copy objects to isolated scene, replace instances, export."""
        with self.temp_scene(src, debug=False) as temp:
            col = temp.collection
            if not col or not col.objects:
                logger.warning("No objects to export.")
                return None
            copies = list(col.objects)
            self._replace_instances_with_placeholders(copies, temp)
            return self.export_file(ext)
