from __future__ import annotations
import c4d
import maxon
from scene.materials.jb_base_node_material import JBBaseNodeMaterial

C4D_NODESPACE = "net.maxon.nodespace.standard"
C4D_BSDF = "net.maxon.render.node.bsdf"
C4D_IMAGE = "net.maxon.pattern.node.generator.image"

NODE_NAME_ID = "net.maxon.node.base.name"

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


class JBCinema4DNodeMaterial(JBBaseNodeMaterial):
    """C4D Native Standard Renderer — node material (net.maxon.nodespace.standard)."""

    def id(self) -> int:
        return c4d.Mmaterial

    def nodespace_id(self) -> str:
        return C4D_NODESPACE

    # ------------------------------------------------------------------ #
    #  Нахождение ключевых нодов                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _find_end_node(graph):
        """Находит end-ноду стандартного графа по её instance ID 'material'."""
        for child in graph.GetRoot().GetChildren():
            try:
                if str(child.GetId()) == "material":
                    return child
            except Exception:
                pass
        return None

    def _get_key_nodes(self, graph) -> dict:
        bsdf_nodes: list = []
        try:
            maxon.GraphModelHelper.FindNodesByAssetId(
                graph, maxon.Id(C4D_BSDF), True, bsdf_nodes
            )
        except Exception:
            pass

        return {
            "bsdf": bsdf_nodes[0] if bsdf_nodes else None,
            "end": self._find_end_node(graph),
        }

    def _build_default_graph(self, graph, transaction) -> dict:
        # AddGraph для net.maxon.nodespace.standard уже создаёт BSDF и end-ноду.
        # Достраивать ничего не нужно — просто возвращаем существующие ноды.
        return self._get_key_nodes(graph)

    # ------------------------------------------------------------------ #
    #  Нод изображения                                                   #
    # ------------------------------------------------------------------ #

    def _make_image_node(self, graph, channel: str, path: str):
        """Находит image-ноду для канала или создаёт новую."""
        existing = self.find_nodes_by_asset_id(graph, C4D_IMAGE)
        for node in existing:
            try:
                name_val = node.GetValue(NODE_NAME_ID)
                if str(name_val) == channel:
                    port = node.GetInputs().FindChild(PORT_IMG_URL)
                    if port is not None and not port.IsNullValue():
                        port.SetDefaultValue(self.path_to_url(path))
                    return node
            except Exception:
                pass

        node = self.add_node(graph, C4D_IMAGE)
        try:
            node.SetValue(NODE_NAME_ID, maxon.String(channel))
        except Exception:
            pass
        port = node.GetInputs().FindChild(PORT_IMG_URL)
        if port is not None and not port.IsNullValue():
            port.SetDefaultValue(self.path_to_url(path))
        return node

    # ------------------------------------------------------------------ #
    #  Подключение каналов                                               #
    # ------------------------------------------------------------------ #

    def _wire_channel(self, channel, path, graph, key_nodes, transaction) -> None:
        bsdf = key_nodes.get("bsdf")
        end = key_nodes.get("end")

        img = self._make_image_node(graph, channel, path)

        # Сначала ищем именованный выход result, иначе берём первый выход
        img_out = img.GetOutputs().FindChild(PORT_IMG_RESULT)
        if img_out is None or img_out.IsNullValue():
            img_out = self.get_first_output(img)
        if img_out is None:
            return

        def wire(node, port_id: str) -> None:
            if node is None:
                return
            port = self.get_input_port(node, port_id)
            if port is not None:
                img_out.Connect(port)

        if channel == "basecolor":
            wire(bsdf, PORT_BSDF_COLOR)

        elif channel == "roughness":
            wire(bsdf, PORT_BSDF_ROUGHNESS)

        elif channel == "normal":
            wire(bsdf, PORT_BSDF_NORMAL)

        elif channel == "metallic":
            # Standard renderer не имеет metalness.
            # Используем reflectionstrength как ближайший аналог.
            wire(bsdf, PORT_BSDF_METALNESS)

        elif channel == "emissive":
            wire(end, PORT_MAT_EMISSION)

        elif channel == "opacity":
            wire(end, PORT_MAT_ALPHA)

        elif channel == "height":
            wire(end, PORT_MAT_DISPLACEMENT)

        elif channel == "refraction":
            wire(end, PORT_MAT_TRANSPARENCY)

        elif channel == "ao":
            # AO нет прямого аналога в стандартном рендере — пропускаем
            pass
