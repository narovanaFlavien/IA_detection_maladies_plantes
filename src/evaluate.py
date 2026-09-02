import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)


def calculate_metrics(
    y_true,
    y_pred
):
    """
    Calcule les principales métriques
    de classification.
    """

    accuracy = accuracy_score(
        y_true,
        y_pred
    )

    precision = precision_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        average="weighted",
        zero_division=0
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }


def generate_classification_report(
    y_true,
    y_pred,
    class_names
):
    """
    Génère le classification report.
    """

    return classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        digits=4,
        zero_division=0
    )


def generate_confusion_matrix(
    y_true,
    y_pred,
    class_names,
    output_path
):
    """
    Génère et sauvegarde la matrice
    de confusion.
    """

    cm = confusion_matrix(
        y_true,
        y_pred
    )

    plt.figure(
        figsize=(12, 10)
    )

    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        xticklabels=class_names,
        yticklabels=class_names
    )

    plt.xlabel("Prédiction")
    plt.ylabel("Vraie classe")

    plt.title(
        "Matrice de confusion"
    )

    plt.xticks(
        rotation=45,
        ha="right"
    )

    plt.yticks(
        rotation=0
    )

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=300
    )

    plt.close()

    return cm


def evaluate_model(
    model,
    dataloader,
    device,
    class_names,
    output_path
):
    """
    Évalue complètement un modèle
    sur le dataset fourni.
    """

    model.eval()

    all_predictions = []
    all_labels = []

    import torch

    with torch.no_grad():

        for images, labels in dataloader:

            images = images.to(device)

            outputs = model(images)

            predictions = outputs.argmax(
                dim=1
            )

            all_predictions.extend(
                predictions.cpu().numpy()
            )

            all_labels.extend(
                labels.numpy()
            )

    # ========================================================
    # METRIQUES
    # ========================================================

    metrics = calculate_metrics(
        all_labels,
        all_predictions
    )

    # ========================================================
    # CLASSIFICATION REPORT
    # ========================================================

    report = generate_classification_report(
        all_labels,
        all_predictions,
        class_names
    )

    # ========================================================
    # MATRICE DE CONFUSION
    # ========================================================

    confusion_matrix_data = (
        generate_confusion_matrix(
            all_labels,
            all_predictions,
            class_names,
            output_path
        )
    )

    return {
        "metrics": metrics,
        "report": report,
        "confusion_matrix": confusion_matrix_data,
        "y_true": all_labels,
        "y_pred": all_predictions
    }