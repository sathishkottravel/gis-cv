"""Traffic sign classification with a pretrained GTSRB model from Hugging Face."""
import os
from typing import NamedTuple

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

from app import config  # noqa: F401  (loads .env)
from app.labels import LABELS

MODEL_ID = os.getenv("CLASSIFIER_MODEL", "bazyl/gtsrb-model")
LOW_CONFIDENCE = 0.5

_processor = None
_model = None


class Prediction(NamedTuple):
    class_id: int
    label: str
    confidence: float
    low_conf: bool


def load() -> None:
    """Load the model once; safe to call repeatedly."""
    global _processor, _model
    if _model is None:
        _processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        _model = AutoModelForImageClassification.from_pretrained(MODEL_ID).eval()


def predict(image: Image.Image) -> Prediction:
    load()
    inputs = _processor(images=image.convert("RGB"), return_tensors="pt")
    with torch.no_grad():
        logits = _model(**inputs).logits[0]
    # The checkpoint has a 44th "None" output; only the 43 GTSRB classes count.
    probs = logits[: len(LABELS)].softmax(dim=-1)
    confidence, class_id = probs.max(dim=-1)
    confidence = float(confidence)
    return Prediction(int(class_id), LABELS[int(class_id)], confidence, confidence < LOW_CONFIDENCE)
