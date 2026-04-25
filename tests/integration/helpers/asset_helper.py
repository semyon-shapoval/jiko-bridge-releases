import os
import struct
import tempfile
import zlib
import json
import urllib.request as urllib_request
from typing import Any


def create_dummy_texture(filename: str) -> str:
    path = os.path.join(tempfile.gettempdir(), filename)

    def mk_chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\xff\xff")
    png = (
        b"\x89PNG\r\n\x1a\n"
        + mk_chunk(b"IHDR", ihdr)
        + mk_chunk(b"IDAT", idat)
        + mk_chunk(b"IEND", b"")
    )

    with open(path, "wb") as f:
        f.write(png)

    return path


def create_material_direct(
    payload: dict[str, Any],
    texture_path: str,
    host: str = "localhost",
    port: int = 5174,
) -> dict[str, Any] | None:
    body = {
        "packName": payload.get("packName"),
        "assetName": payload.get("assetName"),
        "databaseName": payload.get("databaseName"),
        "files": [
            {
                "filepath": texture_path,
                "assetType": payload.get("files", [{}])[0].get("assetType"),
            }
        ],
    }
    url = f"http://{host}:{port}/api/asset/create"
    req = urllib_request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib_request.urlopen(req, timeout=30) as resp:
        response = json.loads(resp.read().decode("utf-8"))

    return response.get("data") if isinstance(response, dict) else None
