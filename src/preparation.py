"""
Préparation du dataset pour IA_detection_maladies_plantes.

Ce script transforme data/raw/ en data/processed/ en appliquant, dans cet ordre :

    1. découverte des images par classe ;
    2. validation des fichiers image ;
    3. suppression des doublons exacts (hash SHA-256) ;
    4. suppression des images très similaires (perceptual hash / pHash) ;
    5. limitation optionnelle du nombre d'images par SOURCE et par CLASSE ;
    6. séparation reproductible train / validation / test ;
    7. copie vers data/processed/.

IMPORTANT
---------
Les règles de préparation sont volontairement ici, et non dans
`download_raw_datasets_v2.py` : data/raw reste une copie aussi complète que
possible des données collectées. On peut ainsi modifier les règles de
préparation sans devoir retélécharger les datasets.

Les préfixes générés par download_raw_datasets_v2.py sont utilisés pour
identifier la source :
    plantdoc_
    mendeley_
    tomatovillage_
    plantvillage_

Une image ajoutée manuellement dans data/raw sans préfixe connu est classée
comme source `unknown` et n'est pas concernée par les limites par source.
"""

from __future__ import annotations

import hashlib
import random
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from config import PROJECT_ROOT, TRAIN_RATIO, VAL_RATIO, TEST_RATIO, SEED


# ============================================================================
# CONFIGURATION
# ============================================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
}

RAW_DIR = Path(PROJECT_ROOT) / "data" / "raw"
PROCESSED_DIR = Path(PROJECT_ROOT) / "data" / "processed"

# ---------------------------------------------------------------------------
# Validation des images
# ---------------------------------------------------------------------------

# Une image plus petite que ces dimensions est considérée comme trop petite
# pour notre pipeline de classification.
MIN_WIDTH = 100
MIN_HEIGHT = 100

# Si True, une image contenant un canal alpha (RGBA, etc.) reste acceptée.
# Elle sera simplement lue pour vérifier qu'elle est exploitable.
ALLOW_ALPHA = True

# ---------------------------------------------------------------------------
# Détection des images très similaires
# ---------------------------------------------------------------------------

ENABLE_NEAR_DUPLICATE_REMOVAL = True

# Distance de Hamming maximale entre deux pHash.
# Plus la valeur est petite, plus les images doivent être proches.
# 5 = réglage volontairement assez conservateur pour éviter de supprimer
# des feuilles différentes qui présentent naturellement des motifs proches.
PHASH_DISTANCE_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Limitation du nombre d'images par source et par classe
# ---------------------------------------------------------------------------

# Exemple demandé : au maximum 500 images Tomato_Early_Blight provenant
# de PlantVillage.
#
# Structure :
#     "source": {"classe": nombre_maximum}
#
# Une classe/source absente de ce dictionnaire n'a aucune limite.
SOURCE_CLASS_LIMITS: dict[str, dict[str, int]] = {
    "plantvillage": {
        "Tomato_Early_Blight": 500,
    },
}

# Priorité utilisée lorsqu'une image est détectée comme doublon entre
# plusieurs sources. Une source située plus haut est conservée de préférence.
# L'idée est de privilégier les images de terrain / variées avant les images
# PlantVillage plus contrôlées.
SOURCE_PRIORITY = {
    "tomatovillage": 0,
    "plantdoc": 1,
    "mendeley": 2,
    "plantvillage": 3,
    "unknown": 4,
}

# Préfixes produits par download_raw_datasets_v2.py.
SOURCE_PREFIXES = (
    "plantdoc_",
    "mendeley_",
    "tomatovillage_",
    "plantvillage_",
)


# ============================================================================
# DÉPENDANCES
# ============================================================================


def ensure_imagehash() -> None:
    """Installe imagehash uniquement si nécessaire."""
    try:
        import imagehash  # noqa: F401
    except ImportError:
        print("Installation de la dépendance 'ImageHash'...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "ImageHash"],
            check=True,
        )


# ============================================================================
# OUTILS
# ============================================================================


def source_from_filename(path: Path) -> str:
    """Détermine la source à partir du préfixe du nom de fichier."""
    name = path.name.lower()

    for prefix in SOURCE_PREFIXES:
        if name.startswith(prefix):
            return prefix[:-1]  # plantvillage_ -> plantvillage

    return "unknown"


def source_priority(path: Path) -> int:
    """Retourne la priorité d'une image selon sa source."""
    return SOURCE_PRIORITY.get(source_from_filename(path), 888)


def image_sort_key(path: Path) -> tuple[int, str]:
    """Ordre déterministe : priorité source puis chemin."""
    return source_priority(path), str(path).lower()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calcule le SHA-256 du fichier sans charger tout le fichier en RAM."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def validate_image(path: Path) -> tuple[bool, str]:
    """
    Vérifie qu'un fichier est réellement lisible comme image.

    Retourne (True, "ok") ou (False, raison).
    """
    try:
        from PIL import Image

        # verify() détecte notamment plusieurs fichiers corrompus/tronqués.
        with Image.open(path) as image:
            image.verify()

        # Il faut rouvrir l'image après verify().
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode

            if width < MIN_WIDTH or height < MIN_HEIGHT:
                return False, "too_small"

            if not ALLOW_ALPHA and "A" in mode:
                return False, "alpha_channel"

            # Force la lecture des pixels pour détecter certaines corruptions
            # que verify() ne remonte pas toujours.
            image.load()

        return True, "ok"

    except Exception as exc:  # noqa: BLE001
        return False, f"invalid:{type(exc).__name__}"


def compute_phash(path: Path):
    """Calcule le perceptual hash de l'image."""
    import imagehash
    from PIL import Image

    with Image.open(path) as image:
        return imagehash.phash(image.convert("RGB"))


def phash_distance(hash_a, hash_b) -> int:
    """Distance de Hamming entre deux pHash."""
    return int(hash_a - hash_b)


def make_unique_destination(directory: Path, filename: str) -> Path:
    """Évite d'écraser un fichier déjà présent dans data/processed."""
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


# ============================================================================
# DÉCOUVERTE ET VALIDATION
# ============================================================================


def discover_images() -> dict[str, list[Path]]:
    """Retourne les images regroupées par classe de data/raw."""
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Dossier introuvable : {RAW_DIR}")

    by_class: dict[str, list[Path]] = {}

    for class_dir in sorted(RAW_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not class_dir.is_dir():
            continue

        images = sorted(
            [
                path
                for path in class_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ],
            key=lambda p: str(p).lower(),
        )

        if images:
            by_class[class_dir.name] = images

    return by_class


def validate_all_images(
    by_class: dict[str, list[Path]],
) -> tuple[dict[str, list[Path]], Counter]:
    """Valide les images et retire les fichiers illisibles/irréguliers."""
    valid_by_class: dict[str, list[Path]] = defaultdict(list)
    stats: Counter = Counter()

    print("\n" + "=" * 70)
    print("1/5 - VALIDATION DES IMAGES")
    print("=" * 70)

    for class_name, images in by_class.items():
        for image in images:
            stats["discovered"] += 1
            valid, reason = validate_image(image)

            if not valid:
                stats[reason] += 1
                print(f"  Image ignorée [{reason}] : {image}")
                continue

            valid_by_class[class_name].append(image)
            stats["valid"] += 1

    print(f"Images découvertes : {stats['discovered']}")
    print(f"Images valides     : {stats['valid']}")

    invalid = stats["discovered"] - stats["valid"]
    print(f"Images rejetées    : {invalid}")

    return dict(valid_by_class), stats


# ============================================================================
# DOUBLONS EXACTS
# ============================================================================


def remove_exact_duplicates(
    by_class: dict[str, list[Path]],
) -> tuple[dict[str, list[Path]], Counter]:
    """
    Supprime les doublons exacts détectés par SHA-256.

    Deux cas sont distingués :

    - même hash + même classe : on conserve une seule copie, en privilégiant
      la source définie par SOURCE_PRIORITY ;
    - même hash + classes différentes : il s'agit d'une incohérence de label.
      Dans ce cas, on retire toutes les copies concernées plutôt que de choisir
      arbitrairement une classe.
    """
    print("\n" + "=" * 70)
    print("2/5 - DOUBLONS EXACTS (SHA-256)")
    print("=" * 70)

    all_images = [
        (class_name, image)
        for class_name, images in by_class.items()
        for image in images
    ]
    all_images.sort(key=lambda item: (source_priority(item[1]), str(item[1]).lower()))

    hash_groups: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    stats: Counter = Counter()

    for class_name, image in all_images:
        try:
            file_hash = sha256_file(image)
            hash_groups[file_hash].append((class_name, image))
        except OSError:
            stats["hash_error"] += 1
            print(f"  Erreur de lecture du fichier : {image}")

    removed: set[Path] = set()

    for file_hash, group in hash_groups.items():
        if len(group) <= 1:
            continue

        classes = {class_name for class_name, _ in group}

        if len(classes) > 1:
            # Même image physique, mais plusieurs labels : conflit.
            stats["cross_class_conflicts"] += 1
            stats["cross_class_conflict_images"] += len(group)

            print("\n  ⚠ CONFLIT DE LABEL DÉTECTÉ")
            for class_name, image in group:
                print(f"    {class_name:25s} <- {image}")
                removed.add(image)
            print("    Toutes les copies sont retirées de la préparation.")
            continue

        # Même classe : on conserve la meilleure source selon SOURCE_PRIORITY.
        group.sort(key=lambda item: (source_priority(item[1]), str(item[1]).lower()))
        kept_class, kept_image = group[0]

        for duplicate_class, duplicate_image in group[1:]:
            removed.add(duplicate_image)
            stats["exact_duplicates"] += 1
            print(
                f"  Doublon exact supprimé : {duplicate_image.name}\n"
                f"    copie conservée       : {kept_image.name}"
            )

    result: dict[str, list[Path]] = {}

    for class_name, images in by_class.items():
        result[class_name] = [
            image for image in images if image not in removed
        ]

    print(f"Doublons exacts supprimés        : {stats['exact_duplicates']}")
    print(f"Conflits de labels supprimés     : {stats['cross_class_conflicts']}")
    print(f"Images concernées par ces conflits: {stats['cross_class_conflict_images']}")
    print(f"Erreurs de hash                  : {stats['hash_error']}")

    return result, stats


# ============================================================================
# IMAGES TRÈS SIMILAIRES
# ============================================================================


class PhashIndex:
    """Petit index BK-tree pour rechercher rapidement des pHash proches."""

    def __init__(self) -> None:
        self.root = None

    @staticmethod
    def _children(node):
        return node[2]

    def add(self, hash_value, path: Path) -> None:
        if self.root is None:
            self.root = [hash_value, path, {}]
            return

        node = self.root

        while True:
            distance = phash_distance(hash_value, node[0])
            children = self._children(node)

            if distance not in children:
                children[distance] = [hash_value, path, {}]
                return

            node = children[distance]

    def find_within(self, hash_value, max_distance: int):
        """Retourne une image déjà indexée suffisamment proche, ou None."""
        if self.root is None:
            return None

        stack = [self.root]

        while stack:
            node = stack.pop()
            node_hash, node_path, children = node
            distance = phash_distance(hash_value, node_hash)

            if distance <= max_distance:
                return node_path

            lower = distance - max_distance
            upper = distance + max_distance

            for child_distance, child in children.items():
                if lower <= child_distance <= upper:
                    stack.append(child)

        return None


def remove_near_duplicates(
    by_class: dict[str, list[Path]],
) -> tuple[dict[str, list[Path]], Counter]:
    """
    Supprime les images très similaires à l'intérieur de chaque classe.

    On fait volontairement le pHash classe par classe : deux feuilles de
    maladies différentes peuvent naturellement avoir une apparence globale
    proche, et un seuil pHash ne suffit pas à conclure qu'elles sont des
    doublons. Les conflits de labels identiques sont déjà traités par
    SHA-256 dans l'étape précédente.
    """
    if not ENABLE_NEAR_DUPLICATE_REMOVAL:
        print("\nDétection des images similaires désactivée.")
        return by_class, Counter()

    print("\n" + "=" * 70)
    print("3/5 - IMAGES TRÈS SIMILAIRES (pHash)")
    print("=" * 70)
    print(f"Seuil pHash : {PHASH_DISTANCE_THRESHOLD}")

    result: dict[str, list[Path]] = {}
    stats: Counter = Counter()

    for class_name, images in by_class.items():
        # Priorité aux sources de terrain pour conserver une diversité utile.
        ordered_images = sorted(images, key=image_sort_key)
        index = PhashIndex()
        kept: list[Path] = []

        for image in ordered_images:
            try:
                hash_value = compute_phash(image)
            except Exception as exc:  # noqa: BLE001
                stats["phash_error"] += 1
                print(
                    f"  pHash impossible pour {image.name} "
                    f"[{type(exc).__name__}] : image conservée."
                )
                kept.append(image)
                continue

            similar_to = index.find_within(
                hash_value,
                PHASH_DISTANCE_THRESHOLD,
            )

            if similar_to is not None:
                stats["near_duplicates"] += 1
                stats[f"near_duplicates_{class_name}"] += 1
                print(
                    f"  [{class_name}] Image très similaire supprimée : "
                    f"{image.name}\n"
                    f"    similaire à : {similar_to.name}"
                )
                continue

            index.add(hash_value, image)
            kept.append(image)

        result[class_name] = sorted(kept, key=lambda p: str(p).lower())

    print(f"Images très similaires supprimées : {stats['near_duplicates']}")
    print(f"Erreurs pHash (images conservées) : {stats['phash_error']}")

    return result, stats


# ============================================================================
# LIMITES PAR SOURCE / CLASSE
# ============================================================================


def apply_source_class_limits(
    by_class: dict[str, list[Path]],
) -> tuple[dict[str, list[Path]], Counter]:
    """
    Applique SOURCE_CLASS_LIMITS après déduplication.

    Exemple :
        "plantvillage": {"Tomato_Early_Blight": 500}

    signifie qu'au maximum 500 images PlantVillage seront conservées pour
    Tomato_Early_Blight. Les autres sources ne sont pas limitées.
    """
    print("\n" + "=" * 70)
    print("4/5 - LIMITES PAR SOURCE ET PAR CLASSE")
    print("=" * 70)

    result: dict[str, list[Path]] = {}
    stats: Counter = Counter()

    if not SOURCE_CLASS_LIMITS:
        print("Aucune limite configurée.")
        return by_class, stats

    for class_name, images in by_class.items():
        grouped: dict[str, list[Path]] = defaultdict(list)

        for image in images:
            grouped[source_from_filename(image)].append(image)

        selected: list[Path] = []

        for source, source_images in sorted(grouped.items()):
            source_images = sorted(source_images, key=lambda p: str(p).lower())
            limit = SOURCE_CLASS_LIMITS.get(source, {}).get(class_name)

            if limit is None:
                selected.extend(source_images)
                continue

            if limit < 0:
                raise ValueError(
                    f"Limite invalide pour {source}/{class_name}: {limit}"
                )

            # Mélange reproductible avant la limitation afin que les 500
            # images ne dépendent pas simplement de l'ordre des fichiers.
            local_rng = random.Random(
                f"{SEED}|{source}|{class_name}"
            )
            source_images = source_images.copy()
            local_rng.shuffle(source_images)

            kept = source_images[:limit]
            removed_count = len(source_images) - len(kept)

            selected.extend(kept)
            stats[f"limited_{source}_{class_name}"] += removed_count

            print(
                f"  {source:15s} / {class_name:25s} : "
                f"{len(source_images)} -> {len(kept)}"
            )

        # Remettre dans un ordre déterministe avant le split.
        result[class_name] = sorted(
            selected,
            key=lambda p: (source_priority(p), str(p).lower()),
        )

    total_removed = sum(
        value for key, value in stats.items() if key.startswith("limited_")
    )
    print(f"Images supprimées par les limites : {total_removed}")

    return result, stats


# ============================================================================
# SPLIT TRAIN / VALIDATION / TEST
# ============================================================================


def split_images(images: list[Path]) -> tuple[list[Path], list[Path], list[Path]]:
    """Effectue un split reproductible pour une classe."""
    images = images.copy()
    random.shuffle(images)

    n = len(images)

    train_end = int(n * TRAIN_RATIO)
    val_end = train_end + int(n * VAL_RATIO)

    train_images = images[:train_end]
    val_images = images[train_end:val_end]
    test_images = images[val_end:]

    return train_images, val_images, test_images


def reset_processed_directory() -> None:
    """
    Nettoie uniquement train/val/test.

    D'autres fichiers éventuellement présents dans data/processed (rapports,
    métriques, etc.) ne sont donc pas supprimés.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for split in ("train", "val", "test"):
        split_dir = PROCESSED_DIR / split
        if split_dir.exists():
            print(f"Nettoyage de : {split_dir}")
            shutil.rmtree(split_dir)


def copy_split(
    destination_root: Path,
    class_name: str,
    images: list[Path],
) -> None:
    """Copie les images d'un split dans data/processed."""
    destination_dir = destination_root / class_name
    destination_dir.mkdir(parents=True, exist_ok=True)

    for image in images:
        destination = make_unique_destination(
            destination_dir,
            image.name,
        )
        shutil.copy2(image, destination)


def create_splits(by_class: dict[str, list[Path]]) -> Counter:
    """Crée train/val/test et retourne leurs statistiques."""
    print("\n" + "=" * 70)
    print("5/5 - SPLIT TRAIN / VALIDATION / TEST")
    print("=" * 70)
    print(
        f"Ratios : train={TRAIN_RATIO:.2f}, "
        f"val={VAL_RATIO:.2f}, test={TEST_RATIO:.2f}"
    )

    reset_processed_directory()

    train_path = PROCESSED_DIR / "train"
    val_path = PROCESSED_DIR / "val"
    test_path = PROCESSED_DIR / "test"

    stats: Counter = Counter()

    # Une seule initialisation globale pour que le résultat reste reproductible.
    random.seed(SEED)

    for class_name in sorted(by_class):
        images = by_class[class_name]
        train_images, val_images, test_images = split_images(images)

        copy_split(train_path, class_name, train_images)
        copy_split(val_path, class_name, val_images)
        copy_split(test_path, class_name, test_images)

        stats[f"train_{class_name}"] = len(train_images)
        stats[f"val_{class_name}"] = len(val_images)
        stats[f"test_{class_name}"] = len(test_images)

        print(
            f"  {class_name:25s}: "
            f"train={len(train_images):5d} | "
            f"val={len(val_images):5d} | "
            f"test={len(test_images):5d} | "
            f"total={len(images):5d}"
        )

    return stats


# ============================================================================
# RAPPORT FINAL
# ============================================================================


def count_processed_images() -> Counter:
    """Compte les images réellement présentes dans data/processed."""
    counts: Counter = Counter()

    if not PROCESSED_DIR.exists():
        return counts

    for split in ("train", "val", "test"):
        split_dir = PROCESSED_DIR / split
        if not split_dir.exists():
            continue

        for class_dir in split_dir.iterdir():
            if not class_dir.is_dir():
                continue

            count = sum(
                1
                for path in class_dir.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
            counts[f"{split}/{class_dir.name}"] = count

    return counts


def print_final_report(
    validation_stats: Counter,
    exact_stats: Counter,
    near_stats: Counter,
    limit_stats: Counter,
) -> None:
    """Affiche un résumé complet de la préparation."""
    print("\n" + "=" * 70)
    print("RAPPORT FINAL DE PRÉPARATION")
    print("=" * 70)

    print("\nQualité :")
    print(f"  Images découvertes           : {validation_stats['discovered']}")
    print(f"  Images invalides/irrégulières: {validation_stats['discovered'] - validation_stats['valid']}")
    print(f"  Doublons exacts supprimés   : {exact_stats['exact_duplicates']}")
    print(f"  Images très similaires      : {near_stats['near_duplicates']}")

    limited_total = sum(
        value for key, value in limit_stats.items()
        if key.startswith("limited_")
    )
    print(f"  Images retirées par limites : {limited_total}")

    print("\nContenu final de data/processed :")
    counts = count_processed_images()

    total = 0
    for split in ("train", "val", "test"):
        split_total = 0
        for key, count in sorted(counts.items()):
            if key.startswith(f"{split}/"):
                print(f"  {key:45s}: {count:6d}")
                split_total += count

        total += split_total
        print(f"  {'TOTAL ' + split:45s}: {split_total:6d}")

    print("-" * 70)
    print(f"  {'TOTAL DATASET':45s}: {total:6d}")
    print("=" * 70)


# ============================================================================
# PROGRAMME PRINCIPAL
# ============================================================================


def prepare_data() -> None:
    """Pipeline complet de préparation."""
    print("=" * 70)
    print("PRÉPARATION DU DATASET - IA_detection_maladies_plantes")
    print("=" * 70)
    print(f"Source : {RAW_DIR}")
    print(f"Sortie : {PROCESSED_DIR}")
    print(f"Seed   : {SEED}")

    if not (0 <= TRAIN_RATIO <= 1 and 0 <= VAL_RATIO <= 1 and 0 <= TEST_RATIO <= 1):
        raise ValueError("Les ratios train/val/test doivent être compris entre 0 et 1.")

    if abs((TRAIN_RATIO + VAL_RATIO + TEST_RATIO) - 1.0) > 1e-9:
        raise ValueError(
            "TRAIN_RATIO + VAL_RATIO + TEST_RATIO doit être égal à 1."
        )

    ensure_imagehash()

    discovered = discover_images()
    if not discovered:
        raise RuntimeError(f"Aucune image trouvée dans {RAW_DIR}")

    print("\nImages initiales par classe :")
    for class_name, images in discovered.items():
        print(f"  {class_name:25s}: {len(images):6d}")

    # 1. Validation
    clean, validation_stats = validate_all_images(discovered)

    # 2. Doublons exacts
    clean, exact_stats = remove_exact_duplicates(clean)

    # 3. Images très similaires
    clean, near_stats = remove_near_duplicates(clean)

    # 4. Limites par source/classe
    clean, limit_stats = apply_source_class_limits(clean)

    # 5. Split final
    create_splits(clean)

    print_final_report(
        validation_stats,
        exact_stats,
        near_stats,
        limit_stats,
    )

    print("\nPréparation terminée avec succès.")
    print("data/raw n'a pas été modifié.")


if __name__ == "__main__":
    prepare_data()
