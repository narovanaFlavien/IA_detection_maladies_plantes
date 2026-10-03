import { Image as ImageIcon, RotateCcw } from "lucide-react";
import { Button } from "../ui/Button";

interface ImagePreviewProps {
  previewUrl: string;
  fileName: string;
  isAnalyzing: boolean;
  onAnalyze: () => void;
  onReset: () => void;
}

export function ImagePreview({
  previewUrl,
  fileName,
  isAnalyzing,
  onAnalyze,
  onReset,
}: ImagePreviewProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-white">
      <div className="flex aspect-video items-center justify-center bg-forest-950/5">
        <img
          src={previewUrl}
          alt="Aperçu de la feuille à analyser"
          className="h-full w-full object-contain"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-4">
        <div className="flex min-w-0 items-center gap-2 text-sm text-ink-600">
          <ImageIcon className="h-4 w-4 shrink-0 text-ink-400" strokeWidth={2} />
          <span className="truncate">{fileName}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            icon={<RotateCcw className="h-3.5 w-3.5" strokeWidth={2} />}
            onClick={onReset}
            disabled={isAnalyzing}
          >
            Changer d'image
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={onAnalyze}
            disabled={isAnalyzing}
          >
            {isAnalyzing ? "Analyse en cours..." : "Analyser cette plante"}
          </Button>
        </div>
      </div>
    </div>
  );
}
