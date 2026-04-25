from __future__ import annotations
import c4d
import maxon
from scene.materials.jb_base_node_material import JBBaseNodeMaterial

ARNOLD_NODESPACE = "com.autodesk.arnold.nodespace"
ARNOLD_END = "com.autodesk.arnold.material"
ARNOLD_STANDARD = "com.autodesk.arnold.shader.standard_surface"
ARNOLD_IMAGE = "com.autodesk.arnold.shader.image"
ARNOLD_COLCORRECT = "com.autodesk.arnold.shader.color_correct"
ARNOLD_DISP = "com.autodesk.arnold.shader.displacement"
ARNOLD_NORMALMAP = "com.autodesk.arnold.shader.normal_map"

# Порты standard_surface
PORT_BASE_COLOR = f"{ARNOLD_STANDARD}.base_color"
PORT_NORMAL = f"{ARNOLD_STANDARD}.normal"
PORT_ROUGHNESS = f"{ARNOLD_STANDARD}.specular_roughness"
PORT_METALNESS = f"{ARNOLD_STANDARD}.metalness"
PORT_EMISSION = f"{ARNOLD_STANDARD}.emission"
PORT_EMIS_COLOR = f"{ARNOLD_STANDARD}.emission_color"
PORT_OPACITY = f"{ARNOLD_STANDARD}.opacity"
PORT_TRANSMISSION = f"{ARNOLD_STANDARD}.transmission"
PORT_TRANS_COLOR = f"{ARNOLD_STANDARD}.transmission_color"

# Порты end node
PORT_SHADER_IN = f"{ARNOLD_END}.shader"
PORT_DISP_IN = f"{ARNOLD_END}.displacement"

# Порты вспомогательных нодов
PORT_CC_INPUT = f"{ARNOLD_COLCORRECT}.input"
PORT_CC_MULTIPLY = f"{ARNOLD_COLCORRECT}.multiply"
PORT_NM_INPUT = f"{ARNOLD_NORMALMAP}.input"
PORT_DISP_MAP = f"{ARNOLD_DISP}.displacement"
PORT_IMG_FILE = f"{ARNOLD_IMAGE}.filename"


class JBArnoldNodeMaterial(JBBaseNodeMaterial):
    def id(self) -> int:
        return 1029988

    def nodespace_id(self) -> str:
        return ARNOLD_NODESPACE

    # ------------------------------------------------------------------ #
    #  Определение типа существующего материала                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_node_arnold(material: c4d.BaseMaterial) -> bool:
        """Новый Arnold Node Material (нативный C4D Node Editor)"""
        try:
            from arnold.material import IsArnoldNodeMaterial

            return IsArnoldNodeMaterial(material)
        except Exception:
            pass

        try:
            node_mat = material.GetNodeMaterialReference()
            if node_mat is None:
                return False
            return node_mat.HasSpace(maxon.Id(ARNOLD_NODESPACE))
        except Exception:
            return False

    def has_compatible_graph(self, material: c4d.BaseMaterial) -> bool:
        return self.is_node_arnold(material)

    # ------------------------------------------------------------------ #
    #  Создание материала                                                  #
    # ------------------------------------------------------------------ #

    def _get_key_nodes(self, graph) -> dict:
        return {
            "end": self.find_node(graph, ARNOLD_END),
            "surface": self.find_node(graph, ARNOLD_STANDARD),
            "correct": self.find_node(graph, ARNOLD_COLCORRECT),
        }

    def _build_default_graph(self, graph, transaction) -> dict:
        end, _ = self.find_or_add_node(graph, ARNOLD_END)
        surface, _ = self.find_or_add_node(graph, ARNOLD_STANDARD)
        correct, _ = self.find_or_add_node(graph, ARNOLD_COLCORRECT)

        self.get_first_output(correct).Connect(
            self.get_input_port(surface, PORT_BASE_COLOR)
        )
        self.get_first_output(surface).Connect(self.get_input_port(end, PORT_SHADER_IN))
        return {"end": end, "surface": surface, "correct": correct}

    # ------------------------------------------------------------------ #

    def _make_image_node(self, graph, channel: str, path: str):
        existing = self.find_nodes_by_asset_id(graph, ARNOLD_IMAGE)
        for node in existing:
            try:
                name_val = node.GetValue("net.maxon.node.base.name")
                if str(name_val) == channel:
                    port = self.get_input_port(node, PORT_IMG_FILE)
                    if port is not None:
                        port.SetDefaultValue(self.path_to_url(path))
                    return node
            except Exception:
                pass

        node = self.add_node(graph, ARNOLD_IMAGE)
        try:
            node.SetValue("net.maxon.node.base.name", maxon.String(channel))
        except Exception:
            pass
        port = self.get_input_port(node, PORT_IMG_FILE)
        if port is not None:
            port.SetDefaultValue(self.path_to_url(path))
        return node

    def _wire_channel(self, channel, path, graph, key_nodes, transaction) -> None:
        end = key_nodes.get("end")
        surface = key_nodes.get("surface")
        correct = key_nodes.get("correct")

        if surface is None:
            print(f"[JBArnoldNode] standard_surface not found")
            return

        img = self._make_image_node(graph, channel, path)
        img_out = self.get_first_output(img)
        if img_out is None:
            return

        if channel == "basecolor":
            target = self.get_input_port(correct, PORT_CC_INPUT) if correct else None
            target = target or self.get_input_port(surface, PORT_BASE_COLOR)
            if target is not None:
                img_out.Connect(target)

        elif channel == "normal":
            nm, _ = self.find_or_add_node(graph, ARNOLD_NORMALMAP)
            p = self.get_input_port(nm, PORT_NM_INPUT)
            if p is not None:
                img_out.Connect(p)
            nm_out = self.get_first_output(nm)
            if nm_out is not None:
                p = self.get_input_port(surface, PORT_NORMAL)
                if p is not None:
                    nm_out.Connect(p)

        elif channel == "roughness":
            p = self.get_input_port(surface, PORT_ROUGHNESS)
            if p is not None:
                img_out.Connect(p)

        elif channel == "metallic":
            p = self.get_input_port(surface, PORT_METALNESS)
            if p is not None:
                img_out.Connect(p)

        elif channel == "emissive":
            p = self.get_input_port(surface, PORT_EMIS_COLOR)
            if p is not None:
                img_out.Connect(p)
            p = self.get_input_port(surface, PORT_EMISSION)
            if p:
                p.SetDefaultValue(1.0)

        elif channel == "opacity":
            p = self.get_input_port(surface, PORT_OPACITY)
            if p is not None:
                img_out.Connect(p)

        elif channel == "refraction":
            p = self.get_input_port(surface, PORT_TRANS_COLOR)
            if p is not None:
                img_out.Connect(p)
            p = self.get_input_port(surface, PORT_TRANSMISSION)
            if p:
                p.SetDefaultValue(1.0)

        elif channel == "height":
            disp, _ = self.find_or_add_node(graph, ARNOLD_DISP)
            p = self.get_input_port(disp, PORT_DISP_MAP)
            if p is not None:
                img_out.Connect(p)
            disp_out = self.get_first_output(disp)
            if disp_out is not None and end is not None:
                p = self.get_input_port(end, PORT_DISP_IN)
                if p is not None:
                    disp_out.Connect(p)

        elif channel == "ao":
            if correct:
                p = self.get_input_port(correct, PORT_CC_MULTIPLY)
                if p is not None:
                    img_out.Connect(p)
