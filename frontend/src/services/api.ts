import type {
  PredictionResponse,
  ApiErrorResponse,
} from "../types/prediction";
import { ACCEPTED_IMAGE_TYPES } from "../types/prediction";

/**
 * URL de base de l'API backend.
 * Configurable via une variable d'environnement Vite (frontend/.env) :
 *   VITE_API_URL=http://localhost:8000
 */
const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  "http://localhost:8000";

/**
 * Erreur typée renvoyée par le service API.
 * `status` vaut 0 en cas d'échec réseau (serveur injoignable).
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Vérifie côté client qu'un fichier a un type MIME accepté par le backend,
 * avant même de tenter l'upload (JPEG, PNG, WEBP).
 */
export function isAcceptedImageType(file: File): boolean {
  return (ACCEPTED_IMAGE_TYPES as readonly string[]).includes(file.type);
}

/**
 * Envoie une image au backend pour prédiction de maladie de plante.
 *
 * POST {API_BASE_URL}/api/predict (multipart/form-data, champ "file")
 *
 * @throws {ApiError} si le fichier est invalide (400), si une erreur serveur
 * survient (500), ou si le serveur est injoignable (status 0).
 */
export async function predictDisease(
  file: File,
  signal?: AbortSignal
): Promise<PredictionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/api/predict`, {
      method: "POST",
      body: formData,
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }

    throw new ApiError(
      // "Impossible de contacter le serveur. Vérifiez votre connexion.",
      `${error}`,
      0
    );
  }

  if (!response.ok) {
    let detail = "Une erreur est survenue pendant la prédiction.";

    try {
      const errorBody = (await response.json()) as ApiErrorResponse;
      if (errorBody?.detail) {
        detail = errorBody.detail;
      }
    } catch {
      // Le corps de la réponse n'est pas du JSON exploitable : on garde
      // le message par défaut.
    }

    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as PredictionResponse;
}
