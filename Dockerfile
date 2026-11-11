FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RECOUP_DB=/data/recoup.db

WORKDIR /app
COPY pyproject.toml README.md ./
COPY recoup/ ./recoup/
COPY cases/ ./cases/
RUN python -m pip install --no-cache-dir .

EXPOSE 8501

# Mount the Railway volume at /data. Relative adapter recordings live there too.
# Credentials are runtime environment secrets, never build arguments.
CMD ["sh", "-c", "mkdir -p /data && ln -sfn /app/cases /data/cases && cd /data && exec python -m streamlit run /app/recoup/ui/workbench.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true --server.enableXsrfProtection=true --server.enableCORS=true --client.showErrorDetails=none --browser.gatherUsageStats=false"]
