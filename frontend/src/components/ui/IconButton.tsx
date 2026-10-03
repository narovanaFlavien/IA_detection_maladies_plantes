import type { ButtonHTMLAttributes, ReactNode } from "react";

export type IconButtonVariant = "ghost" | "dark";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: ReactNode;
  /** Obligatoire : un bouton icône-seule doit rester accessible au clavier/lecteur d'écran */
  label: string;
  variant?: IconButtonVariant;
  /** Affiche un petit point (ex: notification non lue) en haut à droite de l'icône */
  hasBadge?: boolean;
}

const VARIANTS: Record<IconButtonVariant, string> = {
  ghost: "text-ink-600 hover:bg-parchment-100 hover:text-ink-900",
  dark: "bg-forest-700 text-white hover:bg-forest-900",
};

export function IconButton({
  icon,
  label,
  variant = "ghost",
  hasBadge = false,
  className = "",
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={[
        "relative flex h-9 w-9 items-center justify-center rounded-full transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-moss-500 focus-visible:ring-offset-2 focus-visible:ring-offset-sage-50",
        "disabled:pointer-events-none disabled:opacity-40",
        VARIANTS[variant],
        className,
      ].join(" ")}
      {...props}
    >
      {icon}
      {hasBadge && (
        <span
          aria-hidden="true"
          className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-coral-500"
        />
      )}
    </button>
  );
}
