"""Train Iris models with MLflow: track params/metrics, register versions, set a 'champion' alias.

Run:  python train.py
View: mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
"""
import os

import joblib
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("Iris_Classification")

MODEL_NAME = "Iris_Classifier"
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Three runs with different hyperparameters -> three registered model versions
configs = [
    {"n_estimators": 1, "max_depth": 1},
    {"n_estimators": 5, "max_depth": 2},
    {"n_estimators": 100, "max_depth": 5},
]

best = {"acc": -1, "model": None, "run_id": None}

for cfg in configs:
    with mlflow.start_run() as run:
        model = RandomForestClassifier(random_state=42, **cfg)
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))

        mlflow.log_params(cfg)
        mlflow.log_metric("accuracy", acc)
        # cloudpickle: the model is trained by this script, so it is trusted
        # (newer MLflow defaults to skops, which rejects tree models without extra config)
        mlflow.sklearn.log_model(
            model,
            name="model",
            registered_model_name=MODEL_NAME,
            serialization_format="cloudpickle",
        )
        print(f"run {run.info.run_id[:8]}  params={cfg}  accuracy={acc:.3f}")

        if acc >= best["acc"]:
            best = {"acc": acc, "model": model, "run_id": run.info.run_id}

# Promote the best version to the 'champion' alias (model version management)
client = MlflowClient()
versions = client.search_model_versions(f"name='{MODEL_NAME}'")
best_version = next(v.version for v in versions if v.run_id == best["run_id"])
client.set_registered_model_alias(MODEL_NAME, "champion", best_version)
print(f"Alias 'champion' -> version {best_version} (accuracy {best['acc']:.3f})")

# Save the champion for the Flask/Docker app
os.makedirs("models", exist_ok=True)
joblib.dump(best["model"], "models/model.joblib")
print("Saved models/model.joblib")
