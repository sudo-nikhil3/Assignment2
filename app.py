"""Iris classifier served with Flask and instrumented for Prometheus."""
import os
import time

import joblib
from flask import Flask, Response, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = os.environ.get("MODEL_PATH", "models/model.joblib")
CLASS_NAMES = ["setosa", "versicolor", "virginica"]

app = Flask(__name__)

# ---- Prometheus metrics ----
APP_REQUESTS = Counter("app_requests_total", "Total HTTP requests", ["endpoint"])
PREDICTION_REQUESTS = Counter("prediction_requests_total", "Total prediction requests")
PREDICTION_LATENCY = Histogram("prediction_latency_seconds", "Prediction latency in seconds")
MODEL_UP = Gauge("model_up", "1 if the model is loaded, else 0")


def load_model():
    """Load the saved model; if none exists, train a small one so the app always starts."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    iris = load_iris()
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(iris.data, iris.target)
    return model


model = load_model()
MODEL_UP.set(1)


@app.before_request
def count_request():
    APP_REQUESTS.labels(endpoint=request.path).inc()


@app.route("/")
def home():
    return "DevOps Iris App is running!"


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/predict", methods=["POST"])
def predict():
    start = time.time()
    data = request.get_json(silent=True) or {}
    inputs = data.get("inputs")
    if not inputs:
        return jsonify(error="send JSON like {\"inputs\": [[5.1, 3.5, 1.4, 0.2]]}"), 400
    preds = model.predict(inputs).tolist()
    PREDICTION_REQUESTS.inc()
    PREDICTION_LATENCY.observe(time.time() - start)
    return jsonify(predictions=preds, classes=[CLASS_NAMES[p] for p in preds])


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
