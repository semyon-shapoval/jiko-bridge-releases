"""
High-level scene operations for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

from typing import Optional

import c4d
from src.scene.jb_material_importer import JbMaterialImporter
from src.scene.jb_scene_temp import JbSceneTemp
from src.jb_utils import get_logger

logger = get_logger(__name__)


class JbScene(JbSceneTemp, JbMaterialImporter):
    """High-level import / export operations for the active C4D scene."""

    def get_materials_from_objects(self, objects: list[c4d.BaseObject]):
        """Extracts materials from the given objects by looking for texture tags."""
        materials = []

        for obj in objects:
            if not obj.IsInstanceOf(c4d.Opolygon):
                continue

            for tag in obj.GetTags():
                if not tag.CheckType(c4d.Ttexture):
                    continue

                material = tag[c4d.TEXTURETAG_MATERIAL]
                if material:
                    materials.append(material)

        return materials

    def import_with_temp(self, file_path: str, target: c4d.BaseObject) -> None:
        """Import file and place objects under container."""
        with self.temp_context(debug=False) as tmp_doc:
            if not self.import_file(tmp_doc, file_path):
                logger.warning("No objects imported for file: %s", file_path)
                return
            self.project_scale(tmp_doc, 1)
            self.copy_context(tmp_doc, self.source, target)

    def export_with_temp(self, objects: list, ext: str) -> Optional[str]:
        """Export objects to temp file, replacing instances with placeholders."""
        for obj in objects:
            if obj.CheckType(c4d.Oinstance):
                linked = obj[c4d.INSTANCEOBJECT_LINK]
                if linked:
                    self.copy_user_data(linked, obj)

        with self.temp_context(
            doc=self.source, objects=objects, unit_scale=c4d.DOCUMENT_UNIT_M, debug=False
        ) as tmp_doc:
            if tmp_doc is None:
                return None
            self._replace_instances_with_placeholders(tmp_doc, self.get_all_objects(tmp_doc))
            tmp_doc.ExecutePasses(None, True, True, True, c4d.BUILDFLAGS_NONE)
            self.make_editable_recursive(tmp_doc.GetFirstObject(), tmp_doc)
            self.project_scale(tmp_doc, 0.01)
            return self.export_file(tmp_doc, ext)
