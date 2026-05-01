"""
High-level scene operations for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from typing import Optional
from logging import Logger

import c4d
from src.jb_types import JbSource
from src.scene.jb_scene_file import JbSceneFile
from src.jb_utils import get_logger


class JbScene(JbSceneFile):
    """High-level import / export operations for the active C4D scene."""

    def __init__(self, source: JbSource):
        super().__init__()
        self._source = source
        self._logger = get_logger(__name__)

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def source(self) -> JbSource:
        """Return the active document."""
        if self._source is None:
            self._source = c4d.documents.GetActiveDocument()
        return self._source

    def import_with_temp(self, file_path, target) -> None:
        """Import file and place objects under container."""
        with self.temp_source(debug=False) as tmp_doc:
            if not self.import_file(file_path):
                self.logger.warning("No objects imported for file: %s", file_path)
                return
            self._project_scale(tmp_doc, 1)
            self._copy_source(tmp_doc, self.source, target)

    def export_with_temp(self, src, ext) -> Optional[str]:
        """Export objects to temp file, replacing instances with placeholders."""
        for obj in src:
            if obj.CheckType(c4d.Oinstance):
                linked = obj[c4d.INSTANCEOBJECT_LINK]
                if linked:
                    self.copy_asset_data(linked, obj)

        with self.temp_source(
            objects=src,
            unit_scale=c4d.DOCUMENT_UNIT_M,
            debug=False,
        ) as tmp_doc:
            self.replace_instances_with_placeholders(tmp_doc, self.get_objects(tmp_doc))
            tmp_doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            self._make_editable_recursive(tmp_doc.GetFirstObject(), tmp_doc)
            self._project_scale(tmp_doc, 0.01)
            return self.export_file(ext)
