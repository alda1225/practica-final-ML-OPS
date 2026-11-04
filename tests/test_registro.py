import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.dummy import DummyClassifier


def test_registro_resuelve_alias_y_run(tmp_path):
    anterior = mlflow.get_tracking_uri()
    try:
        mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'prueba.db'}")
        mlflow.set_experiment("prueba-registro")
        x = pd.DataFrame({"entrada": [1.0, 2.0, 3.0, 4.0]})
        modelo = DummyClassifier(strategy="most_frequent").fit(x, [0, 0, 0, 1])
        with mlflow.start_run() as run:
            mlflow.sklearn.log_model(modelo, "modelo", input_example=x.head(1))
            run_id = run.info.run_id
        version = mlflow.register_model(f"runs:/{run_id}/modelo", "prueba-modelo")
        client = MlflowClient()
        client.set_registered_model_alias("prueba-modelo", "produccion", version.version)
        resuelto = client.get_model_version_by_alias("prueba-modelo", "produccion")
        assert resuelto.run_id == run_id
        cargado = mlflow.sklearn.load_model("models:/prueba-modelo@produccion")
        assert cargado.predict(x).tolist() == [0, 0, 0, 0]
    finally:
        mlflow.set_tracking_uri(anterior)
