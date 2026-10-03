import { AlertTriangle, CheckCircle2 } from "lucide-react";

interface PredictionResultProps {
  diseaseClass: string;
  confidence: number;
}

/**
 * Les jeux de données de maladies de plantes (type PlantVillage) nomment
 * les classes "Plante___Maladie" avec des underscores. On les rend lisibles.
 */
function formatDiseaseLabel(rawClassName: string): {
  plant: string | null;
  condition: string;
  isHealthy: boolean;
} {
  const parts = rawClassName.split("___");
  const readable = (value: string) => value.replace(/_/g, " ").trim();
  const isHealthy = /healthy/i.test(rawClassName);

  if (parts.length === 2) {
    return { plant: readable(parts[0]), condition: readable(parts[1]), isHealthy };
  }

  return { plant: null, condition: readable(rawClassName), isHealthy };
}

export function PredictionResult({ diseaseClass, confidence }: PredictionResultProps) {
  const { plant, condition, isHealthy } = formatDiseaseLabel(diseaseClass);
  const confidencePercent = Math.round(confidence * 100);

  return (
    <div
      className={[
        "rounded-2xl border px-6 py-5",
        isHealthy
          ? "border-moss-500/30 bg-moss-500/5"
          : "border-coral-500/30 bg-coral-500/5",
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <span
          className={[
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
            isHealthy
              ? "bg-moss-500/15 text-moss-600"
              : "bg-coral-500/15 text-coral-500",
          ].join(" ")}
        >
          {isHealthy ? (
            <CheckCircle2 className="h-5 w-5" strokeWidth={2} />
          ) : (
            <AlertTriangle className="h-5 w-5" strokeWidth={2} />
          )}
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-ink-400">
            {isHealthy ? "Plante saine" : "Maladie détectée"}
          </p>
          {plant && <p className="mt-0.5 text-sm text-ink-600">{plant}</p>}
          <h3 className="mt-1 font-display text-xl font-medium text-ink-900">
            {condition}
          </h3>

          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-ink-400">
              <span>Confiance du modèle</span>
              <span className="font-medium text-ink-600">
                {confidencePercent}%
              </span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-line">
              <div
                className={[
                  "h-full rounded-full",
                  isHealthy ? "bg-moss-500" : "bg-coral-500",
                ].join(" ")}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
