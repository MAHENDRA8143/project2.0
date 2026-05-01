from __future__ import annotations

import tensorflow as tf
from tensorflow.keras import layers, models


def build_cnn_lstm_attention_model(sequence_length: int, n_features: int, forecast_horizon: int) -> tf.keras.Model:
    """
    CNN + LSTM + Attention architecture for multi-feature, multi-step forecasting.
    """
    inputs = layers.Input(shape=(sequence_length, n_features))

    x = layers.Conv1D(filters=32, kernel_size=3, padding="same", activation="relu")(inputs)
    x = layers.Conv1D(filters=64, kernel_size=3, padding="same", activation="relu")(x)
    x = layers.Dropout(0.15)(x)

    lstm_seq = layers.LSTM(96, return_sequences=True)(x)
    attention_seq = layers.Attention()([lstm_seq, lstm_seq])
    merged = layers.Concatenate()([lstm_seq, attention_seq])

    x = layers.LSTM(96, return_sequences=False)(merged)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.2)(x)

    outputs = layers.Dense(forecast_horizon * n_features)(x)
    outputs = layers.Reshape((forecast_horizon, n_features))(outputs)

    model = models.Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), loss="mse", metrics=["mae"])
    return model
