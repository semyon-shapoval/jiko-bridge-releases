import re
import c4d
from typing import List, Optional
from jb_logger import get_logger


logger = get_logger(__name__)

_PLACEHOLDER_PATTERNS = [
    re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$"),
    re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$"),
]

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

    @classmethod
    def from_placeholder_name(cls, name: str):
        """Parse packName / assetName from a placeholder object/tag name."""
        normalized = re.sub(r"\.\d+$", "", name)
        for pattern in _PLACEHOLDER_PATTERNS:
            m = pattern.match(normalized)
            if m:
                return AssetInfo(
                    packName=m.group("pack"),
                    assetName=m.group("asset"),
                    assetType=None,
                    databaseName=None,
                )
        return None

    @staticmethod
    def get_asset_info(obj: c4d.BaseObject):
        """Reads packName, assetName, assetType, databaseName from object user data."""
        packName = assetName = assetType = databaseName = None

        for key, bc in obj.GetUserDataContainer() or []:
            bc_name = bc[c4d.DESC_NAME]
            if bc_name == "packName":
                packName = obj[key]
            elif bc_name == "assetName":
                assetName = obj[key]
            elif bc_name == "assetType":
                assetType = obj[key] or None
            elif bc_name == "databaseName":
                databaseName = obj[key] or None

        if not (packName and assetName):
            return None

        return AssetInfo(
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

    def __init__(self, 
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
            files=[AssetFile.from_dict(f) for f in data.get("files", [])]
        )

    def to_dict(self) -> dict:
        return {
            "databaseName": self.databaseName,
            "packName": self.packName,
            "assetName": self.assetName,
            "files": [f.to_dict() for f in self.files],
        }
