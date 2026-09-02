from pathlib import Path
from config import (
    PROJECT_ROOT,
    TRAIN_RATIO, VAL_RATIO, TEST_RATIO,
    SEED
)
# from PIL import Image

# import numpy as np
import random
import shutil
# import pandas as pd
# import matplotlib.pyplot as plt

image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
data_raw_path = Path(f"{PROJECT_ROOT}/data/raw")

#Exclure les images invalides

def prepare_data():
    #Séparation TRAIN/VALIDATION/TEST
    #Pour que votre séparation soit reproductible: fixer le random seed
    random.seed(SEED)

    #Ainsi, si nous relançons notre notebook, nous pourrons retrouver la même séparation.

    #Créer les dossiers
    processed_path = Path(f"{PROJECT_ROOT}/data/processed")

    train_path = processed_path / "train"
    val_path = processed_path / "val"
    test_path = processed_path / "test"

    for path in [train_path, val_path, test_path]:
        path.mkdir(parents=True, exist_ok=True)



    for class_dir in data_raw_path.iterdir():

        if not class_dir.is_dir():
            continue

        images = [
            p for p in class_dir.rglob("*")
            if p.suffix.lower() in image_extensions
        ]

        random.shuffle(images)

        n = len(images)

        train_end = int(n * TRAIN_RATIO)
        val_end = train_end + int(n * VAL_RATIO)

        train_images = images[:train_end]
        val_images = images[train_end:val_end]
        test_images = images[val_end:]

        for destination, image_list in [
            (train_path, train_images),
            (val_path, val_images),
            (test_path, test_images)
        ]:

            class_destination = destination / class_dir.name
            class_destination.mkdir(parents=True, exist_ok=True)

            for image in image_list:
                shutil.copy2(
                    image,
                    class_destination / image.name
                )

    print("Séparation terminée.")