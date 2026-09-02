import torch

from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import EfficientNet_B0_Weights
from torch.utils.data import DataLoader

from config import (
    TRAIN_DIR,
    VAL_DIR,
    TEST_DIR,
    IMAGE_SIZE,
    BATCH_SIZE,
    NUM_WORKERS
)


def get_transforms():
    """
    Retourne les transformations pour train,
    validation et test.
    """

    weights = EfficientNet_B0_Weights.DEFAULT

    mean = weights.transforms().mean
    std = weights.transforms().std

    train_transform = transforms.Compose([
        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
        ),

        transforms.RandomHorizontalFlip(
            p=0.5
        ),

        transforms.RandomRotation(
            15
        ),

        transforms.ColorJitter(
            brightness=0.2,
            contrast=0.2
        ),

        transforms.ToTensor(),

        transforms.Normalize(
            mean=mean,
            std=std
        )
    ])

    val_test_transform = transforms.Compose([
        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE)
        ),

        transforms.ToTensor(),

        transforms.Normalize(
            mean=mean,
            std=std
        )
    ])

    return train_transform, val_test_transform


def create_datasets():
    """
    Créé les datasets PyTorch.
    """

    train_transform, val_test_transform = get_transforms()

    train_dataset = ImageFolder(
        root=TRAIN_DIR,
        transform=train_transform
    )

    val_dataset = ImageFolder(
        root=VAL_DIR,
        transform=val_test_transform
    )

    test_dataset = ImageFolder(
        root=TEST_DIR,
        transform=val_test_transform
    )

    return (
        train_dataset,
        val_dataset,
        test_dataset
    )


def create_dataloaders():
    """
    Créé les DataLoaders.
    """

    (
        train_dataset,
        val_dataset,
        test_dataset
    ) = create_datasets()

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=NUM_WORKERS
    )

    return (
        train_loader,
        val_loader,
        test_loader,
        train_dataset,
        val_dataset,
        test_dataset
    )


def verify_classes(
    train_dataset,
    val_dataset,
    test_dataset
):
    """
    Vérifie que les trois datasets
    possèdent les mêmes classes.
    """

    if train_dataset.classes != val_dataset.classes:
        raise ValueError(
            "Les classes Train et Validation sont différentes."
        )

    if train_dataset.classes != test_dataset.classes:
        raise ValueError(
            "Les classes Train et Test sont différentes."
        )

    print("Classes :", train_dataset.classes)

    print(
        "Correspondance :",
        train_dataset.class_to_idx
    )

    return True