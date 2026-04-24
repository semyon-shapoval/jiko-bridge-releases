import c4d

class JBBaseMaterial:
    def id(self) -> str:
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

    @staticmethod
    def find_existing(doc: c4d.documents.BaseDocument, name: str):
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None
