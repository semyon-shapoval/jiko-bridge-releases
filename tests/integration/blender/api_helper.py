from types import SimpleNamespace
from typing import Any, Callable
import urllib.request as urllib_request
from urllib import parse
import json


def http_request(
    endpoint: str,
    query: dict[str, Any],
    host: str = "localhost",
    port: int = 5174,
    timeout: int = 10,
) -> dict[str, Any] | None:
    url = f"http://{host}:{port}{endpoint}?{parse.urlencode(query)}"
    req = urllib_request.Request(url, headers={"Content-Type": "application/json"})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def make_injected_create_asset(
    payload: dict[str, Any],
    original_create_asset: Callable[..., Any],
) -> tuple[dict[str, Any], Callable[..., Any]]:
    payload_capture: dict[str, Any] = {}

    def injected_create_asset(api_self, filepath: str, *args, **kwargs) -> Any:
        kwargs.update(payload)
        payload_capture["payload"] = dict(filepath=filepath, **payload)
        return original_create_asset(api_self, filepath, *args, **kwargs)

    return payload_capture, injected_create_asset


def make_injected_active_asset(
    payload: dict[str, Any],
    host: str = "localhost",
    port: int = 5174,
) -> Callable[..., Any]:
    def injected_active_asset(api_self) -> SimpleNamespace | None:
        query = {k: v for k, v in payload.items() if v is not None}
        data = http_request("/api/asset", query, host=host, port=port)
        if not data or data.get("data") is None:
            return None
        return SimpleNamespace(**data["data"])

    return injected_active_asset
