"""Auditoría real del Service. Solo usa la biblioteca estándar de Python."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

NS = "credito-mlops"
BASE = "http://localhost:30081"
SALIDA = Path(__file__).resolve().parents[1] / "salidas"
BAJO = dict(ingreso_mensual=5000, deuda_actual=100, antiguedad_laboral=15,
            monto_solicitado=1000, plazo_meses=48)
ALTO = dict(ingreso_mensual=500, deuda_actual=12000, antiguedad_laboral=0,
            monto_solicitado=20000, plazo_meses=6)


def kubectl(*args, json_salida=False):
    comando = ["kubectl", "--context", "docker-desktop", "-n", NS, *args]
    r = subprocess.run(comando, capture_output=True, text=True, check=True)
    return json.loads(r.stdout) if json_salida else r.stdout


def peticion(datos=BAJO):
    inicio = time.perf_counter()
    request = Request(BASE + "/predecir", data=json.dumps(datos).encode(),
                      headers={"Content-Type": "application/json", "Connection": "close"})
    try:
        with urlopen(request, timeout=5) as response:
            codigo, cuerpo = response.status, json.load(response)
    except HTTPError as error:
        codigo, cuerpo = error.code, json.load(error)
    except Exception as error:
        codigo, cuerpo = 0, {"error": str(error)}
    return {"hora_utc": datetime.now(timezone.utc).isoformat(), "http": codigo,
            "latencia_ms": round((time.perf_counter() - inicio) * 1000, 2), "respuesta": cuerpo}


def guardar(nombre, datos):
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / nombre).write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")


def balanceo():
    pods = kubectl("get", "pods", "-l", "app=credito-api", "-o", "json", json_salida=True)
    activos = [p for p in pods["items"] if not p["metadata"].get("deletionTimestamp")]
    assert len(activos) >= 3
    assert all(p["status"]["phase"] == "Running" and
               all(c["ready"] for c in p["status"]["containerStatuses"]) for p in activos)
    respuestas = [peticion() for _ in range(30)]
    assert all(r["http"] == 200 for r in respuestas)
    reparto = Counter(r["respuesta"]["pod"] for r in respuestas)
    assert len(reparto) >= 2, "El Service no demostro reparto entre pods"
    esperados = {p["metadata"]["name"] for p in activos}
    assert set(reparto) <= esperados
    endpoints = kubectl("get", "endpointslices", "-l", "kubernetes.io/service-name=credito-api",
                        "-o", "json", json_salida=True)
    ips = {ip for s in endpoints["items"] for e in s["endpoints"]
           if e.get("conditions", {}).get("ready") for ip in e["addresses"]}
    assert ips == {p["status"]["podIP"] for p in activos}
    pruebas = {"bajo_riesgo": peticion(BAJO), "alto_riesgo": peticion(ALTO),
               "invalido": peticion({**BAJO, "ingreso_mensual": -1})}
    assert [r["http"] for r in pruebas.values()] == [200, 200, 422]
    assert pruebas["bajo_riesgo"]["respuesta"]["moroso"] == 0
    assert pruebas["alto_riesgo"]["respuesta"]["moroso"] == 1
    traza = json.loads((SALIDA / "experimentos.json").read_text(encoding="utf-8"))
    assert all(r["respuesta"]["run_id"] == traza["run_id"] and
               r["respuesta"]["version_modelo"] == traza["version"] for r in respuestas)
    guardar("balanceo.json", {"pods": [p["metadata"]["name"] for p in activos],
                              "reparto": dict(reparto), "peticiones": respuestas,
                              "endpoints": sorted(ips), "pruebas_api": pruebas})
    print(json.dumps({"reparto": dict(reparto), "total_http_200": len(respuestas),
                      "pruebas": {k: v["http"] for k, v in pruebas.items()}}, indent=2))


def reparar():
    antes = kubectl("get", "pods", "-l", "app=credito-api", "-o", "json", json_salida=True)["items"]
    objetivo = antes[0]["metadata"]["name"]
    respuestas = []
    detener = threading.Event()

    def trafico():
        while not detener.is_set():
            respuestas.append(peticion())
            detener.wait(0.15)

    hilo = threading.Thread(target=trafico)
    hilo.start()
    try:
        time.sleep(1)
        eliminado = kubectl("delete", "pod", objetivo, "--wait=true", "--timeout=90s")
        rollout = kubectl("rollout", "status", "deployment/credito-api", "--timeout=240s")
        time.sleep(2)
    finally:
        detener.set()
        hilo.join()
    despues = kubectl("get", "pods", "-l", "app=credito-api", "-o", "json", json_salida=True)["items"]
    previos = {p["metadata"]["uid"] for p in antes}
    nuevos = [p["metadata"]["name"] for p in despues if p["metadata"]["uid"] not in previos]
    informe = {"eliminado": objetivo, "nuevos": nuevos, "total": len(respuestas),
               "errores": sum(r["http"] != 200 for r in respuestas), "peticiones": respuestas,
               "delete": eliminado, "rollout": rollout,
               "antes": [p["metadata"]["name"] for p in antes],
               "despues": [p["metadata"]["name"] for p in despues]}
    guardar("autorreparacion.json", informe)
    assert nuevos and objetivo not in informe["despues"]
    assert len(despues) == len(antes)
    assert informe["errores"] == 0, "Hubo errores durante la ventana observada; revisar el registro"
    print(json.dumps({k: v for k, v in informe.items() if k != "peticiones"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("etapa", choices=["balanceo", "autorreparacion"])
    args = parser.parse_args()
    balanceo() if args.etapa == "balanceo" else reparar()
