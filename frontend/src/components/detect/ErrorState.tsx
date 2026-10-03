import { AlertTriangle } from "lucide-react";

interface ErrorStateProps {
  message: string;
}

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-coral-500/30 bg-coral-500/5 px-5 py-4 text-sm text-ink-900">
      <AlertTriangle
        className="mt-0.5 h-4 w-4 shrink-0 text-coral-500"
        strokeWidth={2}
      />
      <p>{message}</p>
    </div>
  );
}
