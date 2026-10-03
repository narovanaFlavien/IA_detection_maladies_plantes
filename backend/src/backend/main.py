import os
from fastapi import FastAPI
from src.backend.routes.prediction import router as prediction_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Détection des maladies des plantes",
    description="Api de détection des maladies des plantes"
)

# ============================================================
# CORS
# ============================================================
# En dev, le frontend (Vite, port 5173) et le backend (port 8000) sont
# sur des origines différentes : sans ce middleware, le navigateur
# bloque les requêtes fetch() côté frontend.
# ALLOWED_ORIGINS est surchargeable via une variable d'environnement
# pour la prod (ex: ALLOWED_ORIGINS=https://plantsafe.example.com).
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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