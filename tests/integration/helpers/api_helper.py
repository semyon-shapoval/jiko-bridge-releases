"""
Api helper
Code by Semyon Shapoval, 2026
"""

from copy import copy
from inspect import signature
from typing import Any, Callable

from plugins.blender.addons.jiko_bridge_blend.src.jb_api import JbAPI
from plugins.blender.addons.jiko_bridge_blend.src.jb_types import AssetModel


def make_injected_create_asset(
    asset_model: AssetModel,
    original_create_asset: Callable[..., Any],
) -> tuple[dict[str, Any], Callable[..., Any]]:
    """Mock for files creation asset api"""
    payload_capture: dict[str, Any] = {}
    original_signature = signature(original_create_asset)

    def injected_create_asset(*args: Any, **kwargs: Any) -> Any:
        bound_args = original_signature.bind_partial(*args, **kwargs)
        merged = dict(bound_args.arguments)

        asset = merged.get("asset")
        if asset is not None:
            for key in ("database_name", "pack_name", "asset_name"):
                value = getattr(asset_model, key, None)
                if value is not None and hasattr(asset, key):
                    setattr(asset, key, value)

            asset_type = asset_model.active_type or (
                asset_model.files[0].asset_type if asset_model.files else None
            )
            if hasattr(asset, "files") and asset_type:
                enriched = []
                for f in list(asset.files):
                    f = copy(f)
                    f.asset_type = asset_type
                    enriched.append(f)
                asset.files = enriched

            merged["asset"] = asset

        payload_capture["asset"] = merged.get("asset")
        return original_create_asset(**merged)

    return payload_capture, injected_create_asset


def make_injected_active_asset(
    asset_model: AssetModel,
) -> Callable[..., Any]:
    """Mock for active asset retrieval api"""

    def injected_active_asset(*_args, **_kwargs) -> Any:
        api = JbAPI()
        return api.get_asset(asset_model)

    return injected_active_asset
