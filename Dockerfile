FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY deadresult/ deadresult/
COPY migrations/ migrations/
COPY alembic.ini .

RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "deadresult.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
