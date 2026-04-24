import c4d
import maxon
from scene.materials.jb_base_material import JBBaseMaterial


RS_ID = "com.redshift3d.redshift4c4d"
REDSHIFT_NODESPACE_ID = f"{RS_ID}.class.nodespace"
RS_CORE_ID = f"{RS_ID}.nodes.core"
RS_OUTPUT_ID = f"{RS_ID}.node.output"
RS_MATERIAL_ID = f"{RS_CORE_ID}.material"
RS_TEX_ID = f"{RS_CORE_ID}.texturesampler"
RS_BUMPMAP_ID = f"{RS_CORE_ID}.bumpmap"
RS_DISPLACEMENT_ID = f"{RS_CORE_ID}.displacement"
NODE_NAME_ID = "net.maxon.node.base.name"


class JBRedshiftMaterial(JBBaseMaterial):
    def id(self) -> str:
        return c4d.VPrsrenderer
    
    def create(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
    ) -> c4d.BaseMaterial:
        """
        Graph Node: https://developers.maxon.net/docs/py/2023_2/modules/maxon_generated/frameworks/graph/datatype/maxon.GraphNode.html
        Graph Interface: https://developers.maxon.net/docs/py/2023_2/modules/maxon_generated/frameworks/graph/interface/maxon.GraphModelInterface.html
        """
        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(name)

        nodes_material = material.GetNodeMaterialReference()
        nodes_material.AddGraph(REDSHIFT_NODESPACE_ID)
        rs_graph = nodes_material.GetGraph(REDSHIFT_NODESPACE_ID)

        with rs_graph.BeginTransaction() as transaction:
            rs_material = None
            rs_output = None
            for child in rs_graph.GetRoot().GetChildren():
                if child.IsInner():
                    n = child.GetValue(NODE_NAME_ID)
                    if n == "RS Material":
                        rs_material = child
                    if n == "Output":
                        rs_output = child

            if not rs_material:
                rs_material = rs_graph.AddChild("", RS_MATERIAL_ID)
            if not rs_output:
                rs_output = rs_graph.AddChild("", RS_OUTPUT_ID)

            transaction.Commit()

        doc.InsertMaterial(material)
        return material

    def apply_channel(
        self, material: c4d.BaseMaterial, channel: str, path: str
    ) -> None:
        nodes_material = material.GetNodeMaterialReference()
        rs_graph = nodes_material.GetGraph(REDSHIFT_NODESPACE_ID)

        rs_material_node = None
        rs_output_node = None
        for child in rs_graph.GetRoot().GetChildren():
            if child.IsInner():
                name = child.GetValue(NODE_NAME_ID)
                if name == "RS Material":
                    rs_material_node = child
                if name == "Output":
                    rs_output_node = child

        with rs_graph.BeginTransaction() as transaction:

            def create_texture_node():
                node = rs_graph.AddChild("", RS_TEX_ID)
                node.SetValue(NODE_NAME_ID, maxon.String(channel))
                node.SetValue(
                    maxon.InternedId(f"{RS_TEX_ID}.color_multiplier"),
                    maxon.Data(maxon.Url(f"file:///{path}")),
                )
                return node, node.GetOutputs().GetChildren()[0]

            self._wire_channel(
                channel,
                lambda _: create_texture_node(),
                rs_graph,
                rs_material_node,
                rs_output_node,
            )
            transaction.Commit()

        material.Update(True, True)

    @staticmethod
    def _wire_channel(
        channel, create_texture_node, rs_graph, rs_material, rs_output
    ) -> None:
        if channel == "basecolor":
            _, out = create_texture_node(channel)
            out.Connect(
                rs_material.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_MATERIAL_ID}.diffuse_color")
                )
            )
        elif channel == "normal":
            _, out = create_texture_node(channel)
            bump = rs_graph.AddChild("", RS_BUMPMAP_ID)
            out.Connect(bump.GetInputs().GetChildren()[0])
            bump.GetOutputs().GetChildren()[0].Connect(
                rs_material.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_MATERIAL_ID}.bump_input")
                )
            )
        elif channel == "roughness":
            _, out = create_texture_node(channel)
            out.Connect(
                rs_material.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_MATERIAL_ID}.refl_roughness")
                )
            )
        elif channel == "height":
            _, out = create_texture_node(channel)
            disp = rs_graph.AddChild("", RS_DISPLACEMENT_ID)
            out.Connect(
                disp.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_DISPLACEMENT_ID}.texmap")
                )
            )
            disp.GetOutputs().GetChildren()[0].Connect(
                rs_output.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_OUTPUT_ID}.displacement")
                )
            )
        elif channel == "emissive":
            _, out = create_texture_node(channel)
            out.Connect(
                rs_material.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_MATERIAL_ID}.emissive_color")
                )
            )
        elif channel == "metallic":
            _, out = create_texture_node(channel)
            out.Connect(
                rs_material.GetInputs().FindChild(
                    maxon.InternedId(f"{RS_MATERIAL_ID}.refl_metalness")
                )
            )
        elif channel in ("opacity", "refraction", "ao"):
            create_texture_node(channel)
