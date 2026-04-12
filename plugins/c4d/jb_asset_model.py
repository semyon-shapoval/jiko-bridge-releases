import os
import re
import c4d
from typing import Dict, Optional
from jb_logger import get_logger


logger = get_logger(__name__)

_PLACEHOLDER_PATTERNS = [
    re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$"),
    re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$"),
]


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

    def get_textures(self, res="1K") -> Dict[str, str]:
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

        textures = {}
        for root, _, files in os.walk(self.asset_path):
            for filename in files:
                if filename.lower().endswith((".png", ".jpg", ".jpeg", ".tiff")):
                    match = pattern.search(filename)
                    if match:
                        textures[match.group(1).lower()] = os.path.join(root, filename)

        return textures

    @classmethod
    def from_c4d_object(cls, obj: c4d.BaseObject) -> Optional["AssetModel"]:
        """Читает user data из c4d.BaseObject и возвращает AssetModel или None."""
        import c4d

        pack_name, asset_name, asset_type, database_name = None, None, None, None

        containers = obj.GetUserDataContainer()
        if containers:
            for key, bc in containers:
                bc_name = bc[c4d.DESC_NAME]
                if bc_name == "pack_name":
                    pack_name = obj[key]
                elif bc_name == "asset_name":
                    asset_name = obj[key]
                elif bc_name == "asset_type":
                    asset_type = obj[key]
                elif bc_name == "database_name":
                    database_name = obj[key] or None

        if not (pack_name and asset_name and asset_type):
            logger.warning(
                "Missing asset information in object '%s': pack_name=%s, asset_name=%s, asset_type=%s",
                obj.GetName(),
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

    @classmethod
    def from_placeholder_name(cls, name: str) -> Optional[dict]:
        """Parse pack_name / asset_name from a placeholder object/tag name."""
        normalized = re.sub(r"\.\d+$", "", name)
        for pattern in _PLACEHOLDER_PATTERNS:
            m = pattern.match(normalized)
            if m:
                return {"pack_name": m.group("pack"), "asset_name": m.group("asset")}
        return None
