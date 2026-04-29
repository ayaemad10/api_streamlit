"""
ai_model/predictor.py
---------------------
Wraps the loaded Keras model and returns structured predictions.
"""

import numpy as np
from utils.logger import get_logger

logger = get_logger("ai_model.predictor")

CLASSES = ["Normal", "Jamming", "Drone"]


class Predictor:
    """
    Runs inference on a preprocessed spectrogram batch.

    Args:
        model: Loaded Keras model (from ModelLoader.get_instance()).
    """

    def __init__(self, model):
        self.model = model

    def predict(self, img_batch: np.ndarray) -> dict:
        """
        Run model inference.

        Args:
            img_batch: float32 array of shape (1, 224, 224, 3), values in [0, 1].

        Returns:
            {
                "class": "Drone",
                "confidence": 0.94,
                "scores": {"Normal": 0.03, "Jamming": 0.03, "Drone": 0.94}
            }
        """
        if img_batch.ndim == 3:
            img_batch = img_batch[np.newaxis, ...]  # add batch dim

        probs = self.model.predict(img_batch, verbose=0)[0]

        class_idx = int(np.argmax(probs))
        label = CLASSES[class_idx]
        confidence = float(probs[class_idx])

        scores = {cls: round(float(p), 6) for cls, p in zip(CLASSES, probs)}

        logger.debug(f"Prediction: {label} ({confidence:.2%}) | scores={scores}")

        return {
            "class": label,
            "confidence": round(confidence, 6),
            "scores": scores,
        }
