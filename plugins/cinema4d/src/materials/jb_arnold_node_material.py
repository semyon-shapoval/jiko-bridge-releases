from __future__ import annotations

from src.materials import JbBaseNodeMaterial

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


class JbArnoldNodeMaterial(JbBaseNodeMaterial):
    def nodespace_id(self) -> str:
        return ARNOLD_NODESPACE

    # ------------------------------------------------------------------ #
    #  Создание материала                                                  #
    # ------------------------------------------------------------------ #

    def _get_key_nodes(self, graph) -> dict:
        return {
            "end": self.find_node(graph, ARNOLD_END),
            "surface": self.find_node(graph, ARNOLD_STANDARD),
            "correct": self.find_node(graph, ARNOLD_COLCORRECT),
        }

    def _build_default_graph(self, graph) -> dict:
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
        node = self._make_labeled_node(graph, ARNOLD_IMAGE, channel)
        port = self.get_input_port(node, PORT_IMG_FILE)
        if port is not None:
            port.SetDefaultValue(self.path_to_url(path))
        return node

    def _wire_channel(self, channel, path, graph, key_nodes) -> None:
        end = key_nodes.get("end")
        surface = key_nodes.get("surface")
        correct = key_nodes.get("correct")

        if surface is None:
            print("[JBArnoldNode] standard_surface not found")
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
            self._connect_port(img_out, nm, PORT_NM_INPUT)
            nm_out = self.get_first_output(nm)
            if nm_out is not None:
                self._connect_port(nm_out, surface, PORT_NORMAL)

        elif channel == "roughness":
            self._connect_port(img_out, surface, PORT_ROUGHNESS)

        elif channel == "metallic":
            self._connect_port(img_out, surface, PORT_METALNESS)

        elif channel == "emissive":
            self._connect_port(img_out, surface, PORT_EMIS_COLOR)
            p = self.get_input_port(surface, PORT_EMISSION)
            if p:
                p.SetDefaultValue(1.0)

        elif channel == "opacity":
            self._connect_port(img_out, surface, PORT_OPACITY)

        elif channel == "refraction":
            self._connect_port(img_out, surface, PORT_TRANS_COLOR)
            p = self.get_input_port(surface, PORT_TRANSMISSION)
            if p:
                p.SetDefaultValue(1.0)

        elif channel == "height":
            disp, _ = self.find_or_add_node(graph, ARNOLD_DISP)
            self._connect_port(img_out, disp, PORT_DISP_MAP)
            disp_out = self.get_first_output(disp)
            if disp_out is not None:
                self._connect_port(disp_out, end, PORT_DISP_IN)

        elif channel == "ao":
            if correct:
                self._connect_port(img_out, correct, PORT_CC_MULTIPLY)
