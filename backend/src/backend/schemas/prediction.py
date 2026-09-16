from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):

    class_name: str = Field(
        description="Classe prédite par le modèle."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Niveau de confiance de la prédiction."
    )