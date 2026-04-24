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
    pack_name: str
    asset_name: str
    asset_type: Optional[str]
    database_name: Optional[str]

    @classmethod
    def from_placeholder_name(cls, name: str):
        """Parse pack_name / asset_name from a placeholder object/tag name."""
        normalized = re.sub(r"\.\d+$", "", name)
        for pattern in _PLACEHOLDER_PATTERNS:
            m = pattern.match(normalized)
            if m:
                return AssetInfo(
                    pack_name=m.group("pack"),
                    asset_name=m.group("asset"),
                    asset_type=None,
                    database_name=None,
                )
        return None

    @staticmethod
    def get_asset_info(obj: c4d.BaseObject):
        """Reads pack_name, asset_name, asset_type, database_name from object user data."""
        pack_name = asset_name = asset_type = database_name = None

        for key, bc in obj.GetUserDataContainer() or []:
            bc_name = bc[c4d.DESC_NAME]
            if bc_name == "pack_name":
                pack_name = obj[key]
            elif bc_name == "asset_name":
                asset_name = obj[key]
            elif bc_name == "asset_type":
                asset_type = obj[key] or None
            elif bc_name == "database_name":
                database_name = obj[key] or None

        if not (pack_name and asset_name):
            return None

        return AssetInfo(
            pack_name=pack_name,
            asset_name=asset_name,
            asset_type=asset_type,
            database_name=database_name,
        )


class AssetFile:
    def __init__(self, data: dict):
        self.file_path: str = data.get("filePath", "")
        self.asset_type: str = data.get("assetType", "")
        self.bridge_type: str = data.get("bridgeType", "")

    def __repr__(self):
        return f"AssetFile({self.__dict__})"

class AssetExportFile:
    def __init__(self, file_path: str, asset_type: str):
        self.file_path = file_path
        self.asset_type = asset_type

    def to_dict(self) -> dict:
        return {
            "filePath": self.file_path,
            "assetType": self.asset_type,
        }

class AssetModel:
    database_name: Optional[str]
    pack_name: Optional[str]
    asset_name: Optional[str]
    files: List[AssetFile]

    def __init__(self, data: dict):
        self.database_name = data.get("database_name")
        self.pack_name = data.get("pack_name")
        self.asset_name = data.get("asset_name")
        self.files = [AssetFile(f) for f in data.get("files", [])]

    def __repr__(self):
        return f"AssetModel({self.__dict__})"
