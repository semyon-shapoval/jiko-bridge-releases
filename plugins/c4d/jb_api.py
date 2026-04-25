import json
import os
import platform
import urllib.error
import urllib.request
from typing import List, Optional

from jb_logger import get_logger
from jb_asset_model import AssetFile, AssetModel


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
        except urllib.error.HTTPError as e:
            logger.error("JB_API HTTP error: %s %s", e.code, e.reason)
            return None
        except Exception as e:
            logger.exception("JB_API error: %s", e)
            return None

    def _asset_from_response(self, resp: Optional[dict]) -> Optional[AssetModel]:
        payload = (resp or {}).get("data")
        if not payload:
            return None
        return AssetModel.from_dict(payload)

    def get_active_asset(self) -> Optional[AssetModel]:
        return self._asset_from_response(self._request("/api/asset/active"))

    def get_asset(
        self,
        packName: str,
        assetName: str,
        databaseName: Optional[str] = None,
        files: Optional[List[AssetFile]] = None,
    ) -> Optional[AssetModel]:
        payload: dict = {"packName": packName, "assetName": assetName}
        if databaseName:
            payload["databaseName"] = databaseName
        if files:
            payload["files"] = [file.to_dict() for file in files]
        return self._asset_from_response(
            self._request("/api/asset", payload, method="POST")
        )

    def get_asset_by_search(
        self,
        searchKey: str
    ) -> Optional[AssetModel]:
        payload: dict = {"searchKey": searchKey}
        return self._asset_from_response(
            self._request("/api/asset", payload, method="POST")
        )

    def create_asset(
        self,
        files: List[AssetFile],
        packName: Optional[str] = None,
        assetName: Optional[str] = None,
        databaseName: Optional[str] = None,
    ) -> Optional[AssetModel]:
        payload: dict = {"files": [file.to_dict() for file in files]}
        if packName:
            payload["packName"] = packName
        if assetName:
            payload["assetName"] = assetName
        if databaseName:
            payload["databaseName"] = databaseName

        return self._asset_from_response(
            self._request("/api/asset/create", payload, method="POST", timeout=300)
        )

    def update_asset(
        self,
        packName: str,
        assetName: str,
        databaseName: Optional[str] = None,
        files: Optional[List[AssetFile]] = None,
    ) -> Optional[dict]:
        payload: dict = {"packName": packName, "assetName": assetName}
        if files is not None:
            payload["files"] = [file.to_dict() for file in files]
        if databaseName:
            payload["databaseName"] = databaseName
        return self._request("/api/asset/update", payload, method="POST")
