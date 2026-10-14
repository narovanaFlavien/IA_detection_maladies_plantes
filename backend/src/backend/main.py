import os
from fastapi import FastAPI
from src.backend.routes.prediction import router as prediction_router
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

app.include_router(
    prediction_router,
    prefix="/api"
)

# ============================================================
# FRONTEND (build Vite) : actif uniquement si STATIC_DIR existe
# ============================================================
STATIC_DIR = Path(os.getenv("STATIC_DIR", "/app/static"))

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR.resolve()):
            return FileResponse(candidate)
        # Fallback SPA : /detecter, /maladies... gérés par react-router
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return {"message": "Api de détection des maladies des plantes", "version": "1.0.0"}