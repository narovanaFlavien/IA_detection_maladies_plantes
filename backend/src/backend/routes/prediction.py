from io import BytesIO

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile
)

from PIL import Image, UnidentifiedImageError

from src.backend.schemas.prediction import PredictionResponse

from src.backend.services.model_service import predict


router = APIRouter(
    tags=["Prediction"]
)


@router.post(
    "/predict",
    response_model=PredictionResponse
)
async def predict_disease(
    file: UploadFile = File(...)
):

    # ========================================================
    # VERIFICATION DU TYPE DE FICHIER
    # ========================================================

    if file.content_type not in [
        "image/jpeg",
        "image/png",
        "image/webp"
    ]:

        raise HTTPException(
            status_code=400,
            detail=(
                "Format d'image non supporté. "
                "Utilisez JPEG, PNG ou WEBP."
            )
        )


    # ========================================================
    # LECTURE DE L'IMAGE
    # ========================================================

    contents = await file.read()


    try:

        image = Image.open(
            BytesIO(contents)
        )

        image.load()

    except (
        UnidentifiedImageError,
        OSError
    ):

        raise HTTPException(
            status_code=400,
            detail="Le fichier envoyé n'est pas une image valide."
        )


    # ========================================================
    # PREDICTION
    # ========================================================

    try:

        result = predict(
            image
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Une erreur est survenue "
                "pendant la prédiction."
            )
        ) from error


    return result