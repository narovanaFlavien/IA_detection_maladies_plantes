/**
 * Miroir du schéma Pydantic `PredictionResponse`
 * (backend/src/backend/schemas/prediction.py)
 */
export interface PredictionResponse {
  /** Classe prédite par le modèle (ex: "Tomato___Late_blight") */
  class_name: string;
  /** Niveau de confiance de la prédiction, compris entre 0 et 1 */
  confidence: number;
}

/**
 * Forme du corps d'erreur renvoyé par FastAPI via HTTPException
 * (ex: { "detail": "Le fichier envoyé n'est pas une image valide." })
 */
export interface ApiErrorResponse {
  detail: string;
}

/** Types MIME acceptés par la route /api/predict */
export const ACCEPTED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

export type AcceptedImageType = (typeof ACCEPTED_IMAGE_TYPES)[number];
