FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


# Ejecutar migraciones automáticamente antes de iniciar la aplicación
# Nota: alembic upgrade head es idempotente - solo aplica migraciones pendientes
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
