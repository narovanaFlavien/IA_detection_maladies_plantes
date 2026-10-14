# ---------- Étape 1 : build du frontend ----------
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Même origine que l'API : appels relatifs (/api/predict)
ENV VITE_API_URL=""
RUN npm run build

# ---------- Étape 2 : runtime ----------
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Hugging Face Spaces exécute le conteneur avec l'utilisateur 1000
RUN useradd -m -u 1000 user
WORKDIR /app

# PyTorch CPU (beaucoup plus léger que les wheels CUDA)
RUN pip install torch==2.14.0 torchvision==0.29.0 \
    --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip install "fastapi[standard]>=0.141.1" pillow

# Disposition attendue par model_service.py : <racine>/backend et <racine>/models
COPY --chown=user backend/ /app/backend/
COPY --chown=user models/ /app/models/
COPY --from=frontend-build --chown=user /frontend/dist /app/static

ENV STATIC_DIR=/app/static HOME=/home/user
USER user
WORKDIR /app/backend

EXPOSE 7860
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "7860"]