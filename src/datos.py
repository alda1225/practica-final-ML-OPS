"""Generador del ejemplo de crédito, separado para reutilizarlo en monitoreo."""
import hashlib

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

SEMILLA = 42
VARIABLES = ["ingreso_mensual", "deuda_actual", "antiguedad_laboral",
             "monto_solicitado", "plazo_meses"]
CONTINUAS = VARIABLES[:-1]
PLAZOS = [6, 12, 18, 24, 36, 48, 60]


def generar(n=3000, semilla=SEMILLA):
    # RandomState conserva la secuencia del material original de la clase.
    rng = np.random.RandomState(semilla)
    ingreso = rng.gamma(4.0, 400.0, n) + 300
    deuda = rng.gamma(2.0, 900.0, n)
    antiguedad = rng.exponential(5.0, n).clip(0, 35)
    monto = rng.gamma(2.5, 2200.0, n) + 500
    plazo = rng.choice(PLAZOS, n)
    carga = (deuda * 0.04 + monto / plazo) / ingreso
    score = 2.2 * carga - 0.06 * antiguedad + rng.normal(0, 0.35, n)
    frame = pd.DataFrame(dict(zip(VARIABLES, [ingreso, deuda, antiguedad, monto, plazo])))
    frame["moroso"] = (score > 0.55).astype(int)
    return frame


def dividir(frame):
    train, resto = train_test_split(frame, test_size=0.4, random_state=SEMILLA,
                                   stratify=frame.moroso)
    validacion, prueba = train_test_split(resto, test_size=0.5, random_state=SEMILLA,
                                        stratify=resto.moroso)
    return train, validacion, prueba


def huella(frame):
    return hashlib.sha256(frame.to_csv(index=False, float_format="%.12g").encode()).hexdigest()
