import os
import re
from typing import Dict, Optional

from .jb_logger import get_logger

logger = get_logger(__name__)


class AssetModel:
    asset_path: Optional[str]
    asset_type: Optional[str]
    pack_name: Optional[str]
    asset_name: Optional[str]
    bridge_type: Optional[str]
    database_name: Optional[str]

    def __init__(self, data: dict):
        self.asset_path = data.get("asset_path")
        self.asset_type = data.get("asset_type")
        self.pack_name = data.get("pack_name")
        self.asset_name = data.get("asset_name")
        self.bridge_type = data.get("bridge_type")
        self.database_name = data.get("database_name")

    def __repr__(self):
        return f"AssetModel({self.__dict__})"

    def get_textures(self, res: str = "1K") -> Dict[str, str]:
        if not self.asset_path or not os.path.exists(self.asset_path):
            return {}

        channels = [
            "basecolor",
            "roughness",
            "metallic",
            "normal",
            "emissive",
            "opacity",
            "refraction",
            "height",
            "ao",
        ]
        pattern = re.compile(r"_(%s)_(%s)" % ("|".join(channels), res), re.IGNORECASE)

        textures: Dict[str, str] = {}
        for root, _, files in os.walk(self.asset_path):
            for filename in files:
                if filename.lower().endswith((".png", ".jpg", ".jpeg", ".tiff")):
                    match = pattern.search(filename)
                    if match:
                        textures[match.group(1).lower()] = os.path.join(root, filename)

        return textures

    @classmethod
    def from_collection(cls, collection) -> Optional["AssetModel"]:
        """Reads custom properties from a Blender collection and returns AssetModel or None."""
        pack_name = collection.get("jb_pack_name")
        asset_name = collection.get("jb_asset_name")
        asset_type = collection.get("jb_asset_type")
        database_name = collection.get("jb_database_name") or None

        if not (pack_name and asset_name and asset_type):
            logger.warning(
                "Missing asset information in collection '%s': pack_name=%s, asset_name=%s, asset_type=%s",
                collection.name,
                pack_name,
                asset_name,
                asset_type,
            )
            return None

        return cls(
            {
                "pack_name": pack_name,
                "asset_name": asset_name,
                "asset_type": asset_type,
                "database_name": database_name,
            }
        )
