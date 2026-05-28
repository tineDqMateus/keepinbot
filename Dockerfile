# ── Image de base ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Métadonnées ───────────────────────────────────────────────────────────────
LABEL maintainer="Keepinbot"
LABEL description="Assistant documentaire RAG hybride pour PME/TPE"

# ── Variables d'environnement ─────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ── Dépendances système ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# ── Dépendances Python ────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Code de l'application ─────────────────────────────────────────────────────
COPY app/ ./app/
COPY scripts/ ./scripts/

# ── Dossiers de données ───────────────────────────────────────────────────────
RUN mkdir -p data/corpus data/chroma data/public/indexed data/public/archive \
    data/samples data/veille

# ── Cron — veille réglementaire quotidienne à 6h ─────────────────────────────
RUN echo "0 6 * * * cd /app && python scripts/run_veille.py >> /var/log/veille.log 2>&1" | crontab -

# ── Port exposé ───────────────────────────────────────────────────────────────
EXPOSE 8501

# ── Démarrage : cron + Streamlit ─────────────────────────────────────────────
CMD cron && streamlit run app/main.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true