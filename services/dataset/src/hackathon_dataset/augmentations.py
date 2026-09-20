from __future__ import annotations

from pathlib import Path
from random import Random

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps


def _shadow_layer(base: Image.Image) -> Image.Image:
    shadow = Image.new("L", base.size, color=255)
    width, height = base.size
    for step in range(14):
        offset = int((step / 13) * width * 0.35)
        alpha = int(255 - (step / 13) * 90)
        for y in range(height):
            if offset > 0:
                shadow.putpixel((min(offset, width - 1), y), alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=55))
    return shadow


def apply_quality_profile(path: Path, profile: str, jpeg_quality: int, rng: Random) -> None:
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        return

    image = Image.open(path).convert("RGB")

    if profile == "scan_blur_rotation":
        image = image.rotate(rng.uniform(-2.4, 2.4), expand=True, fillcolor="white")
        image = ImageOps.grayscale(image).convert("RGB")
        image = image.filter(ImageFilter.GaussianBlur(radius=0.9))
        image = ImageEnhance.Contrast(image).enhance(0.88)
    elif profile == "smartphone_photo":
        image = image.rotate(rng.uniform(-5.0, 5.0), expand=True, fillcolor="white")
        image = ImageEnhance.Contrast(image).enhance(0.84)
        image = ImageEnhance.Sharpness(image).enhance(0.9)
        image = image.filter(ImageFilter.GaussianBlur(radius=0.7))
        shadow = _shadow_layer(image)
        image = ImageChops.multiply(image.convert("L"), shadow).convert("RGB")
    elif profile == "pixelated_scan":
        shrunk = image.resize((max(400, image.width // 4), max(600, image.height // 4)))
        image = shrunk.resize(image.size)
        image = ImageOps.grayscale(image).convert("RGB")
    elif profile == "low_contrast_scan":
        image = ImageOps.grayscale(image).convert("RGB")
        image = ImageEnhance.Contrast(image).enhance(0.65)
        image = ImageEnhance.Brightness(image).enhance(1.08)

    save_kwargs = {}
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        save_kwargs["quality"] = jpeg_quality
    image.save(path, **save_kwargs)
