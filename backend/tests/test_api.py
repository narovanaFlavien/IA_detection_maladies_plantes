from io import BytesIO

from PIL import Image


def make_image_bytes(fmt: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), (0, 128, 0)).save(buffer, format=fmt)
    return buffer.getvalue()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_valid_image(client):
    response = client.post(
        "/api/predict",
        files={"file": ("leaf.png", make_image_bytes(), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["class_name"] == "Tomato_Healthy"
    assert 0.0 <= body["confidence"] <= 1.0


def test_predict_unsupported_content_type(client):
    response = client.post(
        "/api/predict",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "Format d'image non supporté" in response.json()["detail"]


def test_predict_corrupted_image(client):
    response = client.post(
        "/api/predict",
        files={"file": ("fake.png", b"ceci n'est pas une image", "image/png")},
    )
    assert response.status_code == 400
    assert "pas une image valide" in response.json()["detail"]


def test_predict_missing_file(client):
    response = client.post("/api/predict")
    assert response.status_code == 422


def test_predict_model_error_returns_500(client, monkeypatch):
    def boom(image):
        raise RuntimeError("modèle indisponible")

    monkeypatch.setattr("src.backend.routes.prediction.predict", boom)

    response = client.post(
        "/api/predict",
        files={"file": ("leaf.png", make_image_bytes(), "image/png")},
    )
    assert response.status_code == 500