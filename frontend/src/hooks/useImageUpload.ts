import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, isAcceptedImageType, predictDisease } from "../services/api";
import type { PredictionResponse } from "../types/prediction";

export type UploadStatus = "idle" | "loading" | "success" | "error";

interface UseImageUploadResult {
  file: File | null;
  previewUrl: string | null;
  status: UploadStatus;
  result: PredictionResponse | null;
  errorMessage: string | null;
  selectFile: (file: File) => void;
  analyze: () => void;
  reset: () => void;
}

export function useImageUpload(): UseImageUploadResult {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Libère l'URL d'objet créée pour l'aperçu quand elle change ou au démontage
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const selectFile = useCallback((nextFile: File) => {
    if (!isAcceptedImageType(nextFile)) {
      setFile(null);
      setPreviewUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return null;
      });
      setResult(null);
      setStatus("error");
      setErrorMessage(
        "Format non supporté. Utilisez une image JPEG, PNG ou WEBP."
      );
      return;
    }

    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(nextFile);
    });
    setFile(nextFile);
    setResult(null);
    setErrorMessage(null);
    setStatus("idle");
  }, []);

  const analyze = useCallback(() => {
    if (!file) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("loading");
    setErrorMessage(null);

    predictDisease(file, controller.signal)
      .then((prediction) => {
        setResult(prediction);
        setStatus("success");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        const message =
          error instanceof ApiError
            ? `${error.message} karakory`
            : "Une erreur inattendue est survenue.";
        setErrorMessage(message);
        setStatus("error");
      });
  }, [file]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    setFile(null);
    setResult(null);
    setErrorMessage(null);
    setStatus("idle");
  }, []);

  return {
    file,
    previewUrl,
    status,
    result,
    errorMessage,
    selectFile,
    analyze,
    reset,
  };
}
