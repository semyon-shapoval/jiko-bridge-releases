import urllib.request
import urllib.parse
import json
from typing import Optional, Dict, Any

from jb_models import AssetModel
from jb_settings import port_from_settings

API_PREFIX = "/api"
ENDPOINT_HEALTH = API_PREFIX + "/health"
ENDPOINT_ASSET = API_PREFIX + "/asset"
ENDPOINT_ASSET_ACTIVE = ENDPOINT_ASSET + "/active"
ENDPOINT_ASSET_CREATE = ENDPOINT_ASSET + "/create"
ENDPOINT_ASSET_UPDATE = ENDPOINT_ASSET + "/update"


class JB_API:
    """Jiko Bridge API Client"""
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        host = host or 'localhost'
        port = port or port_from_settings()
        self.base_url = f"http://{host}:{port}"
    
    def _make_request(
            self,
            endpoint: str,
            payload: Optional[Dict[str, Any]] = None,
            method: str = "GET",
            timeout: int = 5,
        ) -> Optional[Dict[str, Any]]:
        """Make a JSON request to the Jiko Bridge server."""
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8") if payload else None

        headers = {}
        if data:
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = resp.read()
                return json.loads(resp_data.decode("utf-8"))
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


    def get_asset(self, pack_name: str, asset_name: str, asset_type: str = "MODEL", path_type: str = "model") -> Optional[AssetModel]:
        """Get Asset"""
        params = urllib.parse.urlencode({
            "pack_name": pack_name,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "path_type": path_type
        })
        request = self._make_request(f"{ENDPOINT_ASSET}?{params}")
        if not request:
            return None
        data = request.get("data", None)
        if not data:
            return None
        return AssetModel.from_dict(data)

    def get_active_asset(self) -> Optional[AssetModel]:
        """Get Asset Information"""
        request = self._make_request(ENDPOINT_ASSET_ACTIVE)
        if not request:
            return None
        data = request.get("data", None)
        if not data:
            return None
        return AssetModel.from_dict(data)

    def create_asset(self, filepath: str) -> Optional[AssetModel]:
        """Create Asset"""
        payload = {
            "filepath": filepath,
        }
        request = self._make_request(ENDPOINT_ASSET_CREATE, payload, method="POST", timeout=300)
        if not request:
            print(f"create_asset: no response from server (filepath={filepath})")
            return None
        data = request.get("data", None)
        if not data:
            print(f"create_asset: response missing 'data' field: {request}")
            return None
        return AssetModel.from_dict(data)

    def update_asset(self, filepath: str, pack_name: str, asset_name: str, database_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Update Asset"""
        payload = {
            "filepath": filepath,
            "pack_name": pack_name,
            "asset_name": asset_name,
            "database_name": database_name or "",
        }
        request = self._make_request(ENDPOINT_ASSET_UPDATE, payload, method="PUT")
        if not request:
            return None
        return request
