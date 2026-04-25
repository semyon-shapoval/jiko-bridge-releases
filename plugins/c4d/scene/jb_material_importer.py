import c4d
from jb_asset_model import AssetModel, AssetFile
from scene.jb_scene_container import JBSceneContainer
from scene.materials import (
    JBBaseMaterial,
    JBRedshiftMaterial,
    JBArnoldNodeMaterial,
    JBCinema4DNodeMaterial,
)


class JBMaterialImporter(JBSceneContainer):
    def __init__(self):
        super().__init__()
        self._redshift = JBRedshiftMaterial()
        self._arnold = JBArnoldNodeMaterial()
        self._standard = JBCinema4DNodeMaterial()

    def _get_material_renderer(self) -> JBBaseMaterial:
        doc = c4d.documents.GetActiveDocument()
        render_id = doc.GetActiveRenderData()[c4d.RDATA_RENDERENGINE]
        if render_id == self._redshift.id():
            return self._redshift
        if render_id == self._arnold.id():
            return self._arnold
        return self._standard

    def import_material(self, asset: AssetModel, file: AssetFile) -> None:
        doc = c4d.documents.GetActiveDocument()
        renderer = self._get_material_renderer()
        channel = file.assetType.lower()
        path = file.filepath

        materialName = f"{asset.packName}__{asset.assetName}"

        existing = JBBaseMaterial.find_existing(doc, materialName)
        if existing:
            if renderer.has_compatible_graph(existing):
                material = existing
            else:
                material = renderer.rebuild_graph(doc, existing)
        else:
            material = renderer.create(doc, materialName)

        renderer.apply_channel(material, channel, path)
