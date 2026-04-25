from __future__ import annotations
import c4d
import maxon
from scene.materials.jb_base_node_material import JBBaseNodeMaterial

RS_ID = "com.redshift3d.redshift4c4d"
RS_NODESPACE = f"{RS_ID}.class.nodespace"
RS_CORE = f"{RS_ID}.nodes.core"
RS_OUTPUT = f"{RS_ID}.node.output"
RS_MATERIAL = f"{RS_CORE}.material"
RS_TEX = f"{RS_CORE}.texturesampler"
RS_BUMPMAP = f"{RS_CORE}.bumpmap"
RS_DISPLACEMENT = f"{RS_CORE}.displacement"

# Порты RS Material
RS_PORT_DIFFUSE = f"{RS_MATERIAL}.diffuse_color"
RS_PORT_BUMP = f"{RS_MATERIAL}.bump_input"
RS_PORT_ROUGHNESS = f"{RS_MATERIAL}.refl_roughness"
RS_PORT_EMISSIVE = f"{RS_MATERIAL}.emissive_color"
RS_PORT_METALNESS = f"{RS_MATERIAL}.refl_metalness"
RS_PORT_DISP_OUT = f"{RS_OUTPUT}.displacement"
RS_PORT_DISP_TEX = f"{RS_DISPLACEMENT}.texmap"
RS_PORT_BUMP_IN = f"{RS_BUMPMAP}.input"
RS_PORT_TEX_FILE = f"{RS_TEX}.tex0"
RS_PORT_TEX_PATH_SUB = "path"
NODE_NAME_ID = "net.maxon.node.base.name"


class JBRedshiftMaterial(JBBaseNodeMaterial):
    def id(self) -> str:
        return c4d.VPrsrenderer

    def nodespace_id(self) -> str:
        return RS_NODESPACE

    # ------------------------------------------------------------------ #

    def _get_key_nodes(self, graph) -> dict:
        return {
            "material": self.find_node(graph, RS_MATERIAL),
            "output": self.find_node(graph, RS_OUTPUT),
        }

    def _build_default_graph(self, graph, transaction) -> dict:
        material_node, _ = self.find_or_add_node(graph, RS_MATERIAL)
        output_node, _ = self.find_or_add_node(graph, RS_OUTPUT)
        return {"material": material_node, "output": output_node}

    # ------------------------------------------------------------------ #

    def _set_tex_path(self, node, path: str) -> None:
        """Устанавливает путь к файлу через tex0 → path (sub-port URL)."""
        filename_port = node.GetInputs().FindChild(maxon.InternedId(RS_PORT_TEX_FILE))
        if filename_port is None:
            return
        path_port = filename_port.FindChild(maxon.InternedId(RS_PORT_TEX_PATH_SUB))
        if path_port is not None:
            path_port.SetDefaultValue(self.path_to_url(path))

    def _make_texture_node(self, graph, channel: str, path: str):
        existing = self.find_nodes_by_asset_id(graph, RS_TEX)
        for node in existing:
            try:
                name_val = node.GetValue(NODE_NAME_ID)
                if str(name_val) == channel:
                    self._set_tex_path(node, path)
                    return node
            except Exception:
                pass

        node = self.add_node(graph, RS_TEX)
        try:
            node.SetValue(NODE_NAME_ID, maxon.String(channel))
        except Exception:
            pass
        self._set_tex_path(node, path)
        return node

    def _wire_channel(self, channel, path, graph, key_nodes, transaction) -> None:
        material = key_nodes.get("material")
        output = key_nodes.get("output")
        tex = self._make_texture_node(graph, channel, path)
        tex_out = self.get_first_output(tex)
        if tex_out is None:
            return

        if channel == "basecolor":
            tex_out.Connect(self.get_input_port(material, RS_PORT_DIFFUSE))

        elif channel == "normal":
            bump, _ = self.find_or_add_node(graph, RS_BUMPMAP)
            tex_out.Connect(self.get_input_port(bump, RS_PORT_BUMP_IN))
            bump_out = self.get_first_output(bump)
            if bump_out is not None:
                bump_out.Connect(self.get_input_port(material, RS_PORT_BUMP))

        elif channel == "roughness":
            tex_out.Connect(self.get_input_port(material, RS_PORT_ROUGHNESS))

        elif channel == "metallic":
            tex_out.Connect(self.get_input_port(material, RS_PORT_METALNESS))

        elif channel == "emissive":
            tex_out.Connect(self.get_input_port(material, RS_PORT_EMISSIVE))

        elif channel == "height":
            disp, _ = self.find_or_add_node(graph, RS_DISPLACEMENT)
            tex_out.Connect(self.get_input_port(disp, RS_PORT_DISP_TEX))
            disp_out = self.get_first_output(disp)
            if disp_out is not None:
                disp_out.Connect(self.get_input_port(output, RS_PORT_DISP_OUT))

        elif channel in ("opacity", "refraction", "ao"):
            pass
