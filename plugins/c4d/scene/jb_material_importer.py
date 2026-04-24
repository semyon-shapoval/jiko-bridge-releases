import c4d
from jb_asset_model import AssetModel, AssetFile
from scene.jb_scene_container import JBSceneContainer
from scene.materials import (
    JBBaseMaterial,
    JBRedshiftMaterial,
    JBArnoldMaterial,
    JBStandardMaterial,
)

class JBMaterialImporter(JBSceneContainer):
    def __init__(self):
        super().__init__()
        self._redshift = JBRedshiftMaterial()
        self._arnold = JBArnoldMaterial()
        self._standard = JBStandardMaterial()

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
        channel = file.asset_type.lower()
        path = file.file_path

        existing = JBBaseMaterial.find_existing(doc, asset.asset_name)
        if existing:
            renderer.apply_channel(existing, channel, path)
        else:
            material = renderer.create(doc, asset.asset_name)
            renderer.apply_channel(material, channel, path)
