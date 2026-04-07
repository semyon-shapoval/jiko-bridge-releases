import bpy
from typing import Optional

from .jb_scene_asset import JBSceneAsset
from .jb_logger import get_logger

# TODO: Port C4D scene utilities from plugins/c4d/jb_scene_manager.py
# - support recursive editable conversion / modifier application like C4D make_editable_recursive
# - preserve instance and placeholder cleanup semantics for nested hierarchies

logger = get_logger(__name__)


class JBSceneManager(JBSceneAsset):
    """High-level import / export operations for the active Blender scene."""

    def import_file_to_container(self, file_path: str, container) -> None:
        """Unified API: import file and place objects into collection."""
        objects = self.import_file(file_path)
        if not objects:
            logger.warning("No objects imported for file: %s", file_path)
            return
        self.move_objects_to_container(objects, container)

    def export_to_temp_file(self, objects: list, ext: str) -> Optional[str]:
        """Unified API: copy objects to isolated scene, replace instances, export."""
        with self.isolated_container(objects) as temp:
            copies = list(temp.collection.objects)
            self._replace_instances_with_placeholders(copies, temp)
            return self.export_file(ext)
