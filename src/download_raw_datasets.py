"""
Téléchargement et fusion des datasets externes pour le projet
IA_detection_maladies_plantes.

À exécuter depuis Google Colab après avoir cloné le dépôt :

    git clone https://github.com/narovanaFlavien/IA_detection_maladies_plantes.git
    %cd IA_detection_maladies_plantes
    python src/download_raw_datasets.py

Le script crée/fusionne :

    data/raw/
    ├── Tomate_Saine/
    ├── Tomate_Alternariose/
    └── Tomate_Mildiou/

Sources :
1. PlantDoc Classification - Hugging Face
2. Tomato Leaf Dataset - Mendeley Data v1
3. Tomato-Village - GitHub, Variant-a (Multiclass Classification)

IMPORTANT :
- Le script ne fait PAS le split train/validation/test final du projet.
- Les splits train/valid/test des datasets externes sont regroupés dans
  data/raw, puis votre pipeline de préparation pourra refaire le split.
- Pour Mendeley, on utilise "TomatoLeafMulticlass (Annotated)" et ses
  fichiers YOLO .txt pour retrouver la classe de chaque image.
- "Raw Data" de Mendeley n'est PAS utilisé, car ses images ne sont pas
  rangées dans des dossiers de classes.
- "Annotated & Augmented" de Mendeley n'est PAS utilisé pour éviter
  d'ajouter des images artificiellement augmentées à cette étape.
- Les noms de fichiers sont préfixés par la source pour éviter les
  collisions et permettre d'identifier la provenance.
- Le script nettoie uniquement les fichiers précédemment générés par ce
  script (préfixes plantdoc_, mendeley_, tomatovillage_) afin d'éviter les
  doublons lors d'une nouvelle exécution. Les autres fichiers de data/raw
  ne sont pas supprimés.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Le script est prévu dans src/ ou scripts/ : dans les deux cas, le projet
# est le dossier parent.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Classes finales du projet.
FINAL_CLASSES = {
    "healthy": "Tomate_Saine",
    "early blight": "Tomate_Alternariose",
    "late blight": "Tomate_Mildiou",
}

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
# Mendeley - mapping des IDs YOLO
# ---------------------------------------------------------------------------

# Dans la version Mendeley utilisée ici, les annotations YOLO codent les
# classes avec les IDs suivants :
#
#   0 -> Early Blight
#   1 -> Black Spot
#   2 -> Late Blight
#   3 -> Leaf Mold
#   4 -> Bacterial Spot
#   5 -> Target Spot
#   6 -> Healthy
#
# Nous ne conservons que 0, 2 et 6.
MENDELEY_YOLO_CLASSES = {
    0: "Tomate_Alternariose",
    2: "Tomate_Mildiou",
    6: "Tomate_Saine",
}

# Fichiers générés par ce script. Ils seront supprimés au début d'une
# nouvelle exécution pour rendre le script ré-exécutable sans duplication.
GENERATED_PREFIXES = (
    "plantdoc_",
    "mendeley_",
    "tomatovillage_",
)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Normalise un nom pour faciliter la comparaison des labels."""
    return " ".join(
        text.lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )


def ensure_dependencies() -> None:
    """Installe les dépendances externes nécessaires si elles manquent."""
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
    """Crée les trois classes finales sans supprimer les autres données."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for class_dir in FINAL_CLASSES.values():
        (RAW_DIR / class_dir).mkdir(parents=True, exist_ok=True)


def clean_previous_generated_files() -> None:
    """
    Supprime uniquement les fichiers produits par les exécutions précédentes.

    Cela évite qu'une deuxième exécution transforme :
        mendeley_000001.jpg
    en :
        mendeley_000001_2.jpg
        mendeley_000001_3.jpg
        ...

    Les éventuelles images PlantVillage déjà présentes dans data/raw ne sont
    pas touchées.
    """
    removed = 0

    for class_dir in FINAL_CLASSES.values():
        directory = RAW_DIR / class_dir

        if not directory.exists():
            continue

        for path in directory.iterdir():
            if not path.is_file():
                continue

            if path.name.startswith(GENERATED_PREFIXES):
                path.unlink()
                removed += 1

    if removed:
        print(
            f"Nettoyage : {removed} fichier(s) généré(s) "
            "par une exécution précédente supprimé(s)."
        )


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

    for class_key, class_name in FINAL_CLASSES.items():
        directory = RAW_DIR / class_name

        count = sum(
            1
            for file in directory.rglob("*")
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
        )

        total += count
        print(f"{class_name:25s}: {count:6d} images")

    print("-" * 70)
    print(f"{'TOTAL':25s}: {total:6d} images")
    print("=" * 70)


# ---------------------------------------------------------------------------
# 1. PlantDoc - Hugging Face
# ---------------------------------------------------------------------------

def download_plantdoc() -> None:
    """Télécharge uniquement les trois classes PlantDoc nécessaires."""
    print("\n" + "=" * 70)
    print("1/3 - PLANTDOC / HUGGING FACE")
    print("=" * 70)

    from datasets import load_dataset

    print(f"Chargement : {HF_DATASET}")

    dataset = load_dataset(
        HF_DATASET,
        split=HF_SPLIT,
    )

    label_feature = dataset.features["label"]
    label_names = label_feature.names

    wanted_labels = {
        "tomato leaf": "Tomate_Saine",
        "tomato leaf late blight": "Tomate_Mildiou",
        "tomato early blight leaf": "Tomate_Alternariose",
    }

    counters = Counter()

    for row in dataset:
        numeric_label = row["label"]
        original_label = label_names[numeric_label]
        normalized_label = normalize(original_label)

        if normalized_label not in wanted_labels:
            continue

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

    print("\nPlantDoc ajouté :")
    for class_name in FINAL_CLASSES.values():
        print(f"  {class_name:25s}: {counters[class_name]:5d}")


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


def parse_mendeley_yolo_label(label_file: Path) -> tuple[str | None, str]:
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
    une seule des trois classes que nous voulons conserver.
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

    if class_id not in MENDELEY_YOLO_CLASSES:
        return None, "unknown_class"

    return MENDELEY_YOLO_CLASSES[class_id], "ok"


def find_mendeley_annotated_images(
    extracted_dir: Path,
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
    stats = Counter()

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

            final_class, status = parse_mendeley_yolo_label(label_path)

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
    print("2/3 - TOMATO LEAF DATASET / MENDELEY")
    print("=" * 70)

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

        images, stats = find_mendeley_annotated_images(extract_dir)

        if not images:
            raise RuntimeError(
                "Aucune image Mendeley exploitable n'a été trouvée dans "
                "'TomatoLeafMulticlass (Annotated)'.\n"
                f"Statistiques : {dict(stats)}"
            )

        counters = Counter()
        split_counters = Counter()

        for source, final_class, split in images:
            counters[final_class] += 1
            split_counters[split] += 1

            # Le nom d'origine est conservé pour faciliter la traçabilité.
            # Exemple : mendeley_train_IMG_0212_....jpg
            safe_original_name = source.name
            destination_dir = RAW_DIR / final_class

            filename = f"mendeley_{split}_{safe_original_name}"
            destination = unique_destination(destination_dir, filename)
            shutil.copy2(source, destination)

        print("\nMendeley ajouté depuis 'Annotated' :")
        for class_name in FINAL_CLASSES.values():
            print(f"  {class_name:25s}: {counters[class_name]:5d}")

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

    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            TOMATO_VILLAGE_REPO,
            str(destination),
        ],
        check=True,
    )

    subprocess.run(
        [
            "git",
            "-C",
            str(destination),
            "sparse-checkout",
            "set",
            TOMATO_VILLAGE_SUBDIR,
        ],
        check=True,
    )


def find_tomato_village_images(
    variant_dir: Path,
) -> list[tuple[Path, str, str]]:
    """Recherche les classes utiles dans train/val/test de Variant-a."""
    wanted = {
        "healthy": "Tomate_Saine",
        "early blight": "Tomate_Alternariose",
        "late blight": "Tomate_Mildiou",
    }

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
    print("3/3 - TOMATO-VILLAGE / GITHUB")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        repo_dir = temp_dir / "Tomato-Village"

        clone_tomato_village(repo_dir)

        variant_dir = repo_dir / TOMATO_VILLAGE_SUBDIR

        if not variant_dir.exists():
            raise RuntimeError(
                f"Le dossier attendu n'existe pas : {variant_dir}"
            )

        images = find_tomato_village_images(variant_dir)

        if not images:
            raise RuntimeError(
                "Aucune image Tomato-Village trouvée dans train/val/test. "
                "La structure du dépôt semble avoir changé."
            )

        counters = Counter()
        split_counters = Counter()

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
        for class_name in FINAL_CLASSES.values():
            print(f"  {class_name:25s}: {counters[class_name]:5d}")

        print("\nRépartition par split :")
        for split in ("train", "val", "valid", "test"):
            if split_counters[split]:
                print(f"  {split:25s}: {split_counters[split]:5d}")


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("COLLECTE DES DATASETS - IA_detection_maladies_plantes")
    print("=" * 70)
    print(f"Projet      : {PROJECT_ROOT}")
    print(f"Destination : {RAW_DIR}")

    ensure_dependencies()
    prepare_raw_directories()
    clean_previous_generated_files()

    download_plantdoc()
    download_mendeley()
    download_tomato_village()

    print_final_counts()

    print("\nTerminé.")
    print("Aucune séparation train/validation/test finale n'a été effectuée.")
    print("Les données sont regroupées dans data/raw/." )
    print("Les fichiers Mendeley proviennent de la version Annotated.")


if __name__ == "__main__":
    main()
