"""
Temporary document for operations.
Code by Semyon Shapoval, 2026
"""

from contextlib import contextmanager
from typing import Optional

import c4d
from src.scene import JbSceneFile


class JbSceneTemp(JbSceneFile):
    """Scene-level operations: document helpers, geometry transforms."""

    @contextmanager
    def temp_context(
        self,
        doc: Optional[c4d.documents.BaseDocument] = None,
        objects: Optional[list[c4d.BaseObject]] = None,
        unit_scale: int = c4d.DOCUMENT_UNIT_CM,
        debug: bool = False,
    ):
        """Создаёт временный документ и гарантированно уничтожает его после использования."""
        if doc and objects:
            tmp_doc = c4d.documents.IsolateObjects(doc, objects)
        else:
            tmp_doc = c4d.documents.BaseDocument()

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

    def copy_context(
        self,
        src: c4d.documents.BaseDocument,
        dst: c4d.documents.BaseDocument,
        parent: c4d.BaseObject,
    ) -> None:
        """Переносит материалы и объекты из src в dst, вставляя объекты под parent."""
        mat = src.GetFirstMaterial()
        while mat:
            next_mat = mat.GetNext()
            mat.Remove()
            dst.InsertMaterial(mat)
            mat = next_mat

        objects = self.get_top_objects(src)
        for obj in objects:
            obj.Remove()
            dst.InsertObject(obj)
            obj.InsertUnder(parent)
            obj.SetBit(c4d.BIT_ACTIVE)

    # ------------------------------------------------------------------
    # Geometry transforms
    # ------------------------------------------------------------------

    def project_scale(self, doc: c4d.documents.BaseDocument, factor: float = 0.01) -> None:
        """Масштабирует сцену:
        - точки полигональных объектов (меш не деформируется, Scale остаётся 1)
        - позиции всех объектов (относительные, не трогая Rotation и Scale)
        """
        for obj in self.get_all_objects(doc):
            if obj.IsInstanceOf(c4d.Opolygon):
                points = obj.GetAllPoints()
                if points:
                    obj.SetAllPoints([p * factor for p in points])
                    obj.Message(c4d.MSG_UPDATE)

            pos = obj.GetRelPos()
            obj.SetRelPos(pos * factor)

    def make_editable_recursive(
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
        self.make_editable_recursive(obj.GetDown(), doc)

        if not obj.IsAlive() or obj.IsInstanceOf(c4d.Opolygon):
            self.make_editable_recursive(next_obj, doc)
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

        self.make_editable_recursive(next_obj, doc)
