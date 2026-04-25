from __future__ import annotations
import c4d
import maxon
from scene.materials.jb_base_material import JBBaseMaterial

ASSET_ID_ATTR = "net.maxon.node.attribute.assetid"


class JBBaseNodeMaterial(JBBaseMaterial):
    """
    Базовый класс для материалов на основе нативного Maxon Node Graph API.
    Redshift и Arnold Node наследуются от него.

    Подкласс обязан определить:
        nodespace_id()          -> str   (ID node space рендера)
        node_ids()              -> dict  (словарь с ключами: output, material, texture, ...)
        _get_key_nodes(graph)   -> dict  (найти/создать ключевые узлы в графе)
        _build_default_graph(graph, transaction) -> None   (связать узлы по умолчанию)
        _wire_channel(channel, path, graph, key_nodes, transaction) -> None
    """

    # ------------------------------------------------------------------ #
    #  Хелперы — общие для любого нод-графа                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_graph(material: c4d.BaseMaterial, nodespace_id: str):
        """Возвращает граф или None если пространства нет."""
        try:
            node_mat = material.GetNodeMaterialReference()
            if node_mat is None:
                return None
            graph = node_mat.GetGraph(maxon.Id(nodespace_id))
            return None if graph.IsNullValue() else graph
        except Exception:
            return None

    @staticmethod
    def ensure_graph(material: c4d.BaseMaterial, nodespace_id: str):
        """Возвращает граф, создавая его если нужно."""
        node_mat = material.GetNodeMaterialReference()
        if node_mat is None:
            return None
        if not node_mat.HasSpace(maxon.Id(nodespace_id)):
            node_mat.AddGraph(maxon.Id(nodespace_id))
        return node_mat.GetGraph(maxon.Id(nodespace_id))

    @staticmethod
    def find_nodes_by_asset_id(graph, asset_id: str) -> list:
        """Ищет все узлы с данным asset ID через официальный GraphModelHelper.
        При неудаче — fallback через ручной обход дочерних узлов."""
        result = []
        try:
            maxon.GraphModelHelper.FindNodesByAssetId(
                graph, maxon.Id(asset_id), True, result
            )
        except Exception:
            pass

        if not result:
            for child in graph.GetRoot().GetChildren():
                if not child.IsInner():
                    continue
                try:
                    aid_val = child.GetValue(maxon.Id(ASSET_ID_ATTR))
                    aid = str(aid_val[0]) if aid_val else ""
                    if asset_id in aid:
                        result.append(child)
                except Exception:
                    continue

        return result

    @staticmethod
    def find_node(graph, asset_id: str):
        """Возвращает первый узел с данным asset ID или None."""
        result = JBBaseNodeMaterial.find_nodes_by_asset_id(graph, asset_id)
        return result[0] if result else None

    @staticmethod
    def add_node(graph, asset_id: str):
        """Добавляет новый узел в граф."""
        return graph.AddChild(maxon.Id(), maxon.Id(asset_id))

    @staticmethod
    def find_or_add_node(graph, asset_id: str):
        """Ищет узел, создаёт если не найден. Возвращает (node, was_created)."""
        node = JBBaseNodeMaterial.find_node(graph, asset_id)
        if node is not None:
            return node, False
        return JBBaseNodeMaterial.add_node(graph, asset_id), True

    @staticmethod
    def get_input_port(node, port_id: str):
        """Возвращает входной порт узла.

        Стратегия:
        1. InternedId — Redshift (порты зарегистрированы в C4D-реестре).
        2. maxon.Id — Arnold и другие сторонние рендеры (оригинальный способ).
        3. Итерация GetChildren() — последний fallback по short ID.
        """
        inputs = node.GetInputs()

        try:
            port = inputs.FindChild(maxon.InternedId(port_id))
            if port and not port.IsNullValue():
                return port
        except Exception:
            pass

        try:
            port = inputs.FindChild(maxon.Id(port_id))
            if port and not port.IsNullValue():
                return port
        except Exception:
            pass

        # Fallback: поиск по короткому имени порта
        short_id = port_id.rsplit(".", 1)[-1]
        for child in inputs.GetChildren():
            try:
                child_id = str(child.GetId())
                if child_id == port_id or child_id == short_id:
                    return child
            except Exception:
                continue

        return None

    @staticmethod
    def get_first_output(node):
        """Возвращает первый выходной порт узла."""
        outputs = node.GetOutputs().GetChildren()
        return outputs[0] if outputs else None

    @staticmethod
    def connect(src_node, dst_node, dst_port_id: str) -> bool:
        """Соединяет первый выход src_node с портом dst_port_id узла dst_node."""
        out = JBBaseNodeMaterial.get_first_output(src_node)
        inp = JBBaseNodeMaterial.get_input_port(dst_node, dst_port_id)
        if out is None or inp is None:
            return False
        out.Connect(inp)
        return True

    @staticmethod
    def path_to_url(path: str) -> maxon.Url:
        normalized = path.replace("\\", "/")
        if not normalized.startswith("/"):
            normalized = "/" + normalized
        return maxon.Url(f"file://{normalized}")

    # ------------------------------------------------------------------ #
    #  Интерфейс подкласса (abstract)                                     #
    # ------------------------------------------------------------------ #

    def _get_key_nodes(self, graph) -> dict:
        """
        Найти ключевые узлы в существующем графе.
        Возвращает словарь, например: {'material': node, 'output': node, ...}
        """
        raise NotImplementedError

    def _build_default_graph(self, graph, transaction) -> dict:
        """
        Создать базовую структуру узлов в новом графе внутри транзакции.
        Возвращает словарь ключевых узлов.
        """
        raise NotImplementedError

    def _wire_channel(
        self,
        channel: str,
        path: str,
        graph,
        key_nodes: dict,
        transaction,
    ) -> None:
        """Подключить канал к нужным портам материала."""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    #  Проверка совместимости                                             #
    # ------------------------------------------------------------------ #

    def has_compatible_graph(self, material: c4d.BaseMaterial) -> bool:
        space = self.nodespace_id()
        if space is None:
            return False
        try:
            node_mat = material.GetNodeMaterialReference()
            if node_mat is None:
                return False
            return node_mat.HasSpace(maxon.Id(space))
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Создание нового материала                                          #
    # ------------------------------------------------------------------ #

    def create(
        self,
        doc: c4d.documents.BaseDocument,
        name: str,
    ) -> c4d.BaseMaterial:
        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(name)

        graph = self.ensure_graph(material, self.nodespace_id())
        if graph is None:
            return material

        with graph.BeginTransaction() as t:
            self._build_default_graph(graph, t)
            t.Commit()

        doc.InsertMaterial(material)
        return material

    # ------------------------------------------------------------------ #
    #  Применение канала                                                  #
    # ------------------------------------------------------------------ #

    def apply_channel(
        self,
        material: c4d.BaseMaterial,
        channel: str,
        path: str,
    ) -> None:
        graph = self.get_graph(material, self.nodespace_id())
        if graph is None:
            print(f"[{self.__class__.__name__}] No graph on '{material.GetName()}'")
            return

        key_nodes = self._get_key_nodes(graph)

        # Если граф неполный (например, материал создан C4D без наших нодов) —
        # достраиваем базовую структуру прежде чем подключать каналы.
        missing = [k for k, v in key_nodes.items() if v is None]
        if missing:
            with graph.BeginTransaction() as t:
                key_nodes = self._build_default_graph(graph, t)
                t.Commit()

        with graph.BeginTransaction() as t:
            self._wire_channel(channel, path, graph, key_nodes, t)
            t.Commit()

        material.Update(True, True)
