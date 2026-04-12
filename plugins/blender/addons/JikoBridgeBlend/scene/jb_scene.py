import bpy

from typing import Optional

from .jb_scene_container import JBSceneContainer
from ..jb_logger import get_logger

# TODO: Port C4D scene utilities from plugins/c4d/jb_scene_manager.py
# - support recursive editable conversion / modifier application like C4D make_editable_recursive
# - preserve instance and placeholder cleanup semantics for nested hierarchies

logger = get_logger(__name__)


class JBScene(JBSceneContainer):
    """High-level import / export operations for the active Blender scene."""

    def import_with_temp(self, file_path: str, target: bpy.types.Collection) -> None:
        """Unified API: import file into temp scene, then copy to target collection."""
        with self.temp_scene(debug=False) as temp:
            if not self.import_file(file_path):
                logger.warning("No objects imported for file: %s", file_path)
                return
            root_objects = self.get_top_objects(temp)
            if not root_objects:
                logger.warning(
                    "No root objects found in imported scene for file: %s", file_path
                )
                return
            self.copy_recursive(root_objects, target)

    def export_with_temp(
        self,
        src: bpy.types.Collection | list[bpy.types.Object],
        ext: str,
    ) -> Optional[str]:
        """Unified API: copy objects to isolated scene, replace instances, export."""
        with self.temp_scene(src, debug=False) as temp:
            copies = list(temp.collection.objects)
            self._replace_instances_with_placeholders(copies, temp)
            return self.export_file(ext)
