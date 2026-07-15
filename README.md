# DARS Calidad Dashboard - Agentes

Dashboard de calidad (Agendamiento, Protocolo de atención, Entrega de la información,
Tipificación, CPO y ámbitos complementarios), con backend propio para que los datos
queden compartidos entre todo el equipo en vez de vivir solo en el navegador de cada uno.

## Estructura

- `index.html` — el dashboard (frontend). Habla con el backend vía `/api/calidad-agentes/state`.
- `backend/` — FastAPI + SQLite, aislado de cualquier otro backend que ya corra en el EC2.
  Usa su propio archivo `calidad_agentes.db` y sus propias rutas bajo `/api/calidad-agentes/`,
  así que no choca con otros proyectos de Salud Responde en el mismo servidor.
- `nginx-dars-calidad.conf` — sirve el HTML como sitio estático y hace de proxy hacia el backend.
- `calidad-agentes.service` — unidad systemd para mantener el backend corriendo.
- `deploy.sh` — script para actualizar todo desde el EC2 (`git pull` + reinstalar + reiniciar).

## Antes de poner esto en producción

1. **Cambiar la clave compartida** en DOS lugares (deben coincidir):
   - `index.html`: constante `API_KEY` cerca de la sección "Persistencia".
   - `backend/calidad-agentes.service`: variable de entorno `CALIDAD_AGENTES_API_KEY`.
   - Esta clave queda visible en el código fuente del HTML (cualquiera que abra
     "Ver código fuente" en el navegador puede leerla) — es el trade-off de usar
     una clave simple compartida en un frontend estático en vez de login por usuario.
     Alcanza para evitar cargas accidentales o de gente fuera del equipo, no es
     seguridad fuerte.
2. **Editar `nginx-dars-calidad.conf`**: poner el subdominio real en `server_name`
   si se va a usar uno, o dejar `_` si solo se accede por IP/puerto.

## Primer deploy en el EC2

```bash
sudo mkdir -p /var/www/dars-calidad
sudo chown $USER:$USER /var/www/dars-calidad
git clone <URL_DEL_REPO> /var/www/dars-calidad
cd /var/www/dars-calidad/backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
sudo cp calidad-agentes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now calidad-agentes
sudo cp ../nginx-dars-calidad.conf /etc/nginx/sites-available/dars-calidad
sudo ln -s /etc/nginx/sites-available/dars-calidad /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Actualizaciones siguientes

Desde el EC2, parado en `/var/www/dars-calidad`:

```bash
./deploy.sh
```

## Diseño de los datos

El frontend mantiene `entries` (notas cargadas) y `rosterChanges` (altas/bajas de
profesionales) en memoria, igual que antes con localStorage. Ahora, además de
guardarlos localmente como caché, los reenvía completos al backend en cada cambio
(`POST /api/calidad-agentes/state`), que sobrescribe el estado guardado en SQLite.
Se eligió sobrescribir todo en vez de un modelo de eventos por simplicidad; si el
equipo crece mucho y empiezan a pisarse guardados simultáneos, ahí conviene migrar
a un modelo append-only.
