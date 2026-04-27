import re
from typing import List, Optional
from jb_types import JbContainer
from .jb_logger import get_logger

logger = get_logger(__name__)


class AssetInfo:
    packName: str
    assetName: str
    assetType: Optional[str]
    databaseName: Optional[str]

    def __init__(
        self,
        packName: str,
        assetName: str,
        assetType: Optional[str] = None,
        databaseName: Optional[str] = None,
    ):
        self.packName = packName
        self.assetName = assetName
        self.assetType = assetType
        self.databaseName = databaseName

    @staticmethod
    def _normalize_placeholder_name(name: str) -> str:
        """Strip Blender auto-number suffixes like .001 from placeholder names."""
        return re.sub(r"\.\d{3,}$", "", name)

    @classmethod
    def from_string(cls, value: str):
        """Parse packName / assetName from a placeholder object/tag name."""
        normalized = cls._normalize_placeholder_name(value)
        pattern = re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$")
        m = pattern.match(normalized)
        if m:
            return cls(
                packName=m.group("pack"),
                assetName=m.group("asset"),
                assetType=None,
                databaseName=None,
            )
        return None

    @classmethod
    def from_user_data(cls, container: JbContainer):
        packName = container.get("jb_pack_name")
        assetName = container.get("jb_asset_name")
        assetType = container.get("jb_asset_type") or None
        databaseName = container.get("jb_database_name") or None

        if not (packName and assetName):
            return None

        return cls(
            packName,
            assetName,
            assetType,
            databaseName,
        )


class AssetFile:
    filepath: Optional[str]
    assetType: Optional[str]
    bridgeType: Optional[str]

    def __init__(
        self,
        filepath: Optional[str] = None,
        assetType: Optional[str] = None,
        bridgeType: Optional[str] = None,
    ):
        self.filepath = filepath
        self.assetType = assetType
        self.bridgeType = bridgeType

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            filepath=data.get("filepath", None),
            assetType=data.get("assetType", None),
            bridgeType=data.get("bridgeType", None),
        )

    def to_dict(self) -> dict:
        result = {}
        if self.filepath:
            result["filepath"] = self.filepath
        if self.assetType:
            result["assetType"] = self.assetType
        if self.bridgeType:
            result["bridgeType"] = self.bridgeType

        return result


class AssetModel:
    databaseName: Optional[str]
    packName: Optional[str]
    assetName: Optional[str]
    files: List[AssetFile]

    def __init__(
        self,
        databaseName: Optional[str] = None,
        packName: Optional[str] = None,
        assetName: Optional[str] = None,
        files: Optional[List[AssetFile]] = None,
    ):
        self.databaseName = databaseName
        self.packName = packName
        self.assetName = assetName
        self.files = files or []

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            databaseName=data.get("databaseName"),
            packName=data.get("packName"),
            assetName=data.get("assetName"),
            files=[AssetFile.from_dict(f) for f in data.get("files", [])],
        )

    def to_dict(self) -> dict:
        result = {}
        if self.databaseName:
            result["databaseName"] = self.databaseName
        if self.packName:
            result["packName"] = self.packName
        if self.assetName:
            result["assetName"] = self.assetName
        if self.files:
            result["files"] = [f.to_dict() for f in self.files]
        return result
