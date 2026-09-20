"""
Image preprocessing pipeline:
  1. Grayscale conversion
  2. Deskew (Hough-line based angle detection)
  3. Denoising (fastNlMeansDenoising)
  4. CLAHE contrast enhancement
"""
import io
import math
import numpy as np
import cv2
from PIL import Image


def _to_numpy(image_bytes: bytes) -> np.ndarray:
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _to_bytes(img: np.ndarray) -> bytes:
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


def _grayscale(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Detect skew angle using Hough lines and rotate to correct."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return gray

    angles: list[float] = []
    for rho_theta in lines:
        rho, theta = rho_theta[0]
        angle = math.degrees(theta) - 90
        if abs(angle) < 45:
            angles.append(angle)

    if not angles:
        return gray

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return gray

    h, w = gray.shape
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    return cv2.warpAffine(gray, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def _denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def _clahe(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def preprocess(image_bytes: bytes) -> bytes:
    """Full preprocessing pipeline. Returns PNG bytes ready for Tesseract."""
    img = _to_numpy(image_bytes)
    gray = _grayscale(img)
    deskewed = _deskew(gray)
    denoised = _denoise(deskewed)
    enhanced = _clahe(denoised)
    return _to_bytes(enhanced)
