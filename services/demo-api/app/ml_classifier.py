"""
TF-IDF + Logistic Regression classifier loaded from a joblib model file.
Falls back to keyword classifier if model is unavailable.
"""
import os
from typing import Optional
import joblib
from sklearn.pipeline import Pipeline
from app.config import settings
from app.logger import logger


_model: Optional[Pipeline] = None


def load_model() -> Optional[Pipeline]:
    global _model
    if _model is not None:
        return _model

    if not os.path.exists(settings.model_path):
        logger.warning("ml_model_not_found", path=settings.model_path)
        return None

    try:
        _model = joblib.load(settings.model_path)
        logger.info("ml_model_loaded", path=settings.model_path)
        return _model
    except Exception as exc:
        logger.error("ml_model_load_failed", error=str(exc), path=settings.model_path)
        return None


def classify_ml_ranked(text: str) -> tuple[str, float, float]:
    """
    Classify text using the loaded ML model.
    Returns (document_type, confidence, margin vs second class).
    Raises RuntimeError if model is not available.
    """
    model = load_model()
    if model is None:
        raise RuntimeError("ML model not available")

    proba = model.predict_proba([text])[0]
    ranked = sorted(zip(model.classes_, proba), key=lambda item: float(item[1]), reverse=True)
    best_type, best_p = ranked[0]
    second_p = float(ranked[1][1]) if len(ranked) > 1 else 0.0
    margin = float(best_p) - second_p
    return str(best_type), round(float(best_p), 4), round(margin, 4)


def classify_ml(text: str) -> tuple[str, float]:
    """
    Classify text using the loaded ML model.
    Returns (document_type, confidence).
    Raises RuntimeError if model is not available.
    """
    document_type, confidence, _margin = classify_ml_ranked(text)
    return document_type, confidence
