FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y jq

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el script de Python
COPY recolectar_datos.py .