import { Link } from "react-router-dom";
import { Leaf, ScanLine, ShieldCheck } from "lucide-react";
import { buttonVariants } from "../ui/Button";
import { LeafScanIllustration } from "./LeafScanIllustration";

const HIGHLIGHTS = [
  {
    icon: ScanLine,
    text: "Une photo suffit pour lancer l'analyse",
  },
  {
    icon: Leaf,
    text: "Reconnaît les maladies des principales cultures",
  },
  {
    icon: ShieldCheck,
    text: "Un diagnostic clair pour agir avant que ça se propage",
  },
];

export function Hero() {
  return (
    <section className="grid items-center gap-12 py-6 lg:grid-cols-[1.05fr_0.95fr] lg:py-12">
      <div>
        <h1 className="font-display text-4xl leading-[1.1] font-medium text-ink-900 lg:text-5xl">
          Repérez une maladie sur vos plantes en quelques secondes
        </h1>

        <p className="mt-5 max-w-md leading-relaxed text-ink-600">
          Prenez une photo d'une feuille abîmée et PlantSafe identifie la
          maladie la plus probable, avec un niveau de confiance, pour que
          vous sachiez quoi faire ensuite.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Link to="/detecter" className={buttonVariants({ variant: "primary" })}>
            Analyser une plante
          </Link>
          <Link to="/maladies" className={buttonVariants({ variant: "outline" })}>
            Voir les maladies courantes
          </Link>
        </div>

        <ul className="mt-10 space-y-3">
          {HIGHLIGHTS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-center gap-3 text-sm text-ink-600">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-parchment-100 text-moss-600">
                <Icon className="h-4 w-4" strokeWidth={2} />
              </span>
              {text}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-center justify-center rounded-2xl border border-line bg-parchment-100 p-10">
        <LeafScanIllustration className="h-auto w-full max-w-xs" />
      </div>
    </section>
  );
}
