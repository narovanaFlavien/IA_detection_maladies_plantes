from pathlib import Path


# ============================================================
# CHEMINS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
print(PROJECT_ROOT)

DATASET_DIR = PROJECT_ROOT / "data" / "processed"

TRAIN_DIR = DATASET_DIR / "train"
VAL_DIR = DATASET_DIR / "val"
TEST_DIR = DATASET_DIR / "test"

MODEL_DIR = PROJECT_ROOT / "models"

OUTPUT_DIR = PROJECT_ROOT / "outputs"

FIGURES_DIR = OUTPUT_DIR / "figures"
REPORTS_DIR = OUTPUT_DIR / "reports"


# ============================================================
# DATASET
# ============================================================

IMAGE_SIZE = 224

BATCH_SIZE = 32

NUM_WORKERS = 2

SEED = 42


# ============================================================
# ENTRAINEMENT
# ============================================================

NUM_EPOCHS = 10

LEARNING_RATE = 0.001

MODEL_NAME = "EfficientNet-B0"

OPTIMIZER_NAME = "Adam"

# ============================================================
# RATION Separation TRAIN/VALIDATION/TEST
# ============================================================

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# ============================================================
# MLflow
# ============================================================

MLFLOW_EXPERIMENT_NAME = "Plant Disease Classification"

MLFLOW_RUN_NAME = "EfficientNet-B0-v1"


# ============================================================
# FICHIERS
# ============================================================

MODEL_FILENAME = "efficientnet_b0_v1.pt"

CLASS_NAMES_FILENAME = "classes.json"

MODEL_INFO_FILENAME = "model_info.json"


# ============================================================
# CREATION DES DOSSIERS
# ============================================================

for directory in [
    MODEL_DIR,
    OUTPUT_DIR,
    FIGURES_DIR,
    REPORTS_DIR
]:
    directory.mkdir(
        parents=True,
        exist_ok=True
    )