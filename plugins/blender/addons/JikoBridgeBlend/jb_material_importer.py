import bpy
from typing import Optional

from .jb_asset_model import AssetModel
from .jb_logger import get_logger

logger = get_logger(__name__)


class JBMaterialImporter:
    """Создаёт материалы Blender из ассета."""

    def import_material(self, asset: AssetModel) -> Optional[bpy.types.Material]:
        """Определяет активный рендерер и создаёт подходящий материал."""
        render_engine = bpy.context.scene.render.engine

        return self._create_principled_material(asset)

    def _create_principled_material(
        self, asset: AssetModel
    ) -> Optional[bpy.types.Material]:
        """
        Создаёт материал на основе Principled BSDF с нодами для каждого текстурного канала.
        Работает для Cycles, EEVEE и любых других рендереров Blender.
        """
        channels = asset.get_textures()

        mat = bpy.data.materials.new(name=asset.asset_name or "JB_Material")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        # Output
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

        # Principled BSDF
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (300, 0)
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        x_offset = -300
        y_offset = 300

        def add_texture_node(
            channel: str, path: str, y: float, color_space: str = "sRGB"
        ) -> bpy.types.Node:
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (x_offset - 200, y)
            try:
                img = bpy.data.images.load(path, check_existing=True)
                if color_space != "sRGB":
                    img.colorspace_settings.name = "Non-Color"
                tex_node.image = img
            except Exception as e:
                logger.warning("Failed to load texture '%s': %s", path, e)
            return tex_node

        y = y_offset

        if "basecolor" in channels:
            tex = add_texture_node("basecolor", channels["basecolor"], y, "sRGB")
            links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
            y -= 250

        if "metallic" in channels:
            tex = add_texture_node("metallic", channels["metallic"], y, "Non-Color")
            links.new(tex.outputs["Color"], bsdf.inputs["Metallic"])
            y -= 250

        if "roughness" in channels:
            tex = add_texture_node("roughness", channels["roughness"], y, "Non-Color")
            links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])
            y -= 250

        if "normal" in channels:
            tex = add_texture_node("normal", channels["normal"], y, "Non-Color")
            normal_map = nodes.new("ShaderNodeNormalMap")
            normal_map.location = (x_offset + 100, y)
            links.new(tex.outputs["Color"], normal_map.inputs["Color"])
            links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
            y -= 250

        if "emissive" in channels:
            tex = add_texture_node("emissive", channels["emissive"], y, "sRGB")
            links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = 1.0
            y -= 250

        if "opacity" in channels:
            tex = add_texture_node("opacity", channels["opacity"], y, "Non-Color")
            links.new(tex.outputs["Color"], bsdf.inputs["Alpha"])
            mat.blend_method = "HASHED"
            y -= 250

        if "height" in channels:
            tex = add_texture_node("height", channels["height"], y, "Non-Color")
            disp_node = nodes.new("ShaderNodeDisplacement")
            disp_node.location = (x_offset + 100, y - 100)
            links.new(tex.outputs["Color"], disp_node.inputs["Height"])
            links.new(disp_node.outputs["Displacement"], output.inputs["Displacement"])
            y -= 250

        if "ao" in channels:
            # AO подмешиваем к basecolor через MixRGB
            if "basecolor" in channels:
                ao_tex = add_texture_node("ao", channels["ao"], y, "Non-Color")
                mix = nodes.new("ShaderNodeMixRGB")
                mix.blend_type = "MULTIPLY"
                mix.inputs["Fac"].default_value = 1.0
                mix.location = (x_offset + 100, y + 150)
                # Переподключаем basecolor через mix
                base_tex = next(
                    (
                        n
                        for n in nodes
                        if n.type == "TEX_IMAGE"
                        and n.image
                        and "basecolor" in (n.image.name.lower())
                    ),
                    None,
                )
                if base_tex:
                    links.new(base_tex.outputs["Color"], mix.inputs["Color1"])
                    links.new(ao_tex.outputs["Color"], mix.inputs["Color2"])
                    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])

        logger.info("Material '%s' created successfully.", mat.name)
        return mat
