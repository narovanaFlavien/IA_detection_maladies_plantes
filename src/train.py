import copy
import json
import random

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

import mlflow
import mlflow.pytorch

from config import (
    SEED,
    NUM_EPOCHS,
    LEARNING_RATE,
    BATCH_SIZE,
    MODEL_NAME,
    OPTIMIZER_NAME,
    MLFLOW_EXPERIMENT_NAME,
    MLFLOW_RUN_NAME,
    MODEL_DIR,
    MODEL_FILENAME,
    CLASS_NAMES_FILENAME,
    FIGURES_DIR,
    IMAGE_SIZE
)

from data import (
    create_dataloaders,
    verify_classes
)

from model import create_model
from preparation import prepare_data
from evaluate import evaluate_model, calculate_metrics


# ============================================================
# REPRODUCTIBILITE
# ============================================================

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

print("Device :", device)

if torch.cuda.is_available():
    print(
        "GPU :",
        torch.cuda.get_device_name(0)
    )


# ============================================================
# ENTRAINEMENT D'UNE EPOCH
# ============================================================

def train_one_epoch(
    model,
    loader,
    criterion,
    optimizer
):

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:

        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(
            outputs,
            labels
        )

        loss.backward()

        optimizer.step()

        running_loss += (
            loss.item()
            * images.size(0)
        )

        predictions = outputs.argmax(
            dim=1
        )

        total += labels.size(0)

        correct += (
            predictions == labels
        ).sum().item()

    epoch_loss = running_loss / total

    epoch_accuracy = correct / total

    return epoch_loss, epoch_accuracy


# ============================================================
# VALIDATION
# ============================================================

def validate(
    model,
    loader,
    criterion
):

    model.eval()

    running_loss = 0.0
    correct = 0
    total = 0

    all_predictions = []
    all_labels = []

    with torch.no_grad():

        for images, labels in loader:

            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)

            loss = criterion(
                outputs,
                labels
            )

            running_loss += (
                loss.item()
                * images.size(0)
            )

            predictions = outputs.argmax(
                dim=1
            )

            all_predictions.extend(
                predictions.cpu().numpy()
            )
            
            all_labels.extend(
                labels.cpu().numpy()
            )

            total += labels.size(0)

            correct += (
                predictions == labels
            ).sum().item()

    epoch_loss = running_loss / total

    epoch_accuracy = correct / total

    metrics = calculate_metrics(
        all_labels,
        all_predictions
    )

    return epoch_loss, epoch_accuracy, metrics


# ============================================================
# MAIN
# ============================================================

def main():

    print("\nChargement des données...")
    prepare_data()
    (
        train_loader,
        val_loader,
        test_loader,
        train_dataset,
        val_dataset,
        test_dataset
    ) = create_dataloaders()

    verify_classes(
        train_dataset,
        val_dataset,
        test_dataset
    )

    classes = train_dataset.classes

    num_classes = len(classes)

    print(
        "Nombre de classes :",
        num_classes
    )

    # --------------------------------------------------------
    # MODELE
    # --------------------------------------------------------

    model = create_model(
        num_classes
    )

    model = model.to(device)

    # --------------------------------------------------------
    # LOSS
    # --------------------------------------------------------

    criterion = nn.CrossEntropyLoss()

    # --------------------------------------------------------
    # OPTIMIZER
    # --------------------------------------------------------

    optimizer = optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE
    )

    # --------------------------------------------------------
    # MLflow
    # --------------------------------------------------------

    mlflow.set_experiment(
        MLFLOW_EXPERIMENT_NAME
    )

    with mlflow.start_run(
        run_name=MLFLOW_RUN_NAME
    ):

        # ================================================
        # PARAMETRES
        # ================================================

        mlflow.log_params({
            "model": MODEL_NAME,
            "num_classes": num_classes,
            "image_size": IMAGE_SIZE,
            "batch_size": BATCH_SIZE,
            "epochs": NUM_EPOCHS,
            "learning_rate": LEARNING_RATE,
            "optimizer": OPTIMIZER_NAME,
            "seed": SEED
        })

        print("\nMLflow Run démarré.")

        # ================================================
        # HISTORIQUE
        # ================================================

        history = {
            "train_loss": [],
            "train_accuracy": [],
            "val_loss": [],
            "val_accuracy": [],
            "val_f1": [],
            "val_precision": [],
            "val_recall": []
        }

        best_val_f1_score = 0.0

        best_model_weights = copy.deepcopy(
            model.state_dict()
        )

        # ================================================
        # ENTRAINEMENT
        # ================================================

        for epoch in range(NUM_EPOCHS):

            train_loss, train_accuracy = (
                train_one_epoch(
                    model,
                    train_loader,
                    criterion,
                    optimizer
                )
            )

            val_loss, val_accuracy, val_metrics = (
                validate(
                    model,
                    val_loader,
                    criterion
                )
            )

            # Historique

            history["train_loss"].append(
                train_loss
            )

            history["train_accuracy"].append(
                train_accuracy
            )

            history["val_loss"].append(
                val_loss
            )

            history["val_accuracy"].append(
                # val_accuracy
                val_metrics["accuracy"]
            )
            history["val_f1"].append(
                val_metrics["f1_score"]
            )
            history["val_precision"].append(
                val_metrics["precision"]
            )
            history["val_recall"].append(
                val_metrics["recall"]
            )

            # --------------------------------------------
            # MLflow : métriques de chaque epoch
            # --------------------------------------------

            mlflow.log_metrics({
                "train_loss": train_loss,
                "train_accuracy": train_accuracy,
                "val_loss": val_loss,
                "val_accuracy": val_accuracy,
                "val_precision":val_metrics["precision"],
                "val_recall":val_metrics["recall"],
                "val_f1":val_metrics["f1_score"],
            }, step=epoch)

            print(
                f"Epoch [{epoch + 1}/{NUM_EPOCHS}] | "
                f"Train Loss: {train_loss:.4f} | "
                f"Train Acc: {train_accuracy:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val Acc: {val_accuracy:.4f}"
            )

            # --------------------------------------------
            # Meilleur modèle
            # --------------------------------------------

            if val_metrics["f1_score"] > best_val_f1_score:

                best_val_f1_score = val_metrics["f1_score"]

                best_model_weights = copy.deepcopy(
                    model.state_dict()
                )

                print(
                    "⭐ Nouveau meilleur modèle !"
                )
        # ================================================
        # RESTAURER LE MEILLEUR MODELE
        # ================================================

        model.load_state_dict(
            best_model_weights
        )

        print(
            f"\nMeilleure validation f1 score : "
            f"{best_val_f1_score * 100:.2f}%"
        )

        # ================================================
        # SAUVEGARDER LE MODELE
        # ================================================

        model_path = (
            MODEL_DIR /
            MODEL_FILENAME
        )

        torch.save(
            model.state_dict(),
            model_path
        )

        print(
            "Modèle sauvegardé :",
            model_path
        )


        # ==========================================
        # TEST
        # ==========================================

        evaluation = evaluate_model(
            model=model,
            dataloader=test_loader,
            device=device,
            class_names=classes,
            output_path=FIGURES_DIR
        )

        # ==========================================
        # LOG TEST METRICS
        # ==========================================

        mlflow.log_metrics(
            {
                "test_accuracy":
                    evaluation["metrics"]["accuracy"],

                "test_precision":
                    evaluation["metrics"]["precision"],

                "test_recall":
                    evaluation["metrics"]["recall"],

                "test_f1_score":
                    evaluation["metrics"]["f1_score"]
            }
        )

        mlflow.log_artifact(
            str(FIGURES_DIR)
        )

        mlflow.log_text(
            evaluation["report"],
            "classification_report.txt"
        )

        mlflow.pytorch.log_model(
            model,
            "model"
        )



        # ================================================
        # SAUVEGARDER LES CLASSES
        # ================================================

        class_path = (
            MODEL_DIR /
            CLASS_NAMES_FILENAME
        )

        with open(
            class_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                classes,
                file,
                ensure_ascii=False,
                indent=4
            )

        # ================================================
        # MLflow : METRIQUE FINALE
        # ================================================

        # mlflow.log_metric(
        #     "best_val_accuracy",
        #     best_val_accuracy
        # )

        # ================================================
        # MLflow : MODELE
        # ================================================

        # mlflow.pytorch.log_model(
        #     model,
        #     "model"
        # )

        # ================================================
        # MLflow : classes
        # ================================================

        mlflow.log_artifact(
            str(class_path)
        )

        print(
            "\n✓ Entraînement terminé."
        )

        print(
            "✓ MLflow a enregistré le modèle."
        )


if __name__ == "__main__":
    main()