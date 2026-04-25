from copy import copy
from inspect import signature
from typing import Any, Callable
import sys
import urllib.request as urllib_request
import json


def http_request(
    endpoint: str,
    payload: dict[str, Any],
    host: str = "localhost",
    port: int = 5174,
    timeout: int = 10,
) -> dict[str, Any] | None:
    url = f"http://{host}:{port}{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib_request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def _positional_param_names(func: Callable) -> list[str]:
    try:
        return [
            p.name
            for p in signature(func).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
    except (TypeError, ValueError):
        return []


def _enrich_file_list(
    actual_files: list[Any],
    payload_files: list[dict[str, Any]],
) -> list[Any]:
    """Обогащает список объектов-файлов данными из пейлоада."""
    enriched = []
    for i, f in enumerate(actual_files):
        pf = payload_files[i] if i < len(payload_files) else {}
        if pf:
            f = copy(f)
            for k, v in pf.items():
                if v is not None:
                    setattr(f, k, v)
        enriched.append(f)
    return enriched


def make_injected_create_asset(
    payload: dict[str, Any],
    original_create_asset: Callable[..., Any],
) -> tuple[dict[str, Any], Callable[..., Any]]:
    payload_capture: dict[str, Any] = {}

    def injected_create_asset(*args: Any, **kwargs: Any) -> Any:
        positional_keys = _positional_param_names(original_create_asset)[: len(args)]
        merged = kwargs | {k: v for k, v in payload.items() if k not in positional_keys}

        args = list(args)
        if "files" in payload and "files" in positional_keys:
            files_idx = positional_keys.index("files")
            args[files_idx] = _enrich_file_list(list(args[files_idx]), payload["files"])
        args = tuple(args)

        payload_capture["payload"] = merged.copy()
        return original_create_asset(*args, **merged)

    return payload_capture, injected_create_asset


def make_injected_active_asset(
    payload: dict[str, Any],
    host: str = "localhost",
    port: int = 5174,
) -> Callable[..., Any]:
    def injected_active_asset(*_args, **_kwargs) -> Any:
        body = {k: v for k, v in payload.items() if v is not None}
        data = http_request("/api/asset", body, host=host, port=port)
        if not data or data.get("data") is None:
            return None
        asset_model_module = sys.modules.get("jb_asset_model")
        if asset_model_module and hasattr(asset_model_module, "AssetModel"):
            return asset_model_module.AssetModel.from_dict(data["data"])
        return data["data"]

    return injected_active_asset
