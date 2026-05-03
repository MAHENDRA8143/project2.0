from __future__ import annotations


def build_cnn_lstm_attention_model(sequence_length: int, n_features: int, forecast_horizon: int):
    """Legacy compatibility shim kept for older training scripts.

    The project now uses a scikit-learn forecaster so it remains compatible with
    Python 3.14 without TensorFlow.
    """

    raise RuntimeError(
        "TensorFlow-based training is no longer supported in this project. "
        "Use app.services.model_pipeline.STPForecaster instead."
    )
