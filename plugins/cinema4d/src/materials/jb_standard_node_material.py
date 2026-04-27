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

    @property
    def _bsdf(self):
        nodes = self.find_nodes_by_asset_id(self._graph, C4D_BSDF)
        return nodes[0] if nodes else None

    @property
    def _end(self):
        for child in self._graph.GetRoot().GetChildren():
            try:
                if str(child.GetId()) == "material":
                    return child
            except (AttributeError, ValueError, TypeError):
                pass
        return None

    def _make_image_node(self, channel: str, path: str):
        node = self._make_labeled_node(self._graph, C4D_IMAGE, channel)
        port = node.GetInputs().FindChild(PORT_IMG_URL)
        if port is not None and not port.IsNullValue():
            port.SetDefaultValue(self.path_to_url(path))
        return node

    def _get_img_out(self, img):
        out = img.GetOutputs().FindChild(PORT_IMG_RESULT)
        if out is None or out.IsNullValue():
            out = self.get_first_output(img)
        return out

    def _wire_basecolor(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("basecolor", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._bsdf, PORT_BSDF_COLOR)

    def _wire_roughness(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("roughness", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._bsdf, PORT_BSDF_ROUGHNESS)

    def _wire_normal(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("normal", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._bsdf, PORT_BSDF_NORMAL)

    def _wire_emissive(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("emissive", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_EMISSION)

    def _wire_opacity(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("opacity", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_ALPHA)

    def _wire_height(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("height", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_DISPLACEMENT)

    def _wire_refraction(self, path) -> None:
        img_out = self._get_img_out(self._make_image_node("refraction", path))
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_TRANSPARENCY)
