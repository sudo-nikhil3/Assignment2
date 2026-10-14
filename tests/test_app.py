import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"running" in r.data


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_predict(client):
    r = client.post("/predict", json={"inputs": [[5.1, 3.5, 1.4, 0.2]]})
    assert r.status_code == 200
    assert r.get_json()["classes"] == ["setosa"]


def test_predict_bad_input(client):
    r = client.post("/predict", json={})
    assert r.status_code == 400


def test_metrics(client):
    client.post("/predict", json={"inputs": [[6.0, 2.9, 4.5, 1.5]]})
    r = client.get("/metrics")
    assert r.status_code == 200
    assert b"prediction_requests_total" in r.data
    assert b"model_up 1.0" in r.data
