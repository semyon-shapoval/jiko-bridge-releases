"""
Api helper
Code by Semyon Shapoval, 2026
"""

import logging
from copy import copy
from inspect import signature
from typing import Any, Callable

logging.basicConfig(
    level=logging.DEBUG,
    format='[Test Jiko] %(levelname)s: %(message)s',
)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the specified name."""
    return logging.getLogger(name)


def make_injected_create_asset(asset_model: Any, original_create_asset: Callable[..., Any]):
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
