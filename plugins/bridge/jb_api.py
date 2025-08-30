import os
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any

from jb_models import AssetModel, ServerModel

class JB_API:
    """Jiko Bridge API Client"""
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
    
    def _make_request(
            self, 
            endpoint: str, 
            method: str = "GET", 
            data: Optional[Dict[str, Any]] = None, 
            timeout: int = 5
        ) -> Optional[Dict[str, Any]]:
        """Make a request to the Jiko Bridge server"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == "POST":
                body = json.dumps(data or {}).encode("utf-8")
                headers = {"Content-Type": "application/json"}
                req = urllib.request.Request(url, data=body, method="POST", headers=headers)
            else:
                req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                code = response.getcode()
                if 200 <= code < 300:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
                else:
                    print(f"HTTP Error: {code}")
                    return None

        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    def get_server_data(self) -> Optional[ServerModel]:
        """Get Server Data"""
        request = self._make_request("/server")
        if request:
            return ServerModel(request.get("data", {}))
        return None

    def get_asset(self, pack_name: str, asset_name: str, asset_type: str = "MODEL", path_type: str = "model") -> Optional[AssetModel]:
        """Get Asset"""
        params = urllib.parse.urlencode({
            "pack_name": pack_name,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "path_type": path_type
        })
        request = self._make_request(f"/get-asset?{params}")
        if not request:
            return None
        data = request.get("data", None)
        if not data:
            return None
        return AssetModel(data)

    def get_active_asset(self) -> Optional[AssetModel]:
        """Get Asset Information"""
        request = self._make_request("/active-asset")
        if not request:
            return None
        data = request.get("data", None)
        if not data:
            return None
        return AssetModel(data)

    def create_asset(self, filepath: str) -> Optional[AssetModel]:
        """Create Asset (wait up to 5 minutes)"""
        request = self._make_request("/create-asset", method="POST", data={"filepath": filepath}, timeout=300)
        if not request:
            return None
        data = request.get("data", None)
        if not data:
            return None
        return AssetModel(data)

    def update_asset(self, filepath: str, pack_name: str, asset_name: str) -> Optional[AssetModel]:
        """Update Asset"""
        request = self._make_request("/update-asset", method="POST", data={
            "filepath": filepath,
            "pack_name": pack_name,
            "asset_name": asset_name,
        })
        if not request:
            return None
        data = request.get("data", None)
        if not data:
            return None
        return AssetModel(data)
