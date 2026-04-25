from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class JBSceneBase(ABC):
    """Abstract base class describing the full unified scene API.

    Both C4D and Blender implementations must satisfy this contract so that
    jb_asset_importer and jb_asset_exporter remain DCC-agnostic.
    """

    # ------------------------------------------------------------------
    # Traversal (implemented in JBTree)
    # ------------------------------------------------------------------

    @abstractmethod
    def walk(self, root, fn) -> None:
        """Call *fn* for every object/node in the hierarchy rooted at *root*."""
        pass

    @abstractmethod
    def get_children(self, container) -> list:
        """Return a flat list of all objects inside *container* (recursive)."""
        pass

    @abstractmethod
    def get_top_objects(self, scene_or_doc) -> list:
        """Return direct top-level objects of *scene_or_doc*."""
        pass

    @abstractmethod
    def get_all_objects(self, scene_or_doc) -> list:
        """Return every object in *scene_or_doc* as a flat list."""
        pass

    # ------------------------------------------------------------------
    # Selection (implemented in JBSceneSelect)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_selection(self) -> list:
        """Return the currently selected objects."""
        pass

    @abstractmethod
    def get_selected_asset_containers(self) -> list:
        """Return all selected asset containers (nulls / collections)."""
        pass

    @abstractmethod
    def get_selected_asset_container(self) -> Optional[object]:
        """Return the single unambiguous selected asset container, or None."""
        pass

    # ------------------------------------------------------------------
    # Container management (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_or_create_asset_container(self, asset) -> tuple:
        """Return (container, existed) for the given asset."""
        pass

    @abstractmethod
    def get_objects_recursive(self, container) -> list:
        """Return all objects inside *container* (recursive)."""
        pass

    @abstractmethod
    def clear_container(self, container) -> None:
        """Remove all children/objects from a container."""
        pass

    @abstractmethod
    def cleanup_empty_objects(self, container) -> None:
        """Remove empty placeholder objects from the container tree."""
        pass

    # ------------------------------------------------------------------
    # Object management (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def move_objects_to_container(self, objects: list, container) -> None:
        """Move *objects* into *container*."""
        pass

    @abstractmethod
    def has_instances(self, objects: list) -> bool:
        """Return True if any object in *objects* is an instance reference."""
        pass

    # ------------------------------------------------------------------
    # Instance management (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def create_instance(self, asset_container, name: str) -> object:
        """Create a DCC instance (Empty / Oinstance) referencing *asset_container*."""
        pass

    @abstractmethod
    def set_instance_transform(self, instance, matrix) -> None:
        """Apply a world-space transform matrix to *instance*."""
        pass

    @abstractmethod
    def add_instance_to_container(self, instance, container) -> None:
        """Parent *instance* under *container*."""
        pass

    # ------------------------------------------------------------------
    # Placeholder extraction (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def extract_placeholders(self, container) -> list:
        """Extract and return placeholder dicts from a layout container.

        Each dict has keys: ``packName``, ``assetName``, ``matrix``.
        Placeholder objects are removed from *container* during extraction.
        """
        pass

    @abstractmethod
    def get_materials_from_objects(self, objects: list) -> list:
        """Return materials assigned to the given meshes."""
        pass

    # ------------------------------------------------------------------
    # File I/O (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def import_with_temp(self, file_path: str, container) -> None:
        """Import *file_path* and place resulting objects into *container*."""
        pass

    @abstractmethod
    def export_with_temp(self, objects: list, ext: str) -> Optional[str]:
        """Export *objects* to a temporary file with the given extension.

        Returns the file path on success, None on failure.
        Instances are replaced with mesh placeholders before export.
        """
        pass
