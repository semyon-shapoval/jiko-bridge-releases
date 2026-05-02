"""
Api helper
Code by Semyon Shapoval, 2026
"""

import importlib
from copy import copy
from inspect import signature
from typing import Any, Callable


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
    """Mock for files creation asset api"""
    payload_capture: dict[str, Any] = {}
    original_signature = signature(original_create_asset)

    def injected_create_asset(*args: Any, **kwargs: Any) -> Any:
        bound_args = original_signature.bind_partial(*args, **kwargs)
        merged = dict(bound_args.arguments)

        for key, value in payload.items():
            if value is None:
                continue
            if key == "files" and key in merged:
                merged["files"] = _enrich_file_list(list(merged["files"]), value)
            elif key not in merged:
                merged[key] = value

        payload_capture["payload"] = merged.copy()
        return original_create_asset(**merged)

    return payload_capture, injected_create_asset


def make_injected_active_asset(
    payload: dict[str, Any],
) -> Callable[..., Any]:
    """Mock for active asset retrieval api"""

    def injected_active_asset(*_args, **_kwargs) -> Any:
        data = {k: v for k, v in payload.items() if v is not None}
        try:
            asset_model_module = importlib.import_module("jiko_bridge_blend.src.jb_types")
            asset = asset_model_module.AssetModel.from_dict(data)
            return asset
        except (ImportError, ModuleNotFoundError, AttributeError) as e:
            raise e

    return injected_active_asset
