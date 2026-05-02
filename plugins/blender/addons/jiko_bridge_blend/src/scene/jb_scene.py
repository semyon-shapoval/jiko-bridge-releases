"""
Scene management for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from logging import Logger
from typing import Optional

import bpy
from ..jb_types import JbSource
from .jb_scene_temp import JBSceneTemp
from ..jb_utils import get_logger


class JbScene(JBSceneTemp):
    """High-level operations for the active Blender scene."""

    def __init__(self, source):
        super().__init__()
        self._logger = get_logger(__name__)
        self._source = source

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def source(self) -> JbSource:
        if self._source is not None:
            return self._source
        return bpy.context

    def import_with_temp(self, file_path, target) -> None:
        with self.temp_source(debug=False) as temp:
            if not self.import_file(file_path):
                self.logger.warning("No objects imported for file: %s", file_path)
                return
            self._copy_source(temp.collection, target)

    def export_with_temp(self, src, ext) -> Optional[str]:
        with self.temp_source(src, debug=True) as temp:
            col = temp.collection
            if not col or not col.objects:
                self.logger.warning("No objects to export.")
                return None
            copies = list(col.objects)
            self.replace_instances_with_placeholders(copies, temp)
            return self.export_file(ext)
