import c4d
import maxon


class JBBaseMaterial:
    def nodespace_id(self) -> str | None:
        raise NotImplementedError

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

    def build_graph(self, material: c4d.BaseMaterial) -> c4d.BaseMaterial:
        space = self.nodespace_id()
        node_mat = material.GetNodeMaterialReference()
        if node_mat is None:
            return material

        if not node_mat.HasSpace(maxon.Id(space)):
            node_mat.AddGraph(maxon.Id(space))

        return material

    @staticmethod
    def find_existing(doc: c4d.documents.BaseDocument, name: str):
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None
