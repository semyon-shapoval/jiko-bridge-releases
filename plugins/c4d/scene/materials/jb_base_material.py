import c4d
import maxon

KNOWN_NODE_SPACES = [
    "com.autodesk.arnold.nodespace",
    "com.redshift3d.redshift4c4d.class.nodespace",
    "net.maxon.nodespace.standard",
    "com.chaos.class.vray_node_renderer_nodespace",
    "com.otoy.octane.nodespace",
]


class JBBaseMaterial:
    def id(self) -> str:
        raise NotImplementedError

    def nodespace_id(self) -> str | None:
        return None

    def create(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
    ) -> c4d.BaseMaterial:
        raise NotImplementedError

    def apply_channel(
        self, material: c4d.BaseMaterial, channel: str, path: str
    ) -> None:
        raise NotImplementedError

    def has_compatible_graph(self, material: c4d.BaseMaterial) -> bool:
        space = self.nodespace_id()
        try:
            node_mat = material.GetNodeMaterialReference()
            if node_mat is None:
                return space is None
            if space is None:
                # Standard: совместим только если нет ни одного известного нод-пространства
                for known in KNOWN_NODE_SPACES:
                    try:
                        if node_mat.HasSpace(maxon.Id(known)):
                            return False
                    except Exception:
                        pass
                return True
            return node_mat.HasSpace(maxon.Id(space))
        except Exception:
            return space is None

    def rebuild_graph(
        self, doc: c4d.documents.BaseDocument, material: c4d.BaseMaterial
    ) -> c4d.BaseMaterial:
        space = self.nodespace_id()
        try:
            node_mat = material.GetNodeMaterialReference()
            if node_mat is None:
                return material

            if space is None:
                # Standard: удаляем все известные нод-пространства
                for known in KNOWN_NODE_SPACES:
                    try:
                        if node_mat.HasSpace(maxon.Id(known)):
                            node_mat.RemoveGraph(maxon.Id(known))
                    except Exception:
                        pass
            else:
                # Node-рендер: удаляем все чужие пространства, добавляем своё
                for known in KNOWN_NODE_SPACES:
                    if known == space:
                        continue
                    try:
                        if node_mat.HasSpace(maxon.Id(known)):
                            node_mat.RemoveGraph(maxon.Id(known))
                    except Exception:
                        pass
                if not node_mat.HasSpace(maxon.Id(space)):
                    node_mat.AddGraph(maxon.Id(space))
        except Exception:
            pass

        return material

    @staticmethod
    def find_existing(doc: c4d.documents.BaseDocument, name: str):
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None
