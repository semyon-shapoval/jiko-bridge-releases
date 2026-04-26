import c4d
from jb_asset_model import AssetModel, AssetFile
from scene.jb_scene_container import JBSceneContainer
from scene.materials import (
    JBBaseMaterial,
    JBRedshiftNodeMaterial,
    JBArnoldNodeMaterial,
    JBStandardNodeMaterial,
)

ARNOLD_ID = 1029988
REDSHIFT_ID = c4d.VPrsrenderer
VIEWPORT_ID = 300001061


class JBMaterialImporter(JBSceneContainer):
    def __init__(self):
        super().__init__()
        self._redshift = JBRedshiftNodeMaterial()
        self._arnold = JBArnoldNodeMaterial()
        self._standard = JBStandardNodeMaterial()

    def _get_material_renderer(self) -> JBBaseMaterial:
        doc = c4d.documents.GetActiveDocument()
        render_id = doc.GetActiveRenderData()[c4d.RDATA_RENDERENGINE]
        if render_id == REDSHIFT_ID:
            return self._redshift
        elif render_id == ARNOLD_ID:
            return self._arnold
        elif render_id == VIEWPORT_ID:
            return self._standard
        else:
            return self._standard

    def import_material(self, asset: AssetModel, file: AssetFile) -> None:
        doc = c4d.documents.GetActiveDocument()
        renderer = self._get_material_renderer()
        channel = file.assetType.lower()
        path = file.filepath

        materialName = f"{asset.packName}__{asset.assetName}"

        existing = JBBaseMaterial.find_existing(doc, materialName)
        if existing:
            material = renderer.build_graph(existing)
        else:
            material = renderer.create(doc, materialName)

        renderer.apply_channel(material, channel, path)

        c4d.EventAdd()
