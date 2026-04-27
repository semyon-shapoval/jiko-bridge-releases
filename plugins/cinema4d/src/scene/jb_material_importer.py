"""
Material importer for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

import c4d
from src.jb_asset_model import AssetModel, AssetFile
from src.jb_logger import get_logger
from src.materials import (
    JbRedshiftNodeMaterial,
    JbArnoldNodeMaterial,
    JbStandardNodeMaterial,
)

ARNOLD_ID = 1029988
REDSHIFT_ID = c4d.VPrsrenderer
VIEWPORT_ID = 300001061

logger = get_logger(__name__)


class JbMaterialImporter:
    """Material importer that handles different renderers."""

    def __init__(self):
        super().__init__()
        self._redshift = JbRedshiftNodeMaterial()
        self._arnold = JbArnoldNodeMaterial()
        self._standard = JbStandardNodeMaterial()

    def find_existing(self, name: str):
        """Find an existing material by name."""
        doc = c4d.documents.GetActiveDocument()
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None

    def _get_material_renderer(self):
        doc = c4d.documents.GetActiveDocument()
        render_id = doc.GetActiveRenderData()[c4d.RDATA_RENDERENGINE]
        if render_id == REDSHIFT_ID:
            return self._redshift
        if render_id == ARNOLD_ID:
            return self._arnold
        if render_id == VIEWPORT_ID:
            return self._standard
        return self._standard

    def import_material(self, asset: AssetModel, file: AssetFile) -> None:
        """Import a single material file into the scene."""
        if file.asset_type is None or file.filepath is None:
            logger.error("Material file is missing type or path")
            return

        doc = c4d.documents.GetActiveDocument()
        renderer = self._get_material_renderer()
        channel = file.asset_type.lower()
        path = file.filepath

        material_name = f"{asset.pack_name}__{asset.asset_name}"

        material = self.find_existing(material_name)
        if not material:
            material = c4d.BaseMaterial(c4d.Mmaterial)
            material.SetName(material_name)
            doc.InsertMaterial(material)

        renderer.apply_channel(material, channel, path)

        c4d.EventAdd()
