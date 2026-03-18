import bpy
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from .jb_logger import get_logger

logger = get_logger(__name__)


class JBFileImporter:
    def import_file(self, file_path: str) -> list:
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
            return []

        return handler(file_path)

    def _get_new_objects(self, before: set) -> list:
        """Returns objects added to the scene since before."""
        return [obj for obj in bpy.context.scene.objects if obj not in before]

    def _import_fbx(self, file_path: str) -> list:
        before = set(bpy.context.scene.objects)
        try:
            bpy.ops.import_scene.fbx(filepath=file_path)
        except Exception as e:
            logger.error("FBX import failed: %s", e)
            return []
        return self._get_new_objects(before)

    def _import_alembic(self, file_path: str) -> list:
        before = set(bpy.context.scene.objects)
        try:
            bpy.ops.wm.alembic_import(filepath=file_path, as_background_job=False)
        except Exception as e:
            logger.error("Alembic import failed: %s", e)
            return []
        return self._get_new_objects(before)

    def _import_obj(self, file_path: str) -> list:
        before = set(bpy.context.scene.objects)
        try:
            bpy.ops.wm.obj_import(filepath=file_path)
        except Exception as e:
            logger.error("OBJ import failed: %s", e)
            return []
        return self._get_new_objects(before)

    def _import_usd(self, file_path: str) -> list:
        before = set(bpy.context.scene.objects)
        try:
            bpy.ops.wm.usd_import(filepath=file_path)
        except Exception as e:
            logger.error("USD import failed: %s", e)
            return []
        return self._get_new_objects(before)

    def _import_gltf(self, file_path: str) -> list:
        before = set(bpy.context.scene.objects)
        try:
            bpy.ops.import_scene.gltf(filepath=file_path)
        except Exception as e:
            logger.error("GLTF import failed: %s", e)
            return []
        return self._get_new_objects(before)


class JBFileExporter:
    def __init__(self):
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    def _generate_path(self, ext: str) -> str:
        filename = f"tmp_{int(time.time())}{ext}"
        return os.path.join(self.cache_path, filename)

    def export_file(self, objects: list, ext: str) -> Optional[str]:
        file_path = self._generate_path(ext)
        handler = {
            ".fbx": self._export_fbx,
            ".abc": self._export_alembic,
            ".glb": self._export_gltf,
        }.get(ext)

        if not handler:
            logger.error("Unsupported export extension: %s", ext)
            return None

        return handler(objects, file_path)

    def _select_only(self, objects: list) -> None:
        for obj in bpy.context.scene.collection.all_objects:
            obj.select_set(False)
        for obj in objects:
            obj.select_set(True)
        if objects:
            bpy.context.view_layer.objects.active = objects[0]

    def _export_fbx(self, objects: list, file_path: str) -> Optional[str]:
        self._select_only(objects)
        try:
            bpy.ops.export_scene.fbx(
                filepath=file_path,
                use_selection=True,
                apply_scale_options="FBX_SCALE_ALL",
                global_scale=0.01,
                path_mode="COPY",
                embed_textures=False,
            )
            logger.info("FBX exported: %s", file_path)
            return file_path
        except Exception as e:
            logger.error("FBX export failed: %s", e)
            return None

    def _export_alembic(self, objects: list, file_path: str) -> Optional[str]:
        self._select_only(objects)
        try:
            bpy.ops.wm.alembic_export(
                filepath=file_path,
                selected=True,
                as_background_job=False,
            )
            logger.info("Alembic exported: %s", file_path)
            return file_path
        except Exception as e:
            logger.error("Alembic export failed: %s", e)
            return None

    def _export_gltf(self, objects: list, file_path: str) -> Optional[str]:
        self._select_only(objects)
        try:
            bpy.ops.export_scene.gltf(
                filepath=file_path,
                use_selection=True,
                export_format="GLB",
            )
            logger.info("GLTF exported: %s", file_path)
            return file_path
        except Exception as e:
            logger.error("GLTF export failed: %s", e)
            return None
