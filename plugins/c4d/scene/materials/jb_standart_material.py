import c4d
from typing import Dict
from scene.materials.jb_base_material import JBBaseMaterial


class JBStandardMaterial(JBBaseMaterial):
    def create(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
    ) -> c4d.BaseMaterial:
        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(name)
        material.RemoveReflectionAllLayers()
        doc.InsertMaterial(material)
        return material

    def apply_channel(
        self, material: c4d.BaseMaterial, channel: str, path: str
    ) -> None:
        def load_bitmap():
            bmp = c4d.BaseShader(c4d.Xbitmap)
            bmp[c4d.BITMAPSHADER_FILENAME] = path
            material.InsertShader(bmp)
            return bmp

        def assign(use_const, shader_const):
            try:
                material[use_const] = True
                material[shader_const] = load_bitmap()
            except Exception as e:
                print(f"Error assigning {channel}: {e}")

        if channel == "basecolor":
            assign(c4d.MATERIAL_USE_COLOR, c4d.MATERIAL_COLOR_SHADER)
        elif channel == "normal":
            assign(c4d.MATERIAL_USE_NORMAL, c4d.MATERIAL_NORMAL_SHADER)
        elif channel == "emissive":
            assign(c4d.MATERIAL_USE_LUMINANCE, c4d.MATERIAL_LUMINANCE_SHADER)
        elif channel == "opacity":
            assign(c4d.MATERIAL_USE_ALPHA, c4d.MATERIAL_ALPHA_SHADER)
        elif channel == "refraction":
            assign(c4d.MATERIAL_USE_TRANSPARENCY, c4d.MATERIAL_TRANSPARENCY_SHADER)
        elif channel == "height":
            assign(c4d.MATERIAL_USE_DISPLACEMENT, c4d.MATERIAL_DISPLACEMENT_SHADER)
        elif channel in ("roughness", "metallic"):
            bmp = load_bitmap()
            layer = material.AddReflectionLayer()
            layer.SetName(channel)
            data_id = layer.GetDataID()
            material.SetParameter(
                data_id | c4d.REFLECTION_LAYER_TRANS_TEXTURE, bmp, c4d.DESCFLAGS_SET_0
            )
        elif channel == "ao":
            assign(c4d.MATERIAL_USE_DIFFUSION, c4d.MATERIAL_DIFFUSION_SHADER)
