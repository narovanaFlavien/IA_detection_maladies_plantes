import type { ComponentType } from "react";
import { Home, Leaf, ScanLine } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  /** Correspond à la prop `end` de NavLink : true pour ne matcher que la route exacte */
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Accueil", icon: Home, end: true },
  { to: "/detecter", label: "Détecter une maladie", icon: ScanLine },
  { to: "/maladies", label: "Maladies", icon: Leaf },
];
