# Entorno del tablero, del pipeline y de MLflow (Laboratorio 11).
# Los datos institucionales NO entran a la imagen (.dockerignore excluye data/): se montan desde
# docker-compose.yml. Las salidas y los registros de MLflow tambien viven en carpetas montadas.
FROM python:3.13-slim

# Commit del codigo copiado a la imagen; el pipeline lo registra en MLflow (no hay .git adentro)
ARG GIT_COMMIT=desconocido
ENV GIT_COMMIT=${GIT_COMMIT} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements-pipeline.txt requirements-docker.txt ./
RUN pip install -r requirements-docker.txt

COPY . .

EXPOSE 8501 5000
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
