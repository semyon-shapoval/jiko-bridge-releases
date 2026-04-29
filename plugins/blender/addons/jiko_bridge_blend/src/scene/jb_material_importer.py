"""
Material Importer for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import bpy
from ..jb_types import AssetModel, AssetFile
from ..jb_utils import get_logger
from ..materials.jb_standard_material import JBStandardMaterial

logger = get_logger(__name__)


class JBMaterialImporter:
    """Material importer that handles Blender materials."""

    def find_existing(self, name: str) -> Optional[bpy.types.Material]:
        """Find an existing material by name."""
        return bpy.data.materials.get(name)

    def import_material(self, asset: AssetModel, file: AssetFile) -> None:
        """Import a single material file into the scene."""
        if file.asset_type is None or file.filepath is None:
            logger.error("Material file is missing type or path")
            return

        channel = file.asset_type.lower()
        path = file.filepath
        material_name = f"{asset.pack_name}__{asset.asset_name}"

        material = self.find_existing(material_name)
        if not material:
            material = bpy.data.materials.new(name=material_name)

        standard = JBStandardMaterial(material)
        standard.apply_channel(channel, path)
