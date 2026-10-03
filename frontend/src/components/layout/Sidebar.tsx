import { Leaf } from "lucide-react";
import { NAV_ITEMS } from "../../config/navigation";
import { SidebarLink } from "./SidebarLink";

export function Sidebar() {
  return (
    <aside className="flex w-64 shrink-0 flex-col bg-forest-700">
      <div className="flex items-center gap-2.5 px-6 py-6">
        <Leaf className="h-6 w-6 text-lime-400" strokeWidth={2.25} />
        <span className="font-display text-xl font-medium tracking-tight text-white">
          PlantSafe
        </span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => (
          <SidebarLink key={item.to} {...item} />
        ))}
      </nav>

      <div className="border-t border-white/10 px-6 py-4 text-xs text-white/40">
        PlantSafe v1.0.0
      </div>
    </aside>
  );
}
