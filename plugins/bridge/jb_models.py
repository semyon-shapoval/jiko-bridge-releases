import os
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Mapping


@dataclass(frozen=True)
class AssetModel:
    """Represents an asset returned from the Jiko Bridge API."""

    asset_path: Optional[str] = None
    asset_type: Optional[str] = None
    pack_name: Optional[str] = None
    asset_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AssetModel":
        return cls(
            
            asset_path=data.get("asset_path"),
            asset_type=data.get("asset_type"),
            pack_name=data.get("pack_name"),
            asset_name=data.get("asset_name"),
        )

    @property
    def type(self) -> Optional[str]:
        ext = self.ext
        if ext == ".fbx":
            return "Assets"
        elif ext == ".abc":
            return "Layout"
        else:
            return None

    @property
    def ext(self):
        if self.asset_path:
            return os.path.splitext(self.asset_path)[1].lower()
        else:
            return None

    def get_textures(self, res: Literal["1K", "2K", "4K"] = "1K"):
        """Get texture file paths from the asset directory."""
        import re

        if not self.asset_path or not os.path.exists(self.asset_path):
            return {}

        textures = {}
        channels = [
            'basecolor',
            'roughness',
            'metallic',
            'normal',
            'emissive',
            'opacity',
            'refraction',
            'height',
            'ao'
        ]

        pattern = re.compile(r'_(%s)_(%s)' % ('|'.join(channels), res), re.IGNORECASE)

        for root, dirs, files in os.walk(self.asset_path):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
                    match = pattern.search(filename)
                    if match:
                        channel = match.group(1).lower()
                        textures[channel] = os.path.join(root, filename)

        return textures