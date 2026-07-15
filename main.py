"""
Backend de Aseguramiento de la Calidad - Agentes (DARS / Salud Responde)

Guarda el estado compartido del dashboard (entries + rosterChanges) en SQLite,
en un archivo propio (calidad_agentes.db) separado de cualquier otro backend
que ya corra en el mismo servidor. No comparte tablas ni rutas con otros
proyectos.

Endpoints:
  GET  /api/calidad-agentes/state   -> {entries: [...], rosterChanges: {...}}
      Lectura libre (el dashboard necesita cargar sin pedir clave).
  POST /api/calidad-agentes/state   -> requiere header X-Api-Key
      Sobrescribe el estado completo con lo que envía el cliente.
      (El cliente ya mantiene el arreglo completo en memoria y lo reenvía
      entero en cada guardado - mismo modelo que ya usaba localStorage.)

Nota de diseño: se eligió "sobrescribir todo" en vez de un modelo de eventos
append-only por simplicidad. Con el volumen y la cantidad de gente que usa
este dashboard, el riesgo de que dos personas guarden exactamente al mismo
segundo y se pisen es bajo. Si en el futuro se vuelve un problema, conviene
migrar a un modelo de eventos (POST /entries agrega, no reemplaza).
"""

import os
import sqlite3
import json
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "calidad_agentes.db")
API_KEY = os.environ.get("CALIDAD_AGENTES_API_KEY", "CAMBIA_ESTA_CLAVE")

app = FastAPI(title="Calidad Agentes DARS - Backend")

# Ajustar en producción si el HTML se sirve desde otro origen/puerto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state_blob (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                entries_json TEXT NOT NULL DEFAULT '[]',
                roster_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO state_blob (id, entries_json, roster_json)
            VALUES (1, '[]', '{}')
        """)
        conn.commit()


@app.on_event("startup")
def on_startup():
    init_db()


class StatePayload(BaseModel):
    entries: List[Dict[str, Any]] = []
    rosterChanges: Dict[str, Any] = {}


@app.get("/api/calidad-agentes/state")
def get_state():
    with get_db() as conn:
        row = conn.execute(
            "SELECT entries_json, roster_json FROM state_blob WHERE id = 1"
        ).fetchone()
    if not row:
        return {"entries": [], "rosterChanges": {}}
    entries_json, roster_json = row
    return {
        "entries": json.loads(entries_json),
        "rosterChanges": json.loads(roster_json),
    }


@app.post("/api/calidad-agentes/state")
def save_state(payload: StatePayload, x_api_key: Optional[str] = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Clave inválida")
    with get_db() as conn:
        conn.execute(
            """
            UPDATE state_blob
            SET entries_json = ?, roster_json = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (json.dumps(payload.entries), json.dumps(payload.rosterChanges)),
        )
        conn.commit()
    return {"ok": True}
