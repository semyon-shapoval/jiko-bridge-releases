"""
Universal protocol for Jiko Bridge.
Code by Semyon Shapoval, 2026
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Protocol, Callable, Generator, Literal, Optional, TypedDict

from .jb_types import (
    AssetInfo,
    AssetFile,
    AssetModel,
    JbContainer,
    JbMaterial,
    JbMatrix,
    JbObject,
    JbScene,
    JbSource,
)


class JbPlaceholderInfo(TypedDict):
    """Represents information about a placeholder object."""

    pack: str
    asset: str
    transform: JbMatrix


class JbSceneABC(ABC):  # pylint: disable=too-many-public-methods
    """Abstract base class for all Jiko Bridge scene operations."""

    # ------------------------------------------------------------------
    # Base
    # ------------------------------------------------------------------

    @abstractmethod
    def __init__(self, source: JbSource): ...

    @property
    @abstractmethod
    def source(self) -> JbSource:
        """Return the source scene."""

    @property
    @abstractmethod
    def logger(self) -> Logger:
        """Return the logger instance."""

    # ------------------------------------------------------------------
    # Scene Objects
    # ------------------------------------------------------------------

    @abstractmethod
    def walk(
        self,
        root: JbContainer | JbObject | list[JbObject],
        fn: Callable[[JbObject], None],
    ) -> None:
        """Call *fn* for every object in the root hierarchy (pre-order)."""

    @abstractmethod
    def get_selection(
        self, select_type: Literal["objects", "recursive", "materials"] = "objects"
    ) -> list[JbObject | JbMaterial]:
        """Return the currently selected objects or materials."""

    @abstractmethod
    def get_materials_from_objects(self, objects: list[JbObject]) -> list[JbMaterial]:
        """Return materials used by the given objects."""

    @abstractmethod
    def get_objects(
        self,
        objects_type: Literal["all", "top"] = "all",
        root: Optional[JbContainer | JbObject | list[JbObject]] = None,
    ) -> list[JbObject]:
        """Return objects of the active scene, either all or top-level."""

    @abstractmethod
    def set_object_transform(self, obj: JbObject, matrix) -> None:
        """Set the transform of the given object."""

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    @abstractmethod
    def get_or_create_container(
        self, name: str, parent: Optional[JbContainer] = None
    ) -> JbContainer:
        """Get or create a container with the given name under the parent."""

    @abstractmethod
    def get_or_create_asset_container(
        self,
        asset: AssetModel,
        file: Optional[AssetFile] = None,
    ) -> tuple[JbContainer, bool]:
        """Get or create a container with asset data."""

    @abstractmethod
    def set_asset_data(
        self, col: JbContainer, asset: AssetModel, file: Optional[AssetFile] = None
    ) -> None:
        """Store asset info in the container's custom properties."""

    @abstractmethod
    def get_asset_data_from_container(self, container: JbContainer) -> Optional[AssetInfo]:
        """Parse asset info from a container's custom properties."""

    @abstractmethod
    def copy_asset_data(self, src: JbContainer, dst: JbContainer | JbObject) -> None:
        """Copy custom properties from src to dst."""

    @abstractmethod
    def filter_containers_from_objects(self, objects: list[JbObject]) -> list[JbContainer]:
        """Return asset containers found among the given objects (via instance Empties)."""

    @abstractmethod
    def move_objects_to_container(self, objects: list[JbObject], container: JbContainer) -> None:
        """Move objects into target collection."""

    @abstractmethod
    def clear_container(self, container: JbContainer) -> None:
        """Remove all objects from the container."""

    @abstractmethod
    def cleanup_empty_objects(self, container: JbContainer) -> None:
        """Remove empty objects that have no children and no data."""

    # ------------------------------------------------------------------
    # Instance
    # ------------------------------------------------------------------

    @abstractmethod
    def create_instance(self, container: JbContainer, name: str) -> JbObject:
        """Create an instance of the given object."""

    @abstractmethod
    def add_instance_to_container(self, instance: JbObject, container: JbContainer) -> None:
        """Add an instance to a container."""

    @abstractmethod
    def extract_placeholders(self, container: JbContainer) -> list[JbPlaceholderInfo]:
        """Extract placeholder info from objects and remove them."""

    @abstractmethod
    def replace_instances_with_placeholders(
        self, objects: list[JbObject], scene: JbScene
    ) -> list[JbObject]:
        """Replace instances in the list with placeholders."""

    @abstractmethod
    def create_placeholder(
        self,
        placeholder_info: JbPlaceholderInfo,
        scene: JbScene,
    ) -> Optional[JbObject]:
        """Create a placeholder object in the scene based on the info."""

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    @abstractmethod
    def import_file(self, file_path: str) -> bool:
        """Import a file into the active scene."""

    @abstractmethod
    def _import_fbx(self, file_path: str) -> bool: ...

    @abstractmethod
    def export_file(self, ext: str) -> Optional[str]:
        """Export the active scene to a file and return its path."""

    @abstractmethod
    def _export_fbx(self, file_path: str) -> Optional[str]: ...

    # ------------------------------------------------------------------
    # Temp Scene
    # ------------------------------------------------------------------

    @abstractmethod
    def temp_scene(
        self,
        src: Optional[JbContainer | list[JbObject]] = None,
        unit_scale: float = 1.0,
        debug: bool = False,
    ) -> Generator[JbScene, None, None]:
        """Context manager for temporary scenes."""

    @abstractmethod
    def _cleanup_temp_scene(self, temp: JbScene, objects: list[JbObject]) -> None: ...

    # ------------------------------------------------------------------
    # Scene (high-level)
    # ------------------------------------------------------------------

    @abstractmethod
    def import_with_temp(self, file_path: str, target: JbContainer) -> None:
        """Import a file into an isolated scene, then copy to target collection."""

    @abstractmethod
    def export_with_temp(
        self,
        src: JbContainer | list[JbObject],
        ext: str,
    ) -> Optional[str]:
        """Copy objects to isolated scene, replace instances, export."""


# Asset Protocols


class JbAssetImporterProtocol(Protocol):
    """Protocol for Asset Importers."""

    def __init__(self, _source: JbSource): ...
    def import_assets(self) -> None:
        """Imports assets by selection."""

    def _collect_materials(self, objects: list[JbObject]) -> list[JbMaterial]: ...
    def _collect_assets_for_reimport(self, objects: list[JbObject]) -> list: ...
    def _collect_active_asset(self, objects: list[JbObject]) -> list: ...
    def _import_single(self, asset: AssetModel) -> None: ...
    def _create_model(self, asset: AssetModel, file: AssetFile) -> JbContainer: ...
    def _convert_to_instances(self, layout_container: JbContainer) -> None: ...


class JbAssetExporterProtocol(Protocol):
    """Protocol for Asset Exporters."""

    def __init__(self, source: JbSource): ...
    def export_asset(self) -> None:
        """Exports an asset from the scene into Jiko Bridge."""

    def _update_asset(self, container: JbContainer) -> None: ...
    def _create_new_asset(self, objects: list[JbObject]) -> None: ...


class JbAPIProtocol(Protocol):
    """Protocol for Jiko Bridge API interactions."""

    def get_active_asset(self) -> Optional[AssetModel]:
        """Get the currently active asset based on selection or context."""

    def get_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str],
        files: Optional[list[AssetFile]],
    ) -> Optional[AssetModel]:
        """Get Asset by its identifiers."""

    def get_asset_by_info(self, asset_info: AssetInfo) -> Optional[AssetModel]:
        """Get Asset by an AssetInfo object."""

    def get_asset_by_search(self, search_key: str) -> Optional[AssetModel]:
        """Search for an Asset by a free-form key."""

    def create_asset(
        self,
        files: list[AssetFile],
        pack_name: Optional[str],
        asset_name: Optional[str],
        database_name: Optional[str],
    ) -> Optional[AssetModel]:
        """Create a new Asset with the given files and optional metadata."""

    def update_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str],
        files: Optional[list[AssetFile]],
    ) -> Optional[AssetModel]:
        """Update an existing Asset's files and metadata."""
