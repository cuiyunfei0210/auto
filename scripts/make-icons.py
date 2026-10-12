"""Draw the sprout-face app icon as a PNG, using only the standard library."""

import struct
import zlib
from pathlib import Path


def chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, size: int) -> None:
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            pixels.extend(color_at(x / size, y / size))
    raw = zlib.compress(bytes(pixels), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", raw)
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def color_at(u: float, v: float) -> bytes:
    # Warm rounded tile.
    dx = max(abs(u - 0.5) - 0.34, 0)
    dy = max(abs(v - 0.5) - 0.34, 0)
    if dx * dx + dy * dy > 0.16 * 0.16:
        return bytes((255, 176, 0))
    # Face.
    if (u - 0.5) ** 2 + (v - 0.58) ** 2 < 0.16**2:
        # Eyes and smile sit on the face.
        if (u - 0.42) ** 2 + (v - 0.56) ** 2 < 0.012**2 or (u - 0.58) ** 2 + (v - 0.56) ** 2 < 0.012**2:
            return bytes((60, 47, 47))
        if abs(u - 0.5) < 0.08 and abs(v - 0.66) < 0.02 and (u - 0.5) ** 2 * 8 + (v - 0.64) ** 2 > 0.004:
            return bytes((60, 47, 47))
        return bytes((255, 247, 234))
    # Leaves.
    if (u - 0.58) ** 2 * 1.4 + (v - 0.30) ** 2 * 3 < 0.03:
        return bytes((47, 154, 85))
    if (u - 0.42) ** 2 * 1.6 + (v - 0.33) ** 2 * 3.2 < 0.028:
        return bytes((125, 206, 115))
    return bytes((255, 176, 0))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "public"
    write_png(root / "icon-192.png", 192)
    write_png(root / "icon-512.png", 512)
    print("icons ok")
