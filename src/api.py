"""Servicio que resuelve el alias del registro al arrancar cada réplica."""
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from typing import Literal

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from mlflow.tracking import MlflowClient
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, ConfigDict, Field

from src.datos import VARIABLES

PETICIONES = Counter("credito_http_requests_total", "Respuestas HTTP", ["ruta", "metodo", "estado"])
LATENCIA = Histogram("credito_http_duration_seconds", "Latencia HTTP", ["ruta"])
logger = logging.getLogger("uvicorn.error")


class Solicitante(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    ingreso_mensual: float = Field(gt=0, le=1_000_000)
    deuda_actual: float = Field(ge=0, le=10_000_000)
    antiguedad_laboral: float = Field(ge=0, le=60)
    monto_solicitado: float = Field(gt=0, le=10_000_000)
    plazo_meses: Literal[6, 12, 18, 24, 36, 48, 60]


def cargar_modelo():
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    uri = os.getenv("MODEL_URI", "models:/credito-riesgo@produccion")
    nombre, alias = uri.removeprefix("models:/").split("@", 1)
    version = MlflowClient().get_model_version_by_alias(nombre, alias)
    # Se fija la versión resuelta para evitar una carrera si el alias cambia.
    modelo = mlflow.sklearn.load_model(f"models:/{nombre}/{version.version}")
    return modelo, {"modelo_uri": uri, "version_modelo": version.version,
                    "run_id": version.run_id, "pod": os.getenv("HOSTNAME", "local")}


@asynccontextmanager
async def lifespan(app):
    app.state.modelo, app.state.traza = cargar_modelo()
    logger.info(json.dumps({"evento": "modelo_cargado", **app.state.traza}))
    yield


app = FastAPI(title="Riesgo crediticio MLOps", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def observar(request: Request, call_next):
    inicio = perf_counter()
    estado = 500
    try:
        respuesta = await call_next(request)
        estado = respuesta.status_code
        return respuesta
    finally:
        ruta = getattr(request.scope.get("route"), "path", "desconocida")
        duracion = perf_counter() - inicio
        if ruta not in ("/metrics", "/health", "/ready"):
            PETICIONES.labels(ruta, request.method, str(estado)).inc()
            LATENCIA.labels(ruta).observe(duracion)
            logger.info(json.dumps({"evento": "http", "ruta": ruta, "estado": estado,
                                    "duracion_ms": round(duracion * 1000, 2),
                                    **getattr(app.state, "traza", {})}))


@app.get("/health")
def health():
    return {"status": "ok", **app.state.traza}


@app.get("/ready")
def ready():
    return {"ready": app.state.modelo is not None, **app.state.traza}


@app.post("/predecir")
def predecir(solicitante: Solicitante):
    fila = pd.DataFrame([solicitante.model_dump()], columns=VARIABLES)
    prediccion = int(app.state.modelo.predict(fila)[0])
    probabilidad = float(app.state.modelo.predict_proba(fila)[0][1])
    return {"moroso": prediccion, "probabilidad": probabilidad, **app.state.traza}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
def interfaz():
    return FileResponse(Path(__file__).with_name("interfaz.html"))
