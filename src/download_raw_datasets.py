"""
Téléchargement et fusion des datasets externes pour le projet
IA_detection_maladies_plantes.

À exécuter depuis Google Colab après avoir cloné le dépôt :

    git clone https://github.com/narovanaFlavien/IA_detection_maladies_plantes.git
    %cd IA_detection_maladies_plantes
    python scripts/download_raw_datasets.py

Le script crée/fusionne :

    data/raw/
    ├── Tomate_Saine/
    ├── Tomate_Alternariose/
    └── Tomate_Mildiou/

Sources :
1. PlantDoc Classification - Hugging Face
2. Tomato Leaf Dataset - Mendeley Data v1
3. Tomato-Village - GitHub, Variant-a (Multiclass Classification)

Important :
- Le script ne fait PAS encore train/validation/test.
- Il regroupe train/val/test de Tomato-Village dans les mêmes classes raw.
- Les noms de fichiers sont préfixés par la source pour éviter les collisions.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Si le script est placé dans scripts/, le projet est son dossier parent.
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

# Seule cette variante nous intéresse.
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
    """
    Installe uniquement les dépendances externes nécessaires.

    Colab possède généralement déjà datasets/Pillow/requests,
    mais cette fonction permet au script de rester autonome.
    """
    packages = {
        "datasets": "datasets",
        "PIL": "Pillow",
        "requests": "requests",
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
    """Crée les trois classes finales sans supprimer les données existantes."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for class_dir in FINAL_CLASSES.values():
        (RAW_DIR / class_dir).mkdir(parents=True, exist_ok=True)


def unique_destination(directory: Path, filename: str) -> Path:
    """
    Retourne un chemin disponible.

    En principe les préfixes de source évitent déjà les collisions,
    mais cette fonction protège aussi contre les doublons internes.
    """
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
) -> Path:
    """
    Copie une image dans data/raw/<classe>/ avec un nom déterministe.
    """
    destination_dir = RAW_DIR / final_class

    extension = source.suffix.lower()
    filename = f"{source_prefix}_{index:06d}{extension}"

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
    """
    Télécharge uniquement les trois labels PlantDoc nécessaires.

    Le dataset HF contient 2 569 lignes, un seul split train et une colonne
    image + label. Le label est un ClassLabel dont le nom peut être récupéré
    via dataset.features["label"].names.
    """
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

    print("Labels disponibles recherchés :")
    for label in wanted_labels:
        print(f"  - {label}")

    counters = {
        "Tomate_Saine": 0,
        "Tomate_Alternariose": 0,
        "Tomate_Mildiou": 0,
    }

    for row in dataset:
        numeric_label = row["label"]
        original_label = label_names[numeric_label]
        normalized_label = normalize(original_label)

        if normalized_label not in wanted_labels:
            continue

        final_class = wanted_labels[normalized_label]
        image = row["image"]

        if image is None:
            print("Image ignorée : valeur image vide.")
            continue

        # On convertit toutes les images en RGB/JPEG afin d'obtenir
        # un format homogène dans data/raw.
        with tempfile.NamedTemporaryFile(
            suffix=".jpg",
            delete=False,
        ) as tmp:
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
    for class_name, count in counters.items():
        print(f"  {class_name:25s}: {count:5d}")


# ---------------------------------------------------------------------------
# 2. Tomato Leaf Dataset - Mendeley
# ---------------------------------------------------------------------------

def download_file(url: str, destination: Path) -> None:
    """Téléchargement streaming avec progression simple."""
    print(f"Téléchargement : {url}")

    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urlopen(request) as response:
        total = response.headers.get("Content-Length")

        if total is not None:
            total = int(total)

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


def find_mendeley_raw_images(extracted_dir: Path) -> list[tuple[Path, str]]:
    """
    Recherche les images dans le dossier 'Raw Data' du ZIP Mendeley.

    La documentation du dataset indique :
      Tomato Leaf Multiclass (Raw Data)
          ├── Early Blight
          ├── Black Spot
          ├── Late Blight
          ├── Leaf Mold
          ├── Bacterial Spot
          ├── Target Spot
          └── Healthy

    On privilégie explicitement Raw Data afin de ne pas recopier les
    images présentes une deuxième fois dans la version annotée.
    """
    wanted = {
        "early blight": "Tomate_Alternariose",
        "late blight": "Tomate_Mildiou",
        "healthy": "Tomate_Saine",
    }

    results = []

    for path in extracted_dir.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        parts_normalized = [normalize(part) for part in path.parts]

        # On ne veut que la partie "Raw Data".
        has_raw_data = any(
            "raw data" in part
            for part in parts_normalized
        )

        if not has_raw_data:
            continue

        matched_class = None

        for part in reversed(parts_normalized):
            if part in wanted:
                matched_class = wanted[part]
                break

        if matched_class:
            results.append((path, matched_class))

    return results


def download_mendeley() -> None:
    """
    Télécharge le ZIP Mendeley v1, l'extrait dans un répertoire temporaire,
    puis ne récupère que Healthy/Early Blight/Late Blight.
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

        print("Recherche des images dans 'Raw Data'...")
        images = find_mendeley_raw_images(extract_dir)

        if not images:
            raise RuntimeError(
                "Aucune image Mendeley trouvée dans le dossier "
                "'Raw Data'. La structure du ZIP semble avoir changé."
            )

        counters = {
            "Tomate_Saine": 0,
            "Tomate_Alternariose": 0,
            "Tomate_Mildiou": 0,
        }

        for source, final_class in images:
            counters[final_class] += 1

            copy_image(
                source=source,
                final_class=final_class,
                source_prefix="mendeley",
                index=counters[final_class],
            )

        print("\nMendeley ajouté :")
        for class_name, count in counters.items():
            print(f"  {class_name:25s}: {count:5d}")


# ---------------------------------------------------------------------------
# 3. Tomato-Village - GitHub
# ---------------------------------------------------------------------------

def clone_tomato_village(destination: Path) -> None:
    """
    Clone uniquement Variant-a(Multiclass Classification) grâce au sparse
    checkout afin d'éviter de récupérer les variantes multi-label/object
    detection qui ne sont pas nécessaires ici.
    """
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
) -> list[tuple[Path, str]]:
    """
    Recherche récursivement dans train/, val/ et test/.

    Les trois splits sont volontairement regroupés : le script de
    préparation du dataset fera la nouvelle séparation ultérieurement.

    Seules les classes :
        Healthy
        Early Blight
        Late Blight
    sont conservées.
    """
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

        # Vérification que l'image provient bien de train/val/test.
        if not any(
            part in {"train", "val", "test"}
            for part in normalized_parts
        ):
            continue

        matched_class = None

        # On parcourt le chemin depuis la fin : le dossier de classe
        # est normalement le parent direct ou proche de l'image.
        for part in reversed(normalized_parts):
            if part in wanted:
                matched_class = wanted[part]
                break

        if matched_class:
            results.append((path, matched_class))

    return results


def download_tomato_village() -> None:
    """
    Clone Tomato-Village Variant-a et fusionne train + val + test.
    """
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

        counters = {
            "Tomate_Saine": 0,
            "Tomate_Alternariose": 0,
            "Tomate_Mildiou": 0,
        }

        # Les trois splits sont tous parcourus.
        for source, final_class in images:
            counters[final_class] += 1

            copy_image(
                source=source,
                final_class=final_class,
                source_prefix="tomatovillage",
                index=counters[final_class],
            )

        print("\nTomato-Village ajouté :")
        for class_name, count in counters.items():
            print(f"  {class_name:25s}: {count:5d}")


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("COLLECTE DES DATASETS - IA_detection_maladies_plantes")
    print("=" * 70)
    print(f"Projet : {PROJECT_ROOT}")
    print(f"Destination : {RAW_DIR}")

    ensure_dependencies()
    prepare_raw_directories()

    download_plantdoc()
    download_mendeley()
    download_tomato_village()

    print_final_counts()

    print("\nTerminé.")
    print("Aucune séparation train/validation/test n'a été effectuée.")
    print("Les données sont maintenant regroupées dans data/raw/.")


if __name__ == "__main__":
    main()
