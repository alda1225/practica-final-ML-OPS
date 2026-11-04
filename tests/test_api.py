from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient
from src.api import app


class ModeloPrueba:
    def predict(self, datos):
        return np.array([0])

    def predict_proba(self, datos):
        return np.array([[0.9, 0.1]])


FILA = dict(ingreso_mensual=2500, deuda_actual=500, antiguedad_laboral=8,
            monto_solicitado=3000, plazo_meses=24)


def test_api_valida_y_devuelve_trazabilidad():
    traza = dict(pod="pod-prueba", version_modelo="2", run_id="run-prueba")
    with patch("src.api.cargar_modelo", return_value=(ModeloPrueba(), traza)):
        with TestClient(app) as client:
            assert client.get("/ready").json()["ready"]
            respuesta = client.post("/predecir", json=FILA)
            assert respuesta.status_code == 200
            assert respuesta.json() == dict(moroso=0, probabilidad=0.1, **traza)
            for campo, valor in [("ingreso_mensual", -1), ("plazo_meses", 7),
                                  ("deuda_actual", -10), ("monto_solicitado", "invalido")]:
                assert client.post("/predecir", json={**FILA, campo: valor}).status_code == 422
            assert client.post("/predecir", json={**FILA, "otro": 1}).status_code == 422
            assert "credito_http_requests_total" in client.get("/metrics").text
