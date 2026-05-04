"""
Temporary document for operations.
Code by Semyon Shapoval, 2026
"""

from contextlib import contextmanager

import c4d
from src.scene.jb_scene_instance import JbSceneInstance


class JbSceneTemp(JbSceneInstance):
    """Scene-level operations: document helpers, geometry transforms."""

    def __init__(self):
        self._temp_source = None

    @contextmanager
    def temp_source(self, objects=None, unit_scale=c4d.DOCUMENT_UNIT_CM, debug=False):
        if objects:
            tmp_doc = c4d.documents.IsolateObjects(self.source, objects)
        else:
            tmp_doc = c4d.documents.BaseDocument()

        self._temp_source = tmp_doc

        unit_scale_data = c4d.UnitScaleData()
        unit_scale_data.SetUnitScale(1, unit_scale)
        tmp_doc[c4d.DOCUMENT_DOCUNIT] = unit_scale_data

        try:
            yield tmp_doc
        finally:
            if debug:
                c4d.documents.InsertBaseDocument(tmp_doc)
                c4d.documents.SetActiveDocument(tmp_doc)
                c4d.EventAdd()
            else:
                c4d.documents.KillDocument(tmp_doc)

            self._temp_source = None

    def _copy_source(self, src, dst, parent) -> None:
        mat = src.GetFirstMaterial()
        while mat:
            next_mat = mat.GetNext()
            mat.Remove()
            dst.InsertMaterial(mat)
            mat = next_mat

        objects = self.walk(src.GetFirstObject())
        for obj in objects:
            obj.Remove()
            dst.InsertObject(obj)
            obj.InsertUnder(parent)
            obj.SetBit(c4d.BIT_ACTIVE)

    # ------------------------------------------------------------------
    # Geometry transforms
    # ------------------------------------------------------------------

    def _project_scale(self, doc: c4d.documents.BaseDocument, factor: float = 0.01) -> None:
        objects = self.walk(doc.GetFirstObject())
        for obj in objects:
            if obj.IsInstanceOf(c4d.Opolygon):
                points = obj.GetAllPoints()
                if points:
                    obj.SetAllPoints([p * factor for p in points])
                    obj.Message(c4d.MSG_UPDATE)

            pos = obj.GetRelPos()
            obj.SetRelPos(pos * factor)

    def _make_editable_recursive(
        self,
        obj: c4d.BaseObject | None,
        doc: c4d.documents.BaseDocument,
    ) -> None:
        """Рекурсивно конвертирует генераторы/инстансы в полигоны (MCOMMAND_MAKEEDITABLE)."""
        if obj is None:
            return

        # Сохраняем соседей и родителя до конвертации — после они могут стать невалидными
        next_obj = obj.GetNext()
        parent = obj.GetUp()

        # Сначала рекурсивно обходим детей
        self._make_editable_recursive(obj.GetDown(), doc)

        if not obj.IsAlive() or obj.IsInstanceOf(c4d.Opolygon):
            self._make_editable_recursive(next_obj, doc)
            return

        result = c4d.utils.SendModelingCommand(
            command=c4d.MCOMMAND_MAKEEDITABLE,
            list=[obj],
            mode=c4d.MODELINGCOMMANDMODE_ALL,
            doc=doc,
        )

        if isinstance(result, list):
            for new_obj in reversed(result):
                if parent:
                    new_obj.InsertUnder(parent)
                else:
                    doc.InsertObject(new_obj)

        self._make_editable_recursive(next_obj, doc)
