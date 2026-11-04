"""Pruebas por variable y alarma de rendimiento con etiquetas disponibles."""
import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from scipy.stats import chi2_contingency, ks_2samp
from sklearn.metrics import f1_score

from src.datos import CONTINUAS, VARIABLES, dividir, generar

ALFA = 0.05 / len(VARIABLES)  # Bonferroni: cinco comparaciones, error familiar 5 %.
EFECTO_MINIMO = 0.10  # 10 puntos de diferencia en CDF o masa de categorías.
CAIDA_F1 = 0.10
LOTES_CONSECUTIVOS = 2


def revisar_datos(baseline, actual):
    resultados = []
    for nombre in VARIABLES:
        a, b = baseline[nombre], actual[nombre]
        if len(b) < 100 or b.isna().any() or not np.isfinite(b).all():
            raise ValueError(f"{nombre}: lote insuficiente o valores no finitos")
        if nombre in CONTINUAS:
            prueba = ks_2samp(a, b)
            p, efecto, metodo = float(prueba.pvalue), float(prueba.statistic), "KS"
        else:
            categorias = sorted(set(a) | set(b))
            tabla = np.array([[int((serie == c).sum()) for c in categorias] for serie in (a, b)])
            prueba = chi2_contingency(tabla, correction=False)
            if np.min(prueba.expected_freq) < 5:
                # Un plazo nuevo o categorías demasiado raras requieren revisión de esquema.
                p, efecto, metodo = 0.0, 1.0, "esquema/frecuencia insuficiente"
            else:
                p = float(prueba.pvalue)
                efecto = float(0.5 * np.abs(tabla[0] / tabla[0].sum() - tabla[1] / tabla[1].sum()).sum())
                metodo = "chi-cuadrado + distancia total de variacion"
        resultados.append({"variable": nombre, "prueba": metodo, "p_valor": p,
                            "efecto": efecto, "alerta": p < ALFA and efecto > EFECTO_MINIMO})
    return {"estado": "ROJO" if any(r["alerta"] for r in resultados) else "VERDE",
            "alfa_por_variable": ALFA, "efecto_minimo": EFECTO_MINIMO,
            "variables": resultados}


def alarma_rendimiento(valores, referencia):
    consecutivos = 0
    resultado = []
    for valor in valores:
        if valor is None:
            resultado.append({"f1": None, "estado": "PENDIENTE_ETIQUETAS", "alarma": False})
            continue
        consecutivos = consecutivos + 1 if referencia - valor > CAIDA_F1 else 0
        resultado.append({"f1": valor, "caida": referencia - valor,
                          "consecutivos": consecutivos,
                          "alarma": consecutivos >= LOTES_CONSECUTIVOS})
    return resultado


def simular(salida="salidas"):
    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    client = MlflowClient()
    version = client.get_model_version_by_alias("credito-riesgo", "produccion")
    modelo = mlflow.sklearn.load_model(f"models:/credito-riesgo/{version.version}")
    train, _, test = dividir(generar())
    normal = generar(1000, 2026)
    derivado = normal.copy()
    derivado.ingreso_mensual *= 2.5
    derivado.deuda_actual *= 3
    derivado.antiguedad_laboral = np.minimum(derivado.antiguedad_laboral + 12, 35)
    derivado.monto_solicitado *= 2
    derivado.plazo_meses = np.random.RandomState(7).choice([48, 60], len(derivado))
    normal.to_csv(out / "lote_normal.csv", index=False)
    derivado.to_csv(out / "lote_derivado.csv", index=False)
    train.to_csv(out / "baseline.csv", index=False)
    verde, rojo = revisar_datos(train, normal), revisar_datos(train, derivado)
    assert verde["estado"] == "VERDE" and rojo["estado"] == "ROJO"
    # Calibración independiente: mide falsas alarmas, no ajusta umbrales al lote rojo.
    falsas = sum(revisar_datos(train, generar(500, 5000 + i))["estado"] == "ROJO" for i in range(100))
    referencia = float(f1_score(test.moroso, modelo.predict(test[VARIABLES])))
    base_concepto = generar(1000, 901)
    pred = modelo.predict(base_concepto[VARIABLES])
    proporciones = [0, 0, 0, 0.10, 0.20, 0.35, 0.50, 0.65, 0.70, 0.70]
    valores, lotes = [], []
    for i, porcentaje in enumerate(proporciones, 1):
        y = base_concepto.moroso.to_numpy().copy()
        indices = np.random.RandomState(100 + i).permutation(len(y))[:int(len(y) * porcentaje)]
        y[indices] = 1 - y[indices]
        valores.append(float(f1_score(y, pred, zero_division=0)))
        lotes.append({"lote": i, "fraccion_etiquetas_invertidas": porcentaje,
                      "entradas_identicas": True})
    for lote, estado in zip(lotes, alarma_rendimiento(valores, referencia)):
        lote.update(estado)
    informe = {"modelo": "credito-riesgo", "version": version.version, "run_id": version.run_id,
               "normal": verde, "derivado": rojo,
               "calibracion": {"lotes": 100, "tamano_lote": 500, "falsas_alarmas": falsas,
                               "semillas": [5000, 5099]},
               "concepto": {"referencia_f1_test": referencia, "caida_minima": CAIDA_F1,
                            "lotes_exigidos": LOTES_CONSECUTIVOS, "lotes": lotes,
                            "data_drift_entradas": revisar_datos(train, base_concepto),
                            "tipo_simulacion": "contrafactual pareado: mismas 1000 entradas en cada lote"}}
    (out / "monitoreo.json").write_text(json.dumps(informe, indent=2), encoding="utf-8")
    plt.rcParams.update({"font.size": 12})
    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    xs = list(range(1, 11))
    ax.plot(xs, valores, "o-", color="#164e63", label="F1 con etiquetas del lote")
    ax.axhline(referencia, color="#64748b", linestyle=":", label="F1 de prueba de referencia")
    ax.axhline(referencia - CAIDA_F1, color="#b91c1c", linestyle="--", label="Referencia menos 0,10")
    alarmas = [r["lote"] for r in lotes if r["alarma"]]
    if alarmas:
        ax.axvspan(alarmas[0] - 0.15, 10.2, color="#fee2e2", zorder=0, label="Alarma sostenida")
    ax.set(xlabel="Lote simulado (orden temporal)", ylabel="F1 clase morosa", ylim=(0, 1), xticks=xs,
           title="Concept drift: cambian las etiquetas y las entradas se mantienen")
    ax.legend(loc="lower left", fontsize=9)
    fig.savefig(out / "concept_drift.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    x = np.arange(len(VARIABLES))
    ax.bar(x - .18, [r["efecto"] for r in verde["variables"]], .36, label="Mismo origen", color="#164e63")
    ax.bar(x + .18, [r["efecto"] for r in rojo["variables"]], .36, label="Deriva inyectada", color="#b91c1c")
    ax.axhline(EFECTO_MINIMO, color="#64748b", linestyle="--", label="Efecto mínimo 0,10")
    ax.set(xticks=x, xticklabels=["Ingreso", "Deuda", "Antigüedad", "Monto", "Plazo"],
           ylabel="Distancia KS / variación total (plazo)", ylim=(0, 1), title="Data drift por variable")
    ax.legend()
    fig.savefig(out / "data_drift.png", dpi=180)
    plt.close(fig)
    with mlflow.start_run(run_id=version.run_id):
        for nombre in ["monitoreo.json", "concept_drift.png", "data_drift.png"]:
            mlflow.log_artifact(str(out / nombre), "monitoreo")
    print(json.dumps(informe, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lote", help="CSV que debe pasar la puerta de data drift")
    parser.add_argument("--baseline", default="salidas/baseline.csv")
    parser.add_argument("--salida", default=os.getenv("SALIDA", "salidas"))
    args = parser.parse_args()
    if args.lote:
        resultado = revisar_datos(pd.read_csv(args.baseline), pd.read_csv(args.lote))
        print(json.dumps(resultado, indent=2))
        raise SystemExit(2 if resultado["estado"] == "ROJO" else 0)
    simular(args.salida)


if __name__ == "__main__":
    main()
