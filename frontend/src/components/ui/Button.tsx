import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "dark" | "outline" | "ghost";
export type ButtonSize = "md" | "sm";

interface ButtonVariantsArgs {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
}

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-moss-500 focus-visible:ring-offset-2 focus-visible:ring-offset-sage-50 disabled:pointer-events-none disabled:opacity-40";

const VARIANTS: Record<ButtonVariant, string> = {
  // CTA principale : la seule touche de couleur vive de l'interface
  primary: "bg-lime-400 text-forest-950 hover:bg-lime-300",
  dark: "bg-forest-700 text-white hover:bg-forest-900",
  outline: "border border-line bg-white text-ink-900 hover:bg-parchment-100",
  ghost: "text-ink-600 hover:bg-parchment-100 hover:text-ink-900",
};

const SIZES: Record<ButtonSize, string> = {
  md: "px-5 py-2.5 text-sm",
  sm: "px-3.5 py-2 text-sm",
};

/**
 * Génère les classes d'un bouton PlantSafe. Utile pour styler un élément
 * qui n'est pas un <button> natif (ex: <Link> de react-router) de façon
 * identique à Button.
 */
export function buttonVariants({
  variant = "primary",
  size = "md",
  className = "",
}: ButtonVariantsArgs = {}): string {
  return [BASE, VARIANTS[variant], SIZES[size], className]
    .filter(Boolean)
    .join(" ");
}

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    ButtonVariantsArgs {
  icon?: ReactNode;
  iconPosition?: "left" | "right";
}

export function Button({
  variant,
  size,
  className,
  icon,
  iconPosition = "left",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={buttonVariants({ variant, size, className })}
      {...props}
    >
      {icon && iconPosition === "left" ? icon : null}
      {children}
      {icon && iconPosition === "right" ? icon : null}
    </button>
  );
}
