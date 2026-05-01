"""
Material Importer for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

import re

import bpy
from ..jb_types import AssetModel, AssetFile
from ..jb_utils import get_logger
from .jb_standard_material import JBStandardMaterial

logger = get_logger(__name__)


class JbMaterialImporter:
    """Material importer that handles Blender materials."""

    def _merge_duplicates(self, material: bpy.types.Material) -> None:
        """Replace duplicate materials (.001, .002, ...) with the given base material."""
        pattern = re.compile(r"^" + re.escape(material.name) + r"\.\d+$")
        duplicates = [m for m in bpy.data.materials if pattern.match(m.name)]
        for dup in duplicates:
            dup.user_remap(material)
            bpy.data.materials.remove(dup)

    def import_material(self, asset: AssetModel, file: AssetFile) -> None:
        """Import a single material file into the scene."""
        if file.asset_type is None or file.filepath is None:
            logger.error("Material file is missing type or path")
            return

        channel = file.asset_type.lower()
        path = file.filepath
        material_name = f"{asset.pack_name}__{asset.asset_name}"

        material = bpy.data.materials.get(material_name)
        if not material:
            material = bpy.data.materials.new(name=material_name)

        if material is None:
            logger.error("Failed to create material: %s", material_name)
            return

        standard = JBStandardMaterial(material)
        standard.apply_channel(channel, path)
        self._merge_duplicates(material)
