FROM python:3.11-slim

# Evitar que Python genere .pyc y usar stdout sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copiar el resto del código
COPY . .

# 3) Puerto para Cloud Run
ENV PORT=8080

# 4) Comando para arrancar FastAPI con Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
