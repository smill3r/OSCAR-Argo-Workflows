FROM python:3.10-slim

WORKDIR /app

RUN pip install minio && pip install requests

COPY split-csv.py .