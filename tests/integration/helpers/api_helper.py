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

    def injected_create_asset(*args, **kwargs) -> Any:
        if len(args) >= 2:
            filepath = args[1]
        elif len(args) == 1:
            filepath = args[0] if isinstance(args[0], str) else kwargs.get("filepath")
        else:
            filepath = kwargs.get("filepath")

        if filepath is None:
            raise TypeError("create_asset was called without a filepath")

        kwargs.update(payload)
        payload_capture["payload"] = dict(filepath=filepath, **payload)
        return original_create_asset(*args, **kwargs)

    return payload_capture, injected_create_asset


def make_injected_active_asset(
    payload: dict[str, Any],
    host: str = "localhost",
    port: int = 5174,
) -> Callable[..., Any]:
    def injected_active_asset(*_args, **_kwargs) -> SimpleNamespace | None:
        query = {k: v for k, v in payload.items() if v is not None}
        data = http_request("/api/asset", query, host=host, port=port)
        if not data or data.get("data") is None:
            return None
        return SimpleNamespace(**data["data"])

    return injected_active_asset
