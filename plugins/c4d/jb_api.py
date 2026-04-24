import os
import json
import platform
import urllib.request
import urllib.parse
from typing import List, Optional

from jb_logger import get_logger
from jb_asset_model import AssetModel, AssetExportFile


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
                parsed = json.loads(resp.read().decode())
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                logger.debug("API response: %s %s\n%s", method, endpoint, pretty)
                return parsed
        except Exception as e:
            logger.exception(f"JB_API error: {e}")
            return None

    def _asset_from_response(self, resp: Optional[dict]) -> Optional[AssetModel]:
        payload = (resp or {}).get("data")
        if not payload:
            return None
        return AssetModel(payload)

    def get_active_asset(self) -> Optional[AssetModel]:
        return self._asset_from_response(self._request("/api/asset/active"))

    def get_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str] = None,
        asset_types: Optional[List[str]] = None,
    ) -> Optional[AssetModel]:
        query: dict = {"pack_name": pack_name, "asset_name": asset_name}
        if database_name:
            query["database_name"] = database_name
        params = urllib.parse.urlencode(query)
        if asset_types:
            params += "&" + urllib.parse.urlencode(
                [("asset_type", t) for t in asset_types]
            )
        return self._asset_from_response(self._request(f"/api/asset?{params}"))

    def create_asset(
        self,
        filepath: str,
        pack_name: Optional[str] = None,
        asset_name: Optional[str] = None,
        database_name: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> Optional[AssetModel]:
        payload: dict = {"filepath": filepath}
        if pack_name:
            payload["pack_name"] = pack_name
        if asset_name:
            payload["asset_name"] = asset_name
        if database_name:
            payload["database_name"] = database_name
        if asset_type:
            payload["asset_type"] = asset_type

        return self._asset_from_response(
            self._request("/api/asset/create", payload, method="POST", timeout=300)
        )

    def update_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str] = None,
        files: Optional[List[AssetExportFile]] = None,
    ) -> Optional[dict]:
        payload: dict = {
            "pack_name": pack_name,
            "asset_name": asset_name,
            "files": files
        }
        if database_name:
            payload["database_name"] = database_name
        return self._request("/api/asset/update", payload, method="POST")
