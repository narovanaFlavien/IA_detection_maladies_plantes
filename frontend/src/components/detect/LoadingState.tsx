import { Loader2 } from "lucide-react";

export function LoadingState() {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-white px-5 py-4 text-sm text-ink-600">
      <Loader2 className="h-4 w-4 animate-spin text-moss-600" strokeWidth={2} />
      Analyse de l'image en cours...
    </div>
  );
}
