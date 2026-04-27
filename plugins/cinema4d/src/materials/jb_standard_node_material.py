"""
Standard renderer node material implementation for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

from src.materials.jb_base_node_material import JbBaseNodeMaterial

C4D_NODESPACE = "net.maxon.nodespace.standard"
C4D_BSDF = "net.maxon.render.node.bsdf"
C4D_IMAGE = "net.maxon.pattern.node.generator.image"

# BSDF node input port IDs (short names)
PORT_BSDF_COLOR = "color"
PORT_BSDF_ROUGHNESS = "roughness"
PORT_BSDF_NORMAL = "normal"
PORT_BSDF_METALNESS = "reflectionstrength"  # closest analog in Standard renderer

# Material end node input port IDs
PORT_MAT_EMISSION = "emission"
PORT_MAT_ALPHA = "alpha"
PORT_MAT_DISPLACEMENT = "displacement"
PORT_MAT_TRANSPARENCY = "transparency"

# Image node port IDs
PORT_IMG_URL = "url"
PORT_IMG_RESULT = "result"


class JbStandardNodeMaterial(JbBaseNodeMaterial):
    """C4D Native Standard Renderer — node material."""

    def nodespace_id(self) -> str:
        return C4D_NODESPACE

    # ------------------------------------------------------------------ #
    #  Нахождение ключевых нодов                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find_end_node(graph):
        """Находит end-ноду по instance ID."""
        for child in graph.GetRoot().GetChildren():
            try:
                if str(child.GetId()) == "material":
                    return child
            except (AttributeError, ValueError, TypeError):
                pass
        return None

    def _get_key_nodes(self, graph) -> dict:
        bsdf_nodes = self.find_nodes_by_asset_id(graph, C4D_BSDF)
        return {
            "bsdf": bsdf_nodes[0] if bsdf_nodes else None,
            "end": self._find_end_node(graph),
        }

    def _build_default_graph(self, graph) -> dict:
        # AddGraph для net.maxon.nodespace.standard уже создаёт BSDF и end-ноду.
        # Достраивать ничего не нужно — просто возвращаем существующие ноды.
        return self._get_key_nodes(graph)

    # ------------------------------------------------------------------ #
    #  Нод изображения                                                   #
    # ------------------------------------------------------------------ #

    def _make_image_node(self, graph, channel: str, path: str):
        node = self._make_labeled_node(graph, C4D_IMAGE, channel)
        port = node.GetInputs().FindChild(PORT_IMG_URL)
        if port is not None and not port.IsNullValue():
            port.SetDefaultValue(self.path_to_url(path))
        return node

    # ------------------------------------------------------------------ #
    #  Подключение каналов                                               #
    # ------------------------------------------------------------------ #

    def _wire_channel(self, channel, path, graph, key_nodes) -> None:
        bsdf = key_nodes.get("bsdf")
        end = key_nodes.get("end")

        img = self._make_image_node(graph, channel, path)

        # Сначала ищем именованный выход result, иначе берём первый выход
        img_out = img.GetOutputs().FindChild(PORT_IMG_RESULT)
        if img_out is None or img_out.IsNullValue():
            img_out = self.get_first_output(img)
        if img_out is None:
            return

        if channel == "basecolor":
            self._connect_port(img_out, bsdf, PORT_BSDF_COLOR)

        elif channel == "roughness":
            self._connect_port(img_out, bsdf, PORT_BSDF_ROUGHNESS)

        elif channel == "normal":
            self._connect_port(img_out, bsdf, PORT_BSDF_NORMAL)

        elif channel == "metallic":
            pass

        elif channel == "emissive":
            self._connect_port(img_out, end, PORT_MAT_EMISSION)

        elif channel == "opacity":
            self._connect_port(img_out, end, PORT_MAT_ALPHA)

        elif channel == "height":
            self._connect_port(img_out, end, PORT_MAT_DISPLACEMENT)

        elif channel == "refraction":
            self._connect_port(img_out, end, PORT_MAT_TRANSPARENCY)

        elif channel == "ao":
            pass
