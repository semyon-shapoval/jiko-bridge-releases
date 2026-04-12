import c4d
from typing import Optional

from jb_logger import get_logger

from scene.jb_scene_container import JBSceneContainer

logger = get_logger(__name__)


class JBScene(JBSceneContainer):
    """High-level import / export operations for the active C4D scene."""

    def import_with_temp(self, file_path: str, target: c4d.BaseObject) -> None:
        """Unified API: import file and place objects under container."""
        with self.temp_context(debug=False) as tmp_doc:
            if not self.import_file(tmp_doc, file_path):
                logger.warning("No objects imported for file: %s", file_path)
                return
            self.project_scale(tmp_doc, 1)
            self.copy_context(tmp_doc, self.doc, target)

    def export_with_temp(self, objects: list, ext: str) -> Optional[str]:
        """Unified API: export objects to temp file, replacing instances with placeholders."""
        for obj in objects:
            if obj.CheckType(c4d.Oinstance):
                linked = obj[c4d.INSTANCEOBJECT_LINK]
                if linked:
                    self.copy_user_data(linked, obj)

        with self.temp_context(
            doc=self.doc, objects=objects, unit_scale=c4d.DOCUMENT_UNIT_M, debug=False
        ) as tmp_doc:
            if tmp_doc is None:
                return None
            self._replace_instances_with_placeholders(
                tmp_doc, self.get_all_objects(tmp_doc)
            )
            tmp_doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            self.make_editable_recursive(tmp_doc.GetFirstObject(), tmp_doc)
            self.project_scale(tmp_doc, 0.01)
            return self.export_file(tmp_doc, ext)
