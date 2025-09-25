FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	DB_PATH=/data/opentap.db

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
	&& useradd -u 1000 -m appuser

COPY . .

# Expose data volume separately for persistence (SQLite DB & uploaded images)
VOLUME ["/data"]

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
