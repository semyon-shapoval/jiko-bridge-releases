from pathlib import Path
import urllib.request
import urllib.parse
import json
import os
import platform
from typing import Optional, Dict


DEFAULT_PORT = 5174

def _get_port() -> int:
    system = platform.system()
    if system == 'Windows':
        path = os.path.join(os.getenv('APPDATA', ''), 'jiko-bridge', 'settings.json')
    elif system == 'Darwin':
        path = os.path.expanduser('~/Library/Application Support/jiko-bridge/settings.json')
    else:
        base = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        path = os.path.join(base, 'jiko-bridge', 'settings.json')

    try:
        with open(path, 'r', encoding='utf-8') as f:
            port = json.load(f).get('apiPort')
        if isinstance(port, int):
            return port
    except Exception:
        pass

    return DEFAULT_PORT


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

    def get_textures(self, res="1K") -> Dict[str, str]:
        import re

        if not self.asset_path or not os.path.exists(self.asset_path):
            return {}

        channels = ['basecolor', 'roughness', 'metallic', 'normal',
                    'emissive', 'opacity', 'refraction', 'height', 'ao']
        pattern = re.compile(r'_(%s)_(%s)' % ('|'.join(channels), res), re.IGNORECASE)

        textures = {}
        for root, _, files in os.walk(self.asset_path):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
                    match = pattern.search(filename)
                    if match:
                        textures[match.group(1).lower()] = os.path.join(root, filename)

        return textures


class JB_API:
    def __init__(self, host: str = 'localhost', port: Optional[int] = None):
        self.base_url = f"http://{host}:{port or _get_port()}"

    def _request(self, endpoint: str, payload: Optional[dict] = None,
                 method: str = "GET", timeout: int = 5) -> Optional[dict]:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode() if payload else None
        headers = {"Content-Type": "application/json"} if data else {}

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f"JB_API error: {e}")
            return None

    def _asset_from_response(self, resp: Optional[dict]) -> Optional[AssetModel]:
        data = (resp or {}).get("data")
        return AssetModel(data) if data else None

    def get_active_asset(self) -> Optional[AssetModel]:
        resp = self._request("/api/asset/active")
        asset = AssetModel(resp.get("data", {}))
        return asset

    def get_asset(self, pack_name: str, asset_name: str,
                  asset_type: str = "MODEL", path_type: str = "model") -> Optional[AssetModel]:
        params = urllib.parse.urlencode({
            "pack_name": pack_name,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "path_type": path_type,
        })
        return self._asset_from_response(self._request(f"/api/asset?{params}"))

    def create_asset(self, filepath: str) -> Optional[AssetModel]:
        return self._asset_from_response(
            self._request("/api/asset/create", {"filepath": filepath}, method="POST", timeout=300)
        )

    def update_asset(self, filepath: str, pack_name: str, asset_name: str,
                     database_name: str = "") -> Optional[dict]:
        return self._request("/api/asset/update", {
            "filepath": filepath,
            "pack_name": pack_name,
            "asset_name": asset_name,
            "database_name": database_name,
        }, method="PUT")