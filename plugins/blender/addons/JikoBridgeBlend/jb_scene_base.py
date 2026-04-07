from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class JBSceneBase(ABC):
    """Abstract base class describing the full unified scene API.

    Both C4D and Blender implementations must satisfy this contract so that
    jb_asset_importer and jb_asset_exporter remain DCC-agnostic.

    Hierarchy:
        JBSceneBase      (this file             — abstract contract)
            └── JBTree           (jb_scene_tree.py      — traversal)
                    └── JBSceneSelect    (jb_scene_select.py    — selection)
                            └── JBSceneInstance  (jb_scene_instance.py  — instances & placeholders)
                                    └── JBSceneFileIO    (jb_scene_file_io.py  — file import/export)
                                            └── JBSceneManager   (jb_scene_manager.py  — containers & scene management)
    """

    # ------------------------------------------------------------------
    # Traversal (implemented in JBTree)
    # ------------------------------------------------------------------

    @abstractmethod
    def walk(self, root, fn) -> None:
        """Call *fn* for every object/node in the hierarchy rooted at *root*."""

    @abstractmethod
    def get_children(self, container) -> list:
        """Return a flat list of all objects inside *container* (recursive)."""

    @abstractmethod
    def get_top_objects(self, scene_or_doc) -> list:
        """Return direct top-level objects of *scene_or_doc*."""

    @abstractmethod
    def get_all_objects(self, scene_or_doc) -> list:
        """Return every object in *scene_or_doc* as a flat list."""

    # ------------------------------------------------------------------
    # Selection (implemented in JBSceneSelect)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_selection(self) -> list:
        """Return the currently selected objects."""

    @abstractmethod
    def get_selected_asset_containers(self) -> list:
        """Return all selected asset containers (nulls / collections)."""

    @abstractmethod
    def get_selected_asset_container(self) -> Optional[object]:
        """Return the single unambiguous selected asset container, or None."""

    @abstractmethod
    def confirm(self, message: str) -> bool:
        """Show a DCC confirmation dialog and return the user's answer."""

    # ------------------------------------------------------------------
    # Container management (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def get_or_create_asset_container(self, asset, target=None) -> tuple:
        """Return (container, existed) for the given asset."""

    @abstractmethod
    def get_asset_info(self, container) -> Optional[object]:
        """Read AssetModel from a container's metadata."""

    @abstractmethod
    def get_objects_recursive(self, container) -> list:
        """Return all objects inside *container* (recursive)."""

    @abstractmethod
    def clear_container(self, container) -> None:
        """Remove all children/objects from a container."""

    @abstractmethod
    def cleanup_empty_objects(self, container) -> None:
        """Remove empty placeholder objects from the container tree."""

    # ------------------------------------------------------------------
    # Object management (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def move_objects_to_container(self, objects: list, container) -> None:
        """Move *objects* into *container*."""

    @abstractmethod
    def has_instances(self, objects: list) -> bool:
        """Return True if any object in *objects* is an instance reference."""

    # ------------------------------------------------------------------
    # Instance management (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def create_instance(self, asset_container, name: str) -> object:
        """Create a DCC instance (Empty / Oinstance) referencing *asset_container*."""

    @abstractmethod
    def set_instance_transform(self, instance, matrix) -> None:
        """Apply a world-space transform matrix to *instance*."""

    @abstractmethod
    def add_instance_to_container(self, instance, container) -> None:
        """Parent *instance* under *container*."""

    # ------------------------------------------------------------------
    # Placeholder extraction (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def extract_placeholders(self, container) -> list:
        """Extract and return placeholder dicts from a layout container.

        Each dict has keys: ``pack_name``, ``asset_name``, ``matrix``.
        Placeholder objects are removed from *container* during extraction.
        """

    # ------------------------------------------------------------------
    # File I/O (implemented in JBSceneManager)
    # ------------------------------------------------------------------

    @abstractmethod
    def import_file_to_container(self, file_path: str, container) -> None:
        """Import *file_path* and place resulting objects into *container*."""

    @abstractmethod
    def export_to_temp_file(self, objects: list, ext: str) -> Optional[str]:
        """Export *objects* to a temporary file with the given extension.

        Returns the file path on success, None on failure.
        Instances are replaced with mesh placeholders before export.
        """
