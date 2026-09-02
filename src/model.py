import torch.nn as nn

from torchvision.models import (
    efficientnet_b0,
    EfficientNet_B0_Weights
)


def create_model(num_classes):
    """
    Crée EfficientNet-B0 pré-entraîné
    et adapte la dernière couche au nombre
    de classes du dataset.
    """

    weights = EfficientNet_B0_Weights.DEFAULT

    model = efficientnet_b0(
        weights=weights
    )

    model.classifier[1] = nn.Linear(
        model.classifier[1].in_features,
        num_classes
    )

    return model