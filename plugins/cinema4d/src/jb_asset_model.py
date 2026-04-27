"""
Asset model for Jiko Bridge plugin for C4D
Code by Semyon Shapoval, 2026
"""

import re
from typing import Any, List, Optional


class AssetInfo:
    """Represents the basic information about an asset."""

    pack_name: str
    asset_name: str
    asset_type: Optional[str]
    database_name: Optional[str]

    def __init__(
        self,
        pack_name: str,
        asset_name: str,
        asset_type: Optional[str] = None,
        database_name: Optional[str] = None,
    ):
        self.pack_name = pack_name
        self.asset_name = asset_name
        self.asset_type = asset_type
        self.database_name = database_name

    @classmethod
    def from_string(cls, value: str):
        """Parse packName / assetName from a placeholder object/tag name."""
        normalized = re.sub(r"\.\d+$", "", value)
        pattern = re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$")
        m = pattern.match(normalized)
        if m:
            return cls(
                pack_name=m.group("pack"),
                asset_name=m.group("asset"),
            )
        return None

class AssetFile:
    """Represents a file associated with an asset."""

    filepath: Optional[str]
    asset_type: Optional[str]
    bridge_type: Optional[str]

    def __init__(
        self,
        filepath: Optional[str] = None,
        asset_type: Optional[str] = None,
        bridge_type: Optional[str] = None,
    ):
        self.filepath = filepath
        self.asset_type = asset_type
        self.bridge_type = bridge_type

    @classmethod
    def from_dict(cls, data: dict):
        """Create an AssetFile instance from a dictionary."""
        return cls(
            filepath=data.get("filepath", None),
            asset_type=data.get("assetType", None),
            bridge_type=data.get("bridgeType", None),
        )

    def to_dict(self) -> dict:
        """Convert the AssetFile instance to a dictionary."""
        result = {}
        if self.filepath:
            result["filepath"] = self.filepath
        if self.asset_type:
            result["assetType"] = self.asset_type
        if self.bridge_type:
            result["bridgeType"] = self.bridge_type

        return result


class AssetModel:
    """Represents a complete asset with its metadata and associated files."""

    database_name: Optional[str]
    pack_name: Optional[str]
    asset_name: Optional[str]
    files: List[AssetFile]

    def __init__(
        self,
        database_name: Optional[str] = None,
        pack_name: Optional[str] = None,
        asset_name: Optional[str] = None,
        files: Optional[List[AssetFile]] = None,
    ):
        self.database_name = database_name
        self.pack_name = pack_name
        self.asset_name = asset_name
        self.files = files or []

    @classmethod
    def from_dict(cls, data: dict):
        """Create an AssetModel instance from a dictionary."""
        return cls(
            database_name=data.get("databaseName"),
            pack_name=data.get("packName"),
            asset_name=data.get("assetName"),
            files=[AssetFile.from_dict(f) for f in data.get("files", [])],
        )

    def to_dict(self) -> dict:
        """Convert the AssetModel instance to a dictionary."""
        result: dict[str, Any] = {}
        if self.database_name:
            result["databaseName"] = self.database_name
        if self.pack_name:
            result["packName"] = self.pack_name
        if self.asset_name:
            result["assetName"] = self.asset_name
        if self.files:
            result["files"] = [f.to_dict() for f in self.files]
        return result
