import c4d
import maxon
from scene.materials.jb_base_material import JBBaseMaterial


def _path_to_url(path: str) -> maxon.Url:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return maxon.Url(f"file://{normalized}")


class JBArnoldMaterial(JBBaseMaterial):
    def id(self) -> str:
        return 1029988

    def create(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
    ) -> c4d.BaseMaterial:
        from arnold.material import ArnoldNodeMaterial, ArnoldMaterialTransaction

        arnoldMaterial = ArnoldNodeMaterial.Create(name)

        with ArnoldMaterialTransaction(arnoldMaterial):
            standard_surface = arnoldMaterial.AddShader(
                "standard_surface", "standard_surface"
            )
            arnoldMaterial.AddRootConnection(standard_surface, None, "shader")

            correct_node = arnoldMaterial.AddShader("color_correct", "color_correct")
            arnoldMaterial.AddConnection(
                correct_node, None, standard_surface, "base_color"
            )

        doc.InsertMaterial(arnoldMaterial.material)
        return arnoldMaterial.material

    def apply_channel(
        self, material: c4d.BaseMaterial, channel: str, path: str
    ) -> None:
        from arnold.material import ArnoldNodeMaterial, ArnoldMaterialTransaction

        arnoldMaterial = ArnoldNodeMaterial(material)
        url = _path_to_url(path)

        def create_texture_node(node_id: str):
            shader = arnoldMaterial.AddShader("image", maxon.String(node_id))
            arnoldMaterial.SetShaderValue(shader, "filename", url)
            return shader

        with ArnoldMaterialTransaction(arnoldMaterial):
            get_shader = getattr(arnoldMaterial, "GetShader", None)
            if not callable(get_shader):
                return

            standard_surface = get_shader("standard_surface")
            correct_node = get_shader("color_correct")
            if not standard_surface or not correct_node:
                return

            if channel == "basecolor":
                arnoldMaterial.AddConnection(
                    create_texture_node(channel), None, correct_node, "input"
                )
            elif channel == "normal":
                arnoldMaterial.AddConnection(
                    create_texture_node(channel), None, standard_surface, "normal"
                )
            elif channel == "roughness":
                arnoldMaterial.AddConnection(
                    create_texture_node(channel),
                    None,
                    standard_surface,
                    "specular_roughness",
                )
            elif channel == "height":
                node = create_texture_node(channel)
                displacement = arnoldMaterial.AddShader("displacement", "displacement")
                arnoldMaterial.AddRootConnection(displacement, None, "displacement")
                arnoldMaterial.AddConnection(node, None, displacement, "displacement")
            elif channel == "opacity":
                arnoldMaterial.AddConnection(
                    create_texture_node(channel), None, standard_surface, "opacity"
                )
            elif channel == "emissive":
                arnoldMaterial.SetShaderValue(standard_surface, "emission", 1.0)
                arnoldMaterial.AddConnection(
                    create_texture_node(channel),
                    None,
                    standard_surface,
                    "emission_color",
                )
            elif channel == "refraction":
                arnoldMaterial.SetShaderValue(standard_surface, "transmission", 1.0)
                arnoldMaterial.AddConnection(
                    create_texture_node(channel),
                    None,
                    standard_surface,
                    "transmission_color",
                )
            elif channel == "metallic":
                arnoldMaterial.AddConnection(
                    create_texture_node(channel),
                    None,
                    standard_surface,
                    "metalness",
                )
            elif channel == "ao":
                arnoldMaterial.AddConnection(
                    create_texture_node(channel), None, correct_node, "multiply"
                )
