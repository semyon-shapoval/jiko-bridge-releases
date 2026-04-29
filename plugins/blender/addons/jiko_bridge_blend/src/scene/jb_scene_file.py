"""
Import and export file handling for Jiko Bridge in Blender.
Code by Semyon Shapoval, 2026
"""

import os
import time
from pathlib import Path
from typing import Optional

import bpy
from .jb_scene_instance import JBSceneInstance
from ..jb_utils import get_logger

logger = get_logger(__name__)


class JBSceneFile(JBSceneInstance):
    """File import/export layer in the scene hierarchy."""

    def import_file(self, file_path: str) -> bool:
        """Imports a file into the Blender scene."""
        if not os.path.exists(file_path):
            logger.error("Import file not found: %s", file_path)
            return False

        ext = Path(file_path).suffix.lower()
        handler = {
            ".fbx": self._import_fbx,
            ".abc": self._import_alembic,
            ".obj": self._import_obj,
            ".usd": self._import_usd,
            ".usda": self._import_usd,
            ".usdc": self._import_usd,
            ".glb": self._import_gltf,
            ".gltf": self._import_gltf,
        }.get(ext)

        if not handler:
            logger.error("Unsupported file extension: %s", ext)
            return False

        return handler(file_path)

    def _import_fbx(self, file_path: str) -> bool:
        logger.debug("Importing FBX asset: %s", file_path)
        try:
            bpy.ops.import_scene.fbx(
                filepath=file_path,
                use_image_search=False,
                automatic_bone_orientation=True,
            )
        except RuntimeError as e:
            logger.error("FBX import failed: %s", e)
            return False
        return True

    def _import_alembic(self, file_path: str) -> bool:
        """Imports an Alembic file into the Blender scene."""
        try:
            bpy.ops.wm.alembic_import(filepath=file_path, as_background_job=False)
        except RuntimeError as e:
            logger.error("Alembic import failed: %s", e)
            return False
        return True

    def _import_obj(self, file_path: str) -> bool:
        try:
            bpy.ops.wm.obj_import(filepath=file_path)
        except RuntimeError as e:
            logger.error("OBJ import failed: %s", e)
            return False
        return True

    def _import_usd(self, file_path: str) -> bool:
        try:
            bpy.ops.wm.usd_import(filepath=file_path)
        except RuntimeError as e:
            logger.error("USD import failed: %s", e)
            return False
        return True

    def _import_gltf(self, file_path: str) -> bool:
        try:
            bpy.ops.import_scene.gltf(filepath=file_path)
        except RuntimeError as e:
            logger.error("GLTF import failed: %s", e)
            return False
        return True

    def _generate_path(self, ext: str) -> str:
        filename = f"tmp_{int(time.time())}{ext}"
        return os.path.join(self.cache_path, filename)

    def export_file(self, ext: str) -> Optional[str]:
        """Exports the current Blender scene to a file."""
        file_path = self._generate_path(ext)
        handler = {
            ".fbx": self._export_fbx,
            ".abc": self._export_alembic,
            ".glb": self._export_gltf,
            ".obj": self._export_obj,
            ".usd": self._export_usd,
        }.get(ext)

        if not handler:
            logger.error("Unsupported export extension: %s", ext)
            return None

        return handler(file_path)

    def _export_fbx(self, file_path: str) -> Optional[str]:
        try:
            bpy.ops.export_scene.fbx(
                filepath=file_path,
                use_selection=False,
                apply_scale_options="FBX_SCALE_UNITS",
                global_scale=1,
                path_mode="COPY",
                embed_textures=False,
                bake_space_transform=False,
            )
            logger.info("FBX exported: %s", file_path)
            return file_path
        except RuntimeError as e:
            logger.error("FBX export failed: %s", e)
            return None

    def _export_alembic(self, file_path: str) -> Optional[str]:
        try:
            bpy.ops.wm.alembic_export(
                filepath=file_path,
                selected=False,
                as_background_job=False,
            )
            logger.info("Alembic exported: %s", file_path)
            return file_path
        except RuntimeError as e:
            logger.error("Alembic export failed: %s", e)
            return None

    def _export_gltf(self, file_path: str) -> Optional[str]:
        try:
            bpy.ops.export_scene.gltf(
                filepath=file_path,
                use_selection=False,
                export_format="GLB",
            )
            logger.info("GLTF exported: %s", file_path)
            return file_path
        except RuntimeError as e:
            logger.error("GLTF export failed: %s", e)
            return None

    def _export_obj(self, _file_path: str):
        logger.warning("OBJ export not implemented yet")

    def _export_usd(self, _file_path: str):
        logger.warning("USD export not implemented yet")
