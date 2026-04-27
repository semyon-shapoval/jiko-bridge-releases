"""
Jiko Bridge API module
Code by Semyon Shapoval, 2026
"""

import json
import os
import platform
import urllib.error
import urllib.request
from typing import List, Optional

from src.jb_logger import get_logger
from src.jb_asset_model import AssetFile, AssetModel
from src.jb_asset_model import AssetInfo

DEFAULT_PORT = 5174

logger = get_logger(__name__)


def _get_port() -> int:
    system = platform.system()
    if system == "Windows":
        path = os.path.join(os.getenv("APPDATA", ""), "jiko-bridge", "settings.json")
    elif system == "Darwin":
        path = os.path.expanduser("~/Library/Application Support/jiko-bridge/settings.json")
    else:
        base = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        path = os.path.join(base, "jiko-bridge", "settings.json")

    try:
        with open(path, "r", encoding="utf-8") as f:
            port = json.load(f).get("apiPort")
        if isinstance(port, int):
            return port
    except (OSError, json.JSONDecodeError):
        pass

    return DEFAULT_PORT


class JbAPI:
    """Client for communicating with the Jiko Bridge API server."""

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
        except urllib.error.HTTPError as e:
            logger.error("JB_API HTTP error: %s %s", e.code, e.reason)
            return None
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
            logger.exception("JB_API error: %s", e)
            return None

    def _asset_from_response(self, resp: Optional[dict]) -> Optional[AssetModel]:
        """Helper to parse an AssetModel from an API response."""
        payload = (resp or {}).get("data")
        if not payload:
            return None
        return AssetModel.from_dict(payload)

    def get_active_asset(self) -> Optional[AssetModel]:
        """Fetches the currently active asset."""
        return self._asset_from_response(self._request("/api/asset/active"))

    def get_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str] = None,
        files: Optional[List[AssetFile]] = None,
    ) -> Optional[AssetModel]:
        """Fetches a specific asset by its identifiers."""
        payload: dict = {"packName": pack_name, "assetName": asset_name}
        if database_name:
            payload["databaseName"] = database_name
        if files:
            payload["files"] = [file.to_dict() for file in files]
        return self._asset_from_response(self._request("/api/asset", payload, method="POST"))

    def get_asset_by_info(self, asset_info: AssetInfo) -> Optional[AssetModel]:
        """Fetches an asset using an AssetInfo object."""
        return self.get_asset(
            asset_info.pack_name,
            asset_info.asset_name,
            asset_info.database_name,
            [AssetFile(asset_type=asset_info.asset_type)],
        )

    def get_asset_by_search(self, search_key: str) -> Optional[AssetModel]:
        """Searches for an asset by a free-form key."""
        payload: dict = {"searchKey": search_key}
        return self._asset_from_response(self._request("/api/asset", payload, method="POST"))

    def create_asset(
        self,
        files: List[AssetFile],
        pack_name: Optional[str] = None,
        asset_name: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> Optional[AssetModel]:
        """Creates a new asset with the given files and optional metadata."""
        payload: dict = {"files": [file.to_dict() for file in files]}
        if pack_name:
            payload["packName"] = pack_name
        if asset_name:
            payload["assetName"] = asset_name
        if database_name:
            payload["databaseName"] = database_name

        return self._asset_from_response(
            self._request("/api/asset/create", payload, method="POST", timeout=300)
        )

    def update_asset(
        self,
        pack_name: str,
        asset_name: str,
        database_name: Optional[str] = None,
        files: Optional[List[AssetFile]] = None,
    ) -> Optional[dict]:
        """Updates an existing asset's files and/or metadata."""
        payload: dict = {"packName": pack_name, "assetName": asset_name}
        if files is not None:
            payload["files"] = [file.to_dict() for file in files]
        if database_name:
            payload["databaseName"] = database_name
        return self._request("/api/asset/update", payload, method="POST")
