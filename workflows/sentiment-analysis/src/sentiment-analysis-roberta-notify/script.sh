#!/bin/bash

echo "Ejecutando servicio de analisis de sentimientos..."

# Ejecutar el script de Python usando el archivo de entrada proporcionado por OSCAR
python sentiment-analysis.py "$INPUT_FILE_PATH" "$TMP_OUTPUT_DIR"

echo "Proceso completado. Archivos disponibles en $TMP_OUTPUT_DIR"