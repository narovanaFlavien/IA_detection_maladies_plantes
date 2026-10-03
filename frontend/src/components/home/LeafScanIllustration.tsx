interface LeafScanIllustrationProps {
  className?: string;
}

/**
 * Illustration dessinée à la main : silhouette de feuille avec nervures,
 * une "tache" détectée (repère corail) cerclée d'un anneau en pointillés,
 * et une ligne de scan diagonale — évoque le diagnostic sans être une
 * photo de stock ni un gradient décoratif.
 */
export function LeafScanIllustration({
  className,
}: LeafScanIllustrationProps) {
  return (
    <svg
      viewBox="0 0 240 260"
      className={className}
      role="img"
      aria-label="Illustration d'une feuille en cours d'analyse"
    >
      {/* Tige */}
      <path
        d="M120 220 L120 240"
        stroke="var(--color-moss-600)"
        strokeWidth="3"
        strokeLinecap="round"
      />

      {/* Silhouette de la feuille */}
      <path
        d="M120 20
           C 172 42, 202 92, 202 140
           C 202 192, 162 222, 120 222
           C 78 222, 38 192, 38 140
           C 38 92, 68 42, 120 20 Z"
        fill="var(--color-moss-500)"
        fillOpacity="0.18"
        stroke="var(--color-forest-700)"
        strokeWidth="2.5"
      />

      {/* Nervure centrale */}
      <path
        d="M120 42 L120 204"
        stroke="var(--color-forest-700)"
        strokeWidth="2"
        strokeLinecap="round"
      />

      {/* Nervures secondaires */}
      {[
        [70, 74],
        [88, 108],
        [104, 140],
        [170, 74],
        [152, 108],
        [136, 140],
      ].map(([x, y], index) => (
        <path
          key={index}
          d={`M120 ${y - 10} L${x} ${y}`}
          stroke="var(--color-forest-700)"
          strokeOpacity="0.5"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      ))}

      {/* Ligne de scan */}
      <line
        x1="30"
        y1="150"
        x2="210"
        y2="110"
        stroke="var(--color-lime-400)"
        strokeWidth="3"
        strokeLinecap="round"
        opacity="0.85"
      />

      {/* Repère de détection sur la tache */}
      <circle
        cx="150"
        cy="128"
        r="7"
        fill="var(--color-coral-500)"
      />
      <circle
        cx="150"
        cy="128"
        r="20"
        fill="none"
        stroke="var(--color-coral-500)"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />
    </svg>
  );
}
