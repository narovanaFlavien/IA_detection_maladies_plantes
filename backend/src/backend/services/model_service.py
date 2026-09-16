import json
from pathlib import Path

import torch
import torch.nn as nn
from torchvision.models import (
    efficientnet_b0,
    EfficientNet_B0_Weights
)

from PIL import Image
from .preprocessing import inference_transform


# ============================================================
# CHEMINS
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_DIR.parent
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "efficientnet_b0_v1.pt"
CLASSES_PATH = MODEL_DIR / "classes.json"


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


# ============================================================
# CHARGEMENT DES CLASSES
# ============================================================

with open(
    CLASSES_PATH,
    "r",
    encoding="utf-8"
) as file:
    CLASS_NAMES = json.load(file)


# ============================================================
# CREATION DU MODELE
# ============================================================

weights = EfficientNet_B0_Weights.DEFAULT

model = efficientnet_b0(
    weights=weights
)

model.classifier[1] = nn.Linear(
    model.classifier[1].in_feature,
    len(CLASS_NAMES)
)


# ============================================================
# CHARGEMENT DES POIDS
# ============================================================

state_dict = torch.load(
    MODEL_PATH,
    map_location=DEVICE
)

model.load_state_dict(state_dict)

model = model.to(DEVICE)

model.eval()


def predict(image: Image.Image) -> dict:
    """
    Effectue une prédiction sur une image.
    """
    image = image.convert("RGB")
    image_tensor = inference_transform(image)

    # image_tensor = image_tensor.unsqueeze(0)
    #unsqueeze n'existe pas
    image_tensor = image_tensor.unsqueeze(0)

    image_tensor = image_tensor.to(DEVICE)

    with torch.no_grad():

        outputs = model(image_tensor)

        probabilities = torch.softmax(
            outputs,
            dim=1
        )

        confidence, predicted_index = torch.max(
            probabilities,
            dim=1
        )

    predicted_index = predicted_index.item()
    confidence = confidence.item()

    predicted_class = CLASS_NAMES[predicted_index]

    return {
        "class_name": predicted_class,
        "confidence": confidence
    }