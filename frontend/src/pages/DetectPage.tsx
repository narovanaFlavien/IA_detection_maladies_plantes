import { useImageUpload } from "../hooks/useImageUpload";
import { ImageDropzone } from "../components/detect/ImageDropzone";
import { ImagePreview } from "../components/detect/ImagePreview";
import { LoadingState } from "../components/detect/LoadingState";
import { ErrorState } from "../components/detect/ErrorState";
import { PredictionResult } from "../components/detect/PredictionResult";

export function DetectPage() {
  const {
    file,
    previewUrl,
    status,
    result,
    errorMessage,
    selectFile,
    analyze,
    reset,
  } = useImageUpload();

  return (
    <div className="max-w-2xl">
      <h1 className="font-display text-2xl font-medium text-ink-900">
        Détecter une maladie
      </h1>
      <p className="mt-2 text-ink-600">
        Déposez une photo nette d'une feuille abîmée pour obtenir un
        diagnostic.
      </p>

      <div className="mt-8 space-y-4">
        {!previewUrl && <ImageDropzone onFileSelected={selectFile} />}

        {previewUrl && file && (
          <ImagePreview
            previewUrl={previewUrl}
            fileName={file.name}
            isAnalyzing={status === "loading"}
            onAnalyze={analyze}
            onReset={reset}
          />
        )}

        {status === "loading" && <LoadingState />}

        {status === "error" && errorMessage && (
          <ErrorState message={errorMessage} />
        )}

        {status === "success" && result && (
          <PredictionResult
            diseaseClass={result.class_name}
            confidence={result.confidence}
          />
        )}
      </div>
    </div>
  );
}
