"""
ai_model/model_loader.py
------------------------
Thread-safe singleton loader for the TensorFlow/Keras model.
"""

import os
import threading
from utils.logger import get_logger

logger = get_logger("ai_model.model_loader")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "best_model.keras")


class ModelLoader:
    """
    Singleton pattern for loading and caching the Keras model.
    Thread-safe: uses a lock to prevent double-loading.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """Return the cached model, loading it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._load_model()
        return cls._instance

    @staticmethod
    def _load_model():
        """Load the Keras model from disk."""
        try:
            import tensorflow as tf
            logger.info(f"Loading Keras model from: {MODEL_PATH}")

            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

            model = tf.keras.models.load_model(MODEL_PATH, compile=False)
            logger.info(f"Model loaded successfully. Input shape: {model.input_shape}")
            return model

        except ImportError:
            logger.warning("TensorFlow not installed — using mock model for demo")
            return _MockModel()
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            return _MockModel()


class _MockModel:
    """
    Fallback mock model that returns random predictions.
    Used when TensorFlow is unavailable or model file is missing.
    """

    input_shape = (None, 224, 224, 3)

    def predict(self, x, verbose=0):
        import numpy as np
        batch = x.shape[0]
        # Random softmax-like output for 3 classes
        raw = np.random.dirichlet([5, 1, 1], size=batch)  # bias toward Normal
        return raw

    def __repr__(self):
        return "MockModel(classes=['Normal','Jamming','Drone'])"
