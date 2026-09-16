from fastapi import FastAPI
from src.backend.routes.prediction import router as prediction_router

app = FastAPI(
    title="Détection des maladies des plantes",
    description="Api de détection des maladies des plantes"
)

@app.get("/")
async def root():
    return {
        "message": "Api de détection des maladies des plantes",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

app.include_router(
    prediction_router,
    prefix="/api"
)