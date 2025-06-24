#!/bin/bash

echo "Ejecutando servicio de recolección de datos de Reddit..."

# Ejecutar el script de Python usando el archivo de entrada proporcionado por OSCAR
python recolectar_datos.py "$INPUT_FILE_PATH" "$TMP_OUTPUT_DIR"

echo "Proceso completado. Archivos disponibles en $TMP_OUTPUT_DIR"