import sys
import types

import pytest
from fastapi.testclient import TestClient

# Faux model_service : évite de charger torch et le fichier .pt.
# DOIT être injecté avant l'import de l'application.
_fake_model_service = types.ModuleType("src.backend.services.model_service")
_fake_model_service.predict = lambda image: {
    "class_name": "Tomato_Healthy",
    "confidence": 0.97,
}
sys.modules["src.backend.services.model_service"] = _fake_model_service


@pytest.fixture()
def client():
    from src.backend.main import app

    return TestClient(app)