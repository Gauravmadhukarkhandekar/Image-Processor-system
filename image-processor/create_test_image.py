#!/usr/bin/env python3
"""Create a small test image in the project folder for trying the client."""

from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Run: pip install Pillow")
    raise

# Create a simple 400x300 RGB image (colored gradient)
width, height = 400, 300
img = Image.new("RGB", (width, height))
pixels = img.load()
for y in range(height):
    for x in range(width):
        pixels[x, y] = (x % 256, y % 256, (x + y) % 256)

out = Path(__file__).resolve().parent / "test_input.jpg"
img.save(out, "JPEG", quality=85)
print(f"Created {out}")
print(f"Run: python -m client.client {out} -o output.png")
