FROM python:3.12.11-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY apps/api /app/apps/api
RUN pip install --no-cache-dir uv==0.11.28 && cd /app/apps/api && uv sync --frozen --no-dev
COPY scripts/generate_demo.py /app/scripts/generate_demo.py
ENV PATH="/app/apps/api/.venv/bin:${PATH}" PYTHONPATH="/app/apps/api/src"
RUN mkdir -p /app/data/generated /app/assets
WORKDIR /app
CMD ["sh", "-c", "python /app/scripts/generate_demo.py --output /app/data/generated && python -m quoteflow.cli init-demo --full && uvicorn quoteflow.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
