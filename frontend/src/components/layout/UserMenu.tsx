import { ChevronDown } from "lucide-react";

interface UserMenuProps {
  name: string;
  role: string;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function UserMenu({ name, role }: UserMenuProps) {
  return (
    <button
      type="button"
      className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-2.5 transition-colors hover:bg-parchment-100"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-moss-500 text-xs font-semibold text-white">
        {getInitials(name)}
      </span>
      <span className="hidden text-left sm:block">
        <span className="block text-sm leading-none font-medium text-ink-900">
          {name}
        </span>
        <span className="mt-1 block text-xs leading-none text-ink-400">
          {role}
        </span>
      </span>
      <ChevronDown className="h-3.5 w-3.5 text-ink-400" strokeWidth={2} />
    </button>
  );
}
