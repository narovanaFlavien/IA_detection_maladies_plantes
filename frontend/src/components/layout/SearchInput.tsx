import { Search } from "lucide-react";

export function SearchInput() {
  return (
    <label className="flex w-full max-w-sm items-center gap-2 rounded-lg border border-line bg-sage-50 px-3.5 py-2 text-sm text-ink-600 transition-colors focus-within:border-moss-500 focus-within:bg-white">
      <Search className="h-4 w-4 shrink-0 text-ink-400" strokeWidth={2} />
      <input
        type="search"
        placeholder="Rechercher une maladie, une plante..."
        className="w-full bg-transparent text-ink-900 outline-none placeholder:text-ink-400"
      />
    </label>
  );
}
