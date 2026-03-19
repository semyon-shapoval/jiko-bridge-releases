from urllib import response
import urllib.request
import urllib.parse
import json
import os
import platform
from typing import Optional

from .jb_asset_model import AssetModel
from .jb_logger import get_logger

DEFAULT_PORT = 5174

logger = get_logger(__name__)

def _get_port() -> int:
    system = platform.system()
    if system == "Windows":
        path = os.path.join(os.getenv("APPDATA", ""), "jiko-bridge", "settings.json")
    elif system == "Darwin":
        path = os.path.expanduser(
            "~/Library/Application Support/jiko-bridge/settings.json"
        )
    else:
        base = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        path = os.path.join(base, "jiko-bridge", "settings.json")

    try:
        with open(path, "r", encoding="utf-8") as f:
            port = json.load(f).get("apiPort")
        if isinstance(port, int):
            return port
    except Exception:
        pass

    return DEFAULT_PORT


class JB_API:
    def __init__(self, host: str = "localhost", port: Optional[int] = None):
        self.base_url = f"http://{host}:{port or _get_port()}"

    def _request(
        self,
        endpoint: str,
        payload: Optional[dict] = None,
        method: str = "GET",
        timeout: int = 5,
    ) -> Optional[dict]:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode() if payload else None
        headers = {"Content-Type": "application/json"} if data else {}

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                logger.debug("Making API request: %s %s %s %s", method, url, data, resp)
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error("API request failed: %s", e)
            return None


    def _asset_from_response(self, resp: Optional[dict]) -> Optional[AssetModel]:
        data = (resp or {}).get("data")
        return AssetModel(data) if data else None

    def get_active_asset(self) -> Optional[AssetModel]:
        return self._asset_from_response(self._request("/api/asset/active"))

    def get_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> Optional[AssetModel]:
        query: dict = {"pack_name": pack_name, "asset_name": asset_name}
        if database_name:
            query["database_name"] = database_name
        if asset_type:
            query["asset_type"] = asset_type
        params = urllib.parse.urlencode(query)
        return self._asset_from_response(self._request(f"/api/asset?{params}"))

    def create_asset(self, filepath: str) -> Optional[AssetModel]:
        return self._asset_from_response(
            self._request(
                "/api/asset/create", {"filepath": filepath}, method="POST", timeout=300
            )
        )

    def update_asset(
        self,
        filepath: str,
        pack_name: str,
        asset_name: str,
        asset_type: str,
        database_name: Optional[str] = None,
    ) -> Optional[dict]:
        payload: dict = {
            "filepath": filepath,
            "pack_name": pack_name,
            "asset_name": asset_name,
            "asset_type": asset_type,
        }
        if database_name:
            payload["database_name"] = database_name
        return self._request("/api/asset/update", payload, method="POST")
