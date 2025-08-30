import os
from typing import Dict, Literal, Optional

class ServerModel:
    def __init__(
            self, 
            data: Optional[Dict] = None
        ):
        self.server_version = data.get('server_version', None)
        self.cache_path = data.get('cache_path', None)
        self.has_active_asset = data.get('has_active_asset', False)
        self.active_asset_name = data.get('active_asset_name', None)


class AssetModel:
    def __init__(
            self, 
            data: Optional[Dict],
        ):
        self.asset_path = data.get('asset_path', None)
        self.asset_type = data.get('asset_type', None)
        self.pack_name = data.get('pack_name', None)
        self.asset_name = data.get('asset_name', None)



    @property
    def type(self):
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