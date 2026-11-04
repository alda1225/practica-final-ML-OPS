"""Cinco experimentos comparables y promoción explícita mediante MLflow."""
import json
import os
from pathlib import Path

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from src.datos import SEMILLA, VARIABLES, dividir, generar, huella

NOMBRE_MODELO = "credito-riesgo"
EXPERIMENTO = "credito-experimentos"
CONFIGURACIONES = [
    dict(n_estimators=80, max_depth=4, min_samples_leaf=5, class_weight=None),
    dict(n_estimators=120, max_depth=6, min_samples_leaf=3, class_weight=None),
    dict(n_estimators=150, max_depth=10, min_samples_leaf=1, class_weight=None),
    dict(n_estimators=150, max_depth=6, min_samples_leaf=3, class_weight="balanced"),
    dict(n_estimators=200, max_depth=10, min_samples_leaf=2, class_weight="balanced"),
]


def metricas(y, pred):
    return {"f1": float(f1_score(y, pred, zero_division=0)),
            "accuracy": float(accuracy_score(y, pred)),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0))}


def entrenar(salida="salidas"):
    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment(EXPERIMENTO)
    client = MlflowClient()
    datos = generar()
    train, val, test = dividir(datos)
    resultados = []
    for i, params in enumerate(CONFIGURACIONES, 1):
        with mlflow.start_run(run_name=f"bosque-{i}") as run:
            modelo = RandomForestClassifier(**params, random_state=SEMILLA, n_jobs=1)
            modelo.fit(train[VARIABLES], train.moroso)
            scores = metricas(val.moroso, modelo.predict(val[VARIABLES]))
            mlflow.log_params({**params, "semilla": SEMILLA, "n_train": len(train),
                               "n_validacion": len(val), "n_prueba": len(test),
                               "umbral_clasificacion": 0.5})
            mlflow.log_metrics({f"val_{k}": v for k, v in scores.items()})
            mlflow.set_tags({"git_commit": os.getenv("GIT_COMMIT", "sin-especificar"),
                             "dataset_sha256": huella(datos), "origen": "sintetico-clase",
                             "seleccion": "F1 validacion; desempate menor numero de arboles"})
            mlflow.log_input(mlflow.data.from_pandas(train, source="generador-semilla-42",
                                                   targets="moroso", name="credito-train"),
                             context="training")
            mlflow.log_dict({"semilla": SEMILLA, "proporcion": [0.6, 0.2, 0.2],
                             "train_indices": train.index.tolist(),
                             "validacion_indices": val.index.tolist(),
                             "prueba_indices": test.index.tolist(),
                             "sha256": huella(datos)}, "datos/division.json")
            mlflow.log_table(train.reset_index(drop=True), "datos/baseline.json")
            firma = infer_signature(train[VARIABLES], modelo.predict(train[VARIABLES]))
            mlflow.sklearn.log_model(modelo, "modelo", signature=firma,
                                     input_example=train[VARIABLES].head(2))
            resultados.append({"nombre": f"bosque-{i}", "run_id": run.info.run_id,
                                "parametros": params, **{f"val_{k}": v for k, v in scores.items()}})
            print(json.dumps(resultados[-1]), flush=True)
    ordenados = sorted(resultados, key=lambda r: (-r["val_f1"], r["parametros"]["n_estimators"]))
    ganador = ordenados[0]
    # Se registran dos candidatos reales, cada uno vinculado con su run.
    versiones = []
    for candidato in (ordenados[1], ganador):
        version = mlflow.register_model(f"runs:/{candidato['run_id']}/modelo", NOMBRE_MODELO)
        versiones.append({"version": version.version, "run_id": candidato["run_id"]})
    version = versiones[-1]["version"]
    client.set_registered_model_alias(NOMBRE_MODELO, "produccion", version)
    client.set_model_version_tag(NOMBRE_MODELO, version, "criterio", "mayor val_f1")
    modelo = mlflow.sklearn.load_model(f"models:/{NOMBRE_MODELO}@produccion")
    prueba = metricas(test.moroso, modelo.predict(test[VARIABLES]))
    with mlflow.start_run(run_id=ganador["run_id"]):
        mlflow.log_metrics({f"test_{k}": v for k, v in prueba.items()})
        informe = {"modelo": NOMBRE_MODELO, "alias": "produccion", "version": version,
                   "run_id": ganador["run_id"], "modelo_uri": f"models:/{NOMBRE_MODELO}@produccion",
                   "resultados": resultados, "versiones": versiones,
                   "test": prueba, "dataset_sha256": huella(datos),
                   "n_registros": len(datos), "positivos": int(datos.moroso.sum()),
                   "git_commit": os.getenv("GIT_COMMIT", "sin-especificar")}
        mlflow.log_dict(informe, "seleccion.json")
    (out / "experimentos.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
    print(json.dumps({"seleccion": informe}, indent=2), flush=True)


if __name__ == "__main__":
    entrenar(os.getenv("SALIDA", "salidas"))
