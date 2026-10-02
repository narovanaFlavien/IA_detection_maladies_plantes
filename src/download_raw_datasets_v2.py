"""
Téléchargement et fusion des datasets externes pour le projet
IA_detection_maladies_plantes.

À exécuter depuis Google Colab après avoir cloné le dépôt :

    git clone https://github.com/narovanaFlavien/IA_detection_maladies_plantes.git
    %cd IA_detection_maladies_plantes
    python src/download_raw_datasets.py

Le script crée/fusionne :

    data/raw/
    ├── Tomato_Healthy/
    ├── Tomato_Early_Blight/
    └── Tomato_Late_Blight/

Sources :
1. PlantDoc Classification   - Hugging Face
2. Tomato Leaf Dataset       - Mendeley Data v1
3. Tomato-Village            - GitHub, Variant-a (Multiclass Classification)
4. PlantVillage (raw/color)  - GitHub spMohanty/PlantVillage-Dataset

=====================================================================
COMMENT AJOUTER UNE CLASSE
=====================================================================
Tout se passe dans CLASS_SPECS (section "Classes du projet", plus bas).
Ajouter une classe = ajouter UN bloc ClassSpec(...) qui indique, pour
chaque source, le nom du label correspondant. Aucune autre fonction
n'est à modifier. Une source pour laquelle on laisse () est simplement
ignorée pour cette classe.

Pour découvrir les noms de labels disponibles dans chaque source :

    python src/download_raw_datasets.py --list-labels

Options utiles :

    --sources plantvillage plantdoc    ne traiter que certaines sources
    --list-labels                      afficher les labels disponibles

=====================================================================
NOTES
=====================================================================
- Le script ne fait PAS le split train/validation/test final du projet.
  Les splits des datasets externes sont regroupés dans data/raw, puis
  votre pipeline (src/preparation.py) refait le split.
- Mendeley : on utilise "TomatoLeafMulticlass (Annotated)" et ses
  fichiers YOLO .txt pour retrouver la classe de chaque image.
  "Raw Data" (pas de dossiers de classes) et "Annotated & Augmented"
  (images artificielles) ne sont PAS utilisés.
- PlantVillage : seule la variante raw/color (images RGB d'origine) est
  utilisée, via un clone partiel qui ne télécharge que les dossiers de
  classes demandés. Les noms de fichiers d'origine (UUID) sont conservés.
- Les noms de fichiers sont préfixés par la source pour éviter les
  collisions et identifier la provenance.
- Le script nettoie uniquement les fichiers qu'il a lui-même générés
  (préfixes plantdoc_, mendeley_, tomatovillage_, plantvillage_) pour
  les sources traitées, afin d'éviter les doublons lors d'une nouvelle
  exécution. Les autres fichiers de data/raw ne sont pas supprimés.
- Migration : si d'anciens dossiers français (Tomate_Saine, ...) existent,
  leur contenu est déplacé vers les nouveaux dossiers anglais.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration générale
# ---------------------------------------------------------------------------

# Le script est prévu dans src/ ou scripts/ : dans les deux cas, le projet
# est le dossier parent.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}


# ---------------------------------------------------------------------------
# Utilitaires de normalisation
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """
    Normalise un nom pour faciliter la comparaison des labels.

    "Tomato___Early_blight" et "tomato early blight" donnent le même
    résultat, ce qui permet d'écrire les labels de CLASS_SPECS comme on
    les voit dans chaque source.
    """
    return " ".join(
        text.lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


# ---------------------------------------------------------------------------
# Classes du projet  <-- C'EST ICI QU'ON AJOUTE UNE CLASSE
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClassSpec:
    """
    Décrit une classe finale (classe dans les datasets) et ses équivalents dans chaque source.

    name           : nom du dossier final dans data/raw (en anglais).
    plantdoc       : labels PlantDoc (Hugging Face), comparés après
                     normalisation.
    mendeley_ids   : IDs de classes dans les annotations YOLO de Mendeley.
    tomato_village : noms de dossiers de classes dans Tomato-Village.
    plantvillage   : noms EXACTS des dossiers dans PlantVillage raw/color
                     (ex. "Tomato___Early_blight").
    """

    name: str
    plantdoc: tuple[str, ...] = ()
    mendeley_ids: tuple[int, ...] = ()
    tomato_village: tuple[str, ...] = ()
    plantvillage: tuple[str, ...] = ()


CLASS_SPECS: list[ClassSpec] = [
    ClassSpec(
        name="Tomato_Healthy",
        plantdoc=("tomato leaf",),
        mendeley_ids=(7,),
        tomato_village=("healthy",),
        plantvillage=("Tomato___healthy",),
    ),
    ClassSpec(
        name="Tomato_Early_Blight",
        plantdoc=("tomato early blight leaf",),
        mendeley_ids=(1,),
        tomato_village=("early blight",),
        plantvillage=("Tomato___Early_blight",),
    ),
    ClassSpec(
        name="Tomato_Late_Blight",
        plantdoc=("tomato leaf late blight",),
        mendeley_ids=(3,),
        tomato_village=("late blight",),
        plantvillage=("Tomato___Late_blight",),
    ),
    # -----------------------------------------------------------------
    # Exemple pour ajouter une classe : décommenter et adapter.
    # Vérifier les noms avec :  --list-labels
    # -----------------------------------------------------------------
    # ClassSpec(
    #     name="Tomato_Leaf_Mold",
    #     plantdoc=("tomato mold leaf",),
    #     mendeley_ids=(3,),
    #     tomato_village=(),  # à compléter avec --list-labels
    #     plantvillage=("Tomato___Leaf_Mold",),
    # ),
]

# Anciens noms français -> nouveaux noms anglais. Sert uniquement à migrer
# un data/raw créé par l'ancienne version du script.
LEGACY_CLASS_DIRS = {
    "Tomate_Saine": "Tomato_Healthy",
    "Tomate_Alternariose": "Tomato_Early_Blight",
    "Tomate_Mildiou": "Tomato_Late_Blight",
}


def build_label_map(attribute: str) -> dict[str, str]:
    """
    Construit {label normalisé -> nom de classe finale} pour une source.

    Lève une erreur si un même label est affecté à deux classes.
    """
    mapping: dict[str, str] = {}

    for spec in CLASS_SPECS:
        for label in getattr(spec, attribute):
            key = normalize(label)

            if key in mapping and mapping[key] != spec.name:
                raise ValueError(
                    f"Label '{label}' ({attribute}) affecté à la fois à "
                    f"'{mapping[key]}' et '{spec.name}'."
                )

            mapping[key] = spec.name

    return mapping


def build_mendeley_id_map() -> dict[int, str]:
    """Construit {id YOLO Mendeley -> nom de classe finale}."""
    mapping: dict[int, str] = {}

    for spec in CLASS_SPECS:
        for class_id in spec.mendeley_ids:
            if class_id in mapping and mapping[class_id] != spec.name:
                raise ValueError(
                    f"ID Mendeley {class_id} affecté à la fois à "
                    f"'{mapping[class_id]}' et '{spec.name}'."
                )

            mapping[class_id] = spec.name

    return mapping


def validate_specs() -> None:
    """Vérifie la cohérence de CLASS_SPECS avant tout téléchargement."""
    if not CLASS_SPECS:
        raise ValueError("CLASS_SPECS est vide.")

    names = [spec.name for spec in CLASS_SPECS]
    duplicates = {name for name in names if names.count(name) > 1}

    if duplicates:
        raise ValueError(f"Noms de classes en double : {sorted(duplicates)}")

    build_label_map("plantdoc")
    build_label_map("tomato_village")
    build_label_map("plantvillage")
    build_mendeley_id_map()


def class_names() -> list[str]:
    return [spec.name for spec in CLASS_SPECS]


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

HF_DATASET = "Project-AgML/plant_doc_classification"
HF_SPLIT = "train"

MENDELEY_URL = (
    "https://data.mendeley.com/public-api/zip/"
    "bpfd9cns5g/download/1"
)

TOMATO_VILLAGE_REPO = (
    "https://github.com/mamta-joshi-gehlot/Tomato-Village.git"
)

TOMATO_VILLAGE_SUBDIR = "Variant-a(Multiclass Classification)"

PLANTVILLAGE_REPO = (
    "https://github.com/spMohanty/PlantVillage-Dataset.git"
)

# Images RGB d'origine. Les variantes "grayscale" et "segmented" ne sont
# pas utilisées : ce sont les mêmes images transformées.
PLANTVILLAGE_VARIANT_DIR = "raw/color"

# Mendeley : signification des IDs YOLO, à titre de documentation.
# Seuls les IDs présents dans CLASS_SPECS (mendeley_ids) sont conservés.
# MENDELEY_YOLO_NAMES = {
#     0: "Early Blight",
#     1: "Black Spot",
#     2: "Late Blight",
#     3: "Leaf Mold",
#     4: "Bacterial Spot",
#     5: "Target Spot",
#     6: "Healthy",
# }
MENDELEY_YOLO_NAMES = {
    1: "Early Blight",
    2: "Black Spot",
    3: "Late Blight",
    4: "Leaf Mold",
    5: "Bacterial Spot",
    6: "Target Spot",
    7: "Healthy",
}

# Préfixe des fichiers générés par chaque source. Ils sont supprimés au
# début d'une nouvelle exécution pour rendre le script ré-exécutable sans
# duplication.
SOURCE_PREFIXES = {
    "plantdoc": "plantdoc_",
    "mendeley": "mendeley_",
    "tomatovillage": "tomatovillage_",
    "plantvillage": "plantvillage_",
}


# ---------------------------------------------------------------------------
# Utilitaires fichiers
# ---------------------------------------------------------------------------

def ensure_dependencies(sources: list[str]) -> None:
    """
    Installe les dépendances Python manquantes, uniquement pour les
    sources demandées (seule PlantDoc a besoin de `datasets` et Pillow ;
    les autres sources n'utilisent que la bibliothèque standard et git).
    """
    if "plantdoc" not in sources:
        return

    packages = {
        "datasets": "datasets",
        "PIL": "Pillow",
        "tqdm": "tqdm",
    }

    missing = []

    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        print("Installation des dépendances :", ", ".join(missing))
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", *missing],
            check=True,
        )


def prepare_raw_directories() -> None:
    """Crée les dossiers de classes sans supprimer les autres données."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for name in class_names():
        (RAW_DIR / name).mkdir(parents=True, exist_ok=True)


def unique_destination(directory: Path, filename: str) -> Path:
    """Retourne un chemin disponible sans écraser un fichier existant."""
    destination = directory / filename

    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 2

    while True:
        candidate = directory / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def migrate_legacy_class_dirs() -> None:
    """
    Déplace le contenu des anciens dossiers français vers les dossiers
    anglais, puis supprime les anciens dossiers vides.

    Sans cette étape, data/raw contiendrait à la fois Tomate_Saine et
    Tomato_Healthy, et la préparation des données créerait 6 classes au
    lieu de 3.
    """
    valid_names = set(class_names())

    for legacy_name, new_name in LEGACY_CLASS_DIRS.items():
        legacy_dir = RAW_DIR / legacy_name

        if not legacy_dir.is_dir() or new_name not in valid_names:
            continue

        new_dir = RAW_DIR / new_name
        new_dir.mkdir(parents=True, exist_ok=True)

        moved = 0

        for path in legacy_dir.iterdir():
            if not path.is_file():
                continue

            shutil.move(
                str(path),
                str(unique_destination(new_dir, path.name)),
            )
            moved += 1

        try:
            legacy_dir.rmdir()
        except OSError:
            print(
                f"Attention : {legacy_dir} n'est pas vide après migration "
                "(sous-dossiers ?). À vérifier manuellement."
            )

        print(f"Migration : {legacy_name} -> {new_name} ({moved} fichier(s)).")


def clean_previous_generated_files(sources: list[str]) -> None:
    """
    Supprime uniquement les fichiers produits par les exécutions
    précédentes des sources demandées.

    Cela évite qu'une deuxième exécution transforme :
        mendeley_000001.jpg
    en :
        mendeley_000001_2.jpg
        mendeley_000001_3.jpg
        ...

    Les images ajoutées manuellement dans data/raw ne sont pas touchées.
    """
    prefixes = tuple(SOURCE_PREFIXES[source] for source in sources)
    removed = 0

    for name in class_names():
        directory = RAW_DIR / name

        if not directory.exists():
            continue

        for path in directory.iterdir():
            if path.is_file() and path.name.startswith(prefixes):
                path.unlink()
                removed += 1

    if removed:
        print(
            f"Nettoyage : {removed} fichier(s) généré(s) "
            "par une exécution précédente supprimé(s)."
        )


def copy_image(
    source: Path,
    final_class: str,
    source_prefix: str,
    index: int,
    extra_name: str | None = None,
) -> Path:
    """Copie une image dans data/raw/<classe>."""
    destination_dir = RAW_DIR / final_class

    if extra_name:
        filename = f"{source_prefix}_{extra_name}_{index:06d}{source.suffix.lower()}"
    else:
        filename = f"{source_prefix}_{index:06d}{source.suffix.lower()}"

    destination = unique_destination(destination_dir, filename)
    shutil.copy2(source, destination)
    return destination


def print_final_counts() -> None:
    print("\n" + "=" * 70)
    print("CONTENU FINAL DE data/raw")
    print("=" * 70)

    total = 0
    width = max(len(name) for name in class_names())

    for name in class_names():
        directory = RAW_DIR / name

        count = sum(
            1
            for file in directory.rglob("*")
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
        )

        total += count
        print(f"{name:{width}s} : {count:6d} images")

    print("-" * 70)
    print(f"{'TOTAL':{width}s} : {total:6d} images")
    print("=" * 70)


def print_class_counters(counters: Counter) -> None:
    for name in class_names():
        print(f"  {name:25s}: {counters[name]:5d}")


def run_git(*arguments: str) -> None:
    subprocess.run(["git", *arguments], check=True)


# ---------------------------------------------------------------------------
# 1. PlantDoc - Hugging Face
# ---------------------------------------------------------------------------

def download_plantdoc() -> None:
    """Télécharge uniquement les classes PlantDoc configurées."""
    print("\n" + "=" * 70)
    print("PLANTDOC / HUGGING FACE")
    print("=" * 70)

    wanted_labels = build_label_map("plantdoc")

    if not wanted_labels:
        print("Aucun label PlantDoc configuré : source ignorée.")
        return

    from datasets import load_dataset

    print(f"Chargement : {HF_DATASET}")

    dataset = load_dataset(
        HF_DATASET,
        split=HF_SPLIT,
    )

    label_names = dataset.features["label"].names

    counters: Counter = Counter()
    seen_labels: set[str] = set()

    for row in dataset:
        original_label = label_names[row["label"]]
        normalized_label = normalize(original_label)

        if normalized_label not in wanted_labels:
            continue

        seen_labels.add(normalized_label)
        final_class = wanted_labels[normalized_label]
        image = row["image"]

        if image is None:
            print("Image PlantDoc ignorée : valeur image vide.")
            continue

        # Normalisation en JPEG pour les images provenant de HF.
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            temporary_path = Path(tmp.name)

        try:
            image.convert("RGB").save(
                temporary_path,
                format="JPEG",
                quality=95,
            )

            counters[final_class] += 1

            copy_image(
                source=temporary_path,
                final_class=final_class,
                source_prefix="plantdoc",
                index=counters[final_class],
            )
        finally:
            temporary_path.unlink(missing_ok=True)

    missing = set(wanted_labels) - seen_labels
    if missing:
        print(
            "\nAttention : labels PlantDoc configurés mais introuvables : "
            f"{sorted(missing)}\n"
            "Vérifier avec --list-labels."
        )

    print("\nPlantDoc ajouté :")
    print_class_counters(counters)


# ---------------------------------------------------------------------------
# 2. Tomato Leaf Dataset - Mendeley
# ---------------------------------------------------------------------------

def download_file(url: str, destination: Path) -> None:
    """Téléchargement streaming avec progression."""
    print(f"Téléchargement : {url}")

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    with urlopen(request) as response:
        total = response.headers.get("Content-Length")
        total = int(total) if total else None

        downloaded = 0
        chunk_size = 1024 * 1024

        with destination.open("wb") as file:
            while True:
                chunk = response.read(chunk_size)

                if not chunk:
                    break

                file.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = downloaded * 100 / total
                    print(
                        f"\r  {percent:6.2f}% "
                        f"({downloaded / 1024**2:.1f} MB)",
                        end="",
                    )

    print()


def parse_mendeley_yolo_label(
    label_file: Path,
    id_map: dict[int, str],
) -> tuple[str | None, str]:
    """
    Lit un fichier d'annotation YOLO Mendeley.

    Retourne :
        (classe_finale, statut)

    statuts possibles :
        - "ok"
        - "empty"
        - "invalid"
        - "unknown_class"
        - "ambiguous"

    Une image n'est retenue que si toutes ses annotations appartiennent à
    une seule des classes que nous voulons conserver.
    """
    class_ids: list[int] = []

    try:
        content = label_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None, "invalid"

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()

        if not line:
            continue

        fields = line.split()

        # Format YOLO minimal : class_id x_center y_center width height
        if len(fields) < 5:
            return None, f"invalid_line_{line_number}"

        try:
            class_id = int(float(fields[0]))
        except ValueError:
            return None, f"invalid_class_id_{line_number}"

        class_ids.append(class_id)

    if not class_ids:
        return None, "empty"

    unique_ids = set(class_ids)

    # Une image contenant plusieurs classes différentes est ambiguë pour
    # notre tâche de classification mono-classe.
    if len(unique_ids) > 1:
        return None, "ambiguous"

    class_id = class_ids[0]

    if class_id not in id_map:
        return None, "unknown_class"

    return id_map[class_id], "ok"


def find_mendeley_annotated_images(
    extracted_dir: Path,
    id_map: dict[int, str],
) -> tuple[list[tuple[Path, str, str]], Counter]:
    """
    Recherche les images dans :

        TomatoLeafMulticlass (Annotated)/
            train/images/
            train/labels/
            valid/images/
            valid/labels/
            test/images/
            test/labels/

    Pour chaque image, son fichier .txt ayant le même stem est recherché.
    Le premier champ de l'annotation YOLO donne le class_id.

    Retourne :
        images valides + statistiques de diagnostic.
    """
    results: list[tuple[Path, str, str]] = []
    stats: Counter = Counter()

    annotated_dirs = [
        path
        for path in extracted_dir.rglob("*")
        if path.is_dir()
        and normalize(path.name) == "tomatoleafmulticlass (annotated)"
    ]

    if not annotated_dirs:
        raise RuntimeError(
            "Le dossier 'TomatoLeafMulticlass (Annotated)' est introuvable "
            "dans l'archive Mendeley."
        )

    annotated_dir = annotated_dirs[0]

    for split in ("train", "valid", "val", "test"):
        split_dir = annotated_dir / split

        if not split_dir.exists():
            continue

        images_dir = split_dir / "images"
        labels_dir = split_dir / "labels"

        if not images_dir.exists():
            continue

        if not labels_dir.exists():
            print(f"Attention : labels absent pour '{split}'.")
            continue

        for image_path in images_dir.iterdir():
            if not image_path.is_file():
                continue

            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            stats["images_found"] += 1

            label_path = labels_dir / f"{image_path.stem}.txt"

            if not label_path.exists():
                stats["missing_label"] += 1
                continue

            final_class, status = parse_mendeley_yolo_label(
                label_path,
                id_map,
            )

            if status != "ok":
                stats[status] += 1
                continue

            # split est conservé uniquement comme information de provenance.
            results.append((image_path, final_class, split))
            stats["images_selected"] += 1

    return results, stats


def download_mendeley() -> None:
    """
    Télécharge le ZIP Mendeley v1 et utilise la version Annotated.

    Le dossier Raw Data est volontairement ignoré : il contient les images
    sans organisation par classe dans l'archive actuellement téléchargée.
    """
    print("\n" + "=" * 70)
    print("TOMATO LEAF DATASET / MENDELEY")
    print("=" * 70)

    id_map = build_mendeley_id_map()

    if not id_map:
        print("Aucun ID Mendeley configuré : source ignorée.")
        return

    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        zip_path = temp_dir / "tomato_leaf_dataset.zip"
        extract_dir = temp_dir / "extracted"

        download_file(MENDELEY_URL, zip_path)

        print("Extraction du ZIP...")
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)

        print("Recherche des images dans 'Annotated'...")
        print("Lecture des labels YOLO (.txt)...")

        images, stats = find_mendeley_annotated_images(extract_dir, id_map)

        if not images:
            raise RuntimeError(
                "Aucune image Mendeley exploitable n'a été trouvée dans "
                "'TomatoLeafMulticlass (Annotated)'.\n"
                f"Statistiques : {dict(stats)}"
            )

        counters: Counter = Counter()
        split_counters: Counter = Counter()

        for source, final_class, split in images:
            counters[final_class] += 1
            split_counters[split] += 1

            # Le nom d'origine est conservé pour faciliter la traçabilité.
            # Exemple : mendeley_train_IMG_0212_....jpg
            destination_dir = RAW_DIR / final_class

            filename = f"mendeley_{split}_{source.name}"
            destination = unique_destination(destination_dir, filename)
            shutil.copy2(source, destination)

        print("\nMendeley ajouté depuis 'Annotated' :")
        print_class_counters(counters)

        print("\nRépartition des images sélectionnées par split :")
        for split in ("train", "valid", "val", "test"):
            if split_counters[split]:
                print(f"  {split:25s}: {split_counters[split]:5d}")

        print("\nDiagnostic Mendeley :")
        print(f"  Images trouvées              : {stats['images_found']}")
        print(f"  Images sélectionnées         : {stats['images_selected']}")
        print(f"  Labels manquants             : {stats['missing_label']}")
        print(f"  Labels vides                 : {stats['empty']}")
        print(f"  Annotations ambiguës         : {stats['ambiguous']}")
        print(f"  Classes non retenues         : {stats['unknown_class']}")

        invalid_total = sum(
            value
            for key, value in stats.items()
            if key.startswith("invalid")
        )
        print(f"  Labels invalides             : {invalid_total}")


# ---------------------------------------------------------------------------
# 3. Tomato-Village - GitHub
# ---------------------------------------------------------------------------

def clone_tomato_village(destination: Path) -> None:
    """Clone uniquement Variant-a(Multiclass Classification)."""
    if destination.exists():
        shutil.rmtree(destination)

    print("Clonage partiel de Tomato-Village...")

    run_git(
        "clone",
        "--depth", "1",
        "--filter=blob:none",
        "--sparse",
        TOMATO_VILLAGE_REPO,
        str(destination),
    )

    run_git(
        "-C", str(destination),
        "sparse-checkout", "set",
        TOMATO_VILLAGE_SUBDIR,
    )


def find_tomato_village_images(
    variant_dir: Path,
    wanted: dict[str, str],
) -> list[tuple[Path, str, str]]:
    """Recherche les classes utiles dans train/val/test de Variant-a."""
    results = []

    for path in variant_dir.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        normalized_parts = [normalize(part) for part in path.parts]

        split = None
        for candidate in ("train", "val", "valid", "test"):
            if candidate in normalized_parts:
                split = candidate
                break

        if split is None:
            continue

        matched_class = None

        for part in reversed(normalized_parts):
            if part in wanted:
                matched_class = wanted[part]
                break

        if matched_class:
            results.append((path, matched_class, split))

    return results


def download_tomato_village() -> None:
    """Clone Tomato-Village Variant-a et fusionne ses splits."""
    print("\n" + "=" * 70)
    print("TOMATO-VILLAGE / GITHUB")
    print("=" * 70)

    wanted = build_label_map("tomato_village")

    if not wanted:
        print("Aucun label Tomato-Village configuré : source ignorée.")
        return

    with tempfile.TemporaryDirectory() as temp:
        repo_dir = Path(temp) / "Tomato-Village"

        clone_tomato_village(repo_dir)

        variant_dir = repo_dir / TOMATO_VILLAGE_SUBDIR

        if not variant_dir.exists():
            raise RuntimeError(
                f"Le dossier attendu n'existe pas : {variant_dir}"
            )

        images = find_tomato_village_images(variant_dir, wanted)

        if not images:
            raise RuntimeError(
                "Aucune image Tomato-Village trouvée dans train/val/test. "
                "La structure du dépôt semble avoir changé."
            )

        counters: Counter = Counter()
        split_counters: Counter = Counter()

        for source, final_class, split in images:
            counters[final_class] += 1
            split_counters[split] += 1

            copy_image(
                source=source,
                final_class=final_class,
                source_prefix="tomatovillage",
                index=counters[final_class],
                extra_name=split,
            )

        print("\nTomato-Village ajouté :")
        print_class_counters(counters)

        print("\nRépartition par split :")
        for split in ("train", "val", "valid", "test"):
            if split_counters[split]:
                print(f"  {split:25s}: {split_counters[split]:5d}")


# ---------------------------------------------------------------------------
# 4. PlantVillage - GitHub (raw/color)
# ---------------------------------------------------------------------------

def clone_plantvillage(destination: Path, folders: list[str]) -> None:
    """
    Clone partiel de PlantVillage : seuls les dossiers de classes demandés
    dans raw/color sont téléchargés (le dépôt complet contient 54 306
    images en trois variantes).
    """
    if destination.exists():
        shutil.rmtree(destination)

    print("Clonage partiel de PlantVillage...")

    run_git(
        "clone",
        "--depth", "1",
        "--filter=blob:none",
        "--sparse",
        PLANTVILLAGE_REPO,
        str(destination),
    )

    if folders:
        run_git(
            "-C", str(destination),
            "sparse-checkout", "set",
            *[f"{PLANTVILLAGE_VARIANT_DIR}/{folder}" for folder in folders],
        )


def list_plantvillage_folders(repo_dir: Path) -> list[str]:
    """
    Liste les dossiers de classes de raw/color sans télécharger d'images
    (lecture de l'arbre git uniquement).
    """
    output = subprocess.run(
        [
            "git", "-C", str(repo_dir),
            "ls-tree", "-z", "--name-only",
            "HEAD", f"{PLANTVILLAGE_VARIANT_DIR}/",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    return sorted(
        Path(entry).name
        for entry in output.split("\0")
        if entry
    )


def download_plantvillage() -> None:
    """Clone PlantVillage et copie les classes configurées."""
    print("\n" + "=" * 70)
    print("PLANTVILLAGE / GITHUB (raw/color)")
    print("=" * 70)

    # {nom exact du dossier PlantVillage -> classe finale}
    folder_to_class = {
        folder: spec.name
        for spec in CLASS_SPECS
        for folder in spec.plantvillage
    }

    if not folder_to_class:
        print("Aucun dossier PlantVillage configuré : source ignorée.")
        return

    with tempfile.TemporaryDirectory() as temp:
        repo_dir = Path(temp) / "PlantVillage-Dataset"

        clone_plantvillage(repo_dir, list(folder_to_class))

        counters: Counter = Counter()

        for folder, final_class in folder_to_class.items():
            class_dir = repo_dir / PLANTVILLAGE_VARIANT_DIR / folder

            if not class_dir.is_dir():
                print(
                    f"Attention : dossier PlantVillage introuvable : "
                    f"{PLANTVILLAGE_VARIANT_DIR}/{folder}\n"
                    "Vérifier avec --list-labels."
                )
                continue

            for source in sorted(class_dir.iterdir()):
                if not source.is_file():
                    continue

                if source.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                # Le nom d'origine contient un UUID : on le garde pour la
                # traçabilité (et un éventuel regroupement par feuille).
                safe_stem = source.stem.replace(" ", "_")
                filename = f"plantvillage_{safe_stem}{source.suffix.lower()}"

                destination = unique_destination(
                    RAW_DIR / final_class,
                    filename,
                )
                shutil.copy2(source, destination)
                counters[final_class] += 1

        if not counters:
            raise RuntimeError(
                "Aucune image PlantVillage copiée. "
                "La structure du dépôt semble avoir changé."
            )

        print("\nPlantVillage ajouté :")
        print_class_counters(counters)


# ---------------------------------------------------------------------------
# Affichage des labels disponibles (aide à l'ajout de classes)
# ---------------------------------------------------------------------------

def list_plantdoc_labels() -> None:
    print("\n" + "=" * 70)
    print("LABELS PLANTDOC (champ plantdoc de ClassSpec)")
    print("=" * 70)

    from datasets import load_dataset

    dataset = load_dataset(HF_DATASET, split=HF_SPLIT)
    names = dataset.features["label"].names
    counts = Counter(dataset["label"])

    for index, name in enumerate(names):
        print(f"  {name:45s}: {counts[index]:5d} images")


def list_mendeley_labels() -> None:
    print("\n" + "=" * 70)
    print("IDS MENDELEY YOLO (champ mendeley_ids de ClassSpec)")
    print("=" * 70)

    for class_id, name in MENDELEY_YOLO_NAMES.items():
        print(f"  {class_id} -> {name}")


def list_tomato_village_labels() -> None:
    print("\n" + "=" * 70)
    print("LABELS TOMATO-VILLAGE (champ tomato_village de ClassSpec)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp:
        repo_dir = Path(temp) / "Tomato-Village"
        clone_tomato_village(repo_dir)

        variant_dir = repo_dir / TOMATO_VILLAGE_SUBDIR
        counts: Counter = Counter()

        for path in variant_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                counts[path.parent.name] += 1

        for name, count in sorted(counts.items()):
            print(f"  {name:45s}: {count:5d} images")


def list_plantvillage_labels() -> None:
    print("\n" + "=" * 70)
    print("DOSSIERS PLANTVILLAGE raw/color (champ plantvillage de ClassSpec)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp:
        repo_dir = Path(temp) / "PlantVillage-Dataset"
        clone_plantvillage(repo_dir, [])

        for folder in list_plantvillage_folders(repo_dir):
            print(f"  {folder}")


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

DOWNLOADERS = {
    "plantdoc": download_plantdoc,
    "mendeley": download_mendeley,
    "tomatovillage": download_tomato_village,
    "plantvillage": download_plantvillage,
}

LABEL_LISTERS = {
    "plantdoc": list_plantdoc_labels,
    "mendeley": list_mendeley_labels,
    "tomatovillage": list_tomato_village_labels,
    "plantvillage": list_plantvillage_labels,
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Téléchargement et fusion des datasets externes.",
    )

    parser.add_argument(
        "--sources",
        nargs="+",
        choices=list(DOWNLOADERS),
        default=list(DOWNLOADERS),
        help="Sources à traiter (par défaut : toutes).",
    )

    parser.add_argument(
        "--list-labels",
        action="store_true",
        help="Affiche les labels disponibles dans chaque source "
             "puis quitte (aide pour compléter CLASS_SPECS).",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    sources: list[str] = arguments.sources

    validate_specs()

    if arguments.list_labels:
        ensure_dependencies(sources)

        for source in sources:
            LABEL_LISTERS[source]()

        return

    print("=" * 70)
    print("COLLECTE DES DATASETS - IA_detection_maladies_plantes")
    print("=" * 70)
    print(f"Projet      : {PROJECT_ROOT}")
    print(f"Destination : {RAW_DIR}")
    print(f"Classes     : {', '.join(class_names())}")
    print(f"Sources     : {', '.join(sources)}")

    ensure_dependencies(sources)
    prepare_raw_directories()
    migrate_legacy_class_dirs()
    clean_previous_generated_files(sources)

    for source in sources:
        DOWNLOADERS[source]()

    print_final_counts()

    print("\nTerminé.")
    print("Aucune séparation train/validation/test finale n'a été effectuée.")
    print("Les données sont regroupées dans data/raw/.")


if __name__ == "__main__":
    main()
