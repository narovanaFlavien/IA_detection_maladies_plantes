import { NavLink } from "react-router-dom";
import type { NavItem } from "../../config/navigation";

export function SidebarLink({ to, label, icon: Icon, end }: NavItem) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          "flex items-center gap-3 rounded-md border-l-2 px-3 py-2.5 text-sm transition-colors",
          isActive
            ? "border-lime-400 bg-white/10 font-medium text-white"
            : "border-transparent text-sage-50/70 hover:bg-white/5 hover:text-white",
        ].join(" ")
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2} />
      {label}
    </NavLink>
  );
}
