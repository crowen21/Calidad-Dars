#!/usr/bin/env bash
# Actualiza el dashboard y su backend en el EC2.
# Correr esto DENTRO del servidor, parado en /var/www/dars-calidad
set -euo pipefail

echo "==> Trayendo últimos cambios de GitHub..."
git pull

echo "==> Instalando/actualizando dependencias del backend..."
cd backend
if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/pip install -q -r requirements.txt

echo "==> Reiniciando el servicio del backend..."
sudo systemctl restart calidad-agentes

echo "==> Recargando nginx (por si cambió el HTML)..."
sudo nginx -t && sudo systemctl reload nginx

echo "==> Listo. Backend en :8001, frontend servido por nginx."
