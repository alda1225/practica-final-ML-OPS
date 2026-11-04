# Riesgo crediticio con MLOps

Proyecto final individual. Clasificación de solicitudes de crédito con cinco
variables, experimentos y registro en MLflow, API en Kubernetes y pruebas de drift.

El punto de partida es el generador sintético de `proyecto-base 2.zip`, entregado
en clase. Los ejemplos `drift.zip` y `heladeria-ci-cd-ct.zip` se consultaron como
referencia de monitoreo. La implementación de este repositorio adapta ese material
a la consigna final; no utiliza el archivo joblib preentrenado del ejemplo.

## Datos y reproducibilidad

Se generan 3.000 solicitudes con semilla 42. Las variables son ingreso mensual,
deuda actual, antigüedad laboral, monto solicitado y plazo en meses. El objetivo es
`moroso` (1: incumplimiento simulado; 0: cumplimiento). Son datos artificiales:
sirven para demostrar ingeniería y cambios controlados, no para aprobar créditos.

La división estratificada es 60 % entrenamiento, 20 % validación y 20 % prueba.
Se seleccionan hiperparámetros por F1 de la clase morosa en validación. La prueba
permanece reservada hasta la evaluación final. El conjunto de entrenamiento es
el baseline de distribución. Los lotes de monitoreo usan semillas independientes.

## Desarrollo

Los commits agrupan avances concretos: datos, experimentos, servicio, despliegue,
monitoreo y documentación. Se conserva el autor configurado en Git y las fechas
reales de ejecución.

## Ejecutar en Docker Desktop

Requisitos: Docker Desktop iniciado con Kubernetes habilitado, `docker`, `kubectl`,
Git y PowerShell. El contexto debe ser `docker-desktop`. No hace falta instalar
Python ni dependencias de ML en el anfitrión para entrenar o servir el modelo.
El auditor opcional `verificar_cluster.py` utiliza Python y su biblioteca estándar.

```powershell
git clone https://github.com/alda1225/practica-final-ML-OPS.git
cd practica-final-ML-OPS
./scripts/demo.ps1 -Etapa Preparar
./scripts/demo.ps1 -Etapa Entrenar
./scripts/demo.ps1 -Etapa Desplegar
./scripts/demo.ps1 -Etapa Monitorear
./scripts/demo.ps1 -Etapa Probar
```

Abrir la interfaz en http://localhost:30081, Swagger en http://localhost:30081/docs
y MLflow en http://localhost:30500. Se usa el Service de Kubernetes directamente;
no hay un proceso FastAPI local ni un port-forward hacia una sola réplica.
La imagen local `credito-mlops:1.3` tiene `imagePullPolicy: Never`, apropiado para
el almacén de imágenes compartido de Docker Desktop. En otro clúster se debe
publicar/importar la imagen y adaptar los manifiestos.

`Entrenar` crea cinco runs y dos versiones nuevas en cada ejecución. El alias se
actualiza al ganador de esa ejecución. Si la API ya estaba desplegada, reiniciar
sus Pods para cargar el nuevo alias:

```powershell
kubectl -n credito-mlops rollout restart deployment/credito-api
kubectl -n credito-mlops rollout status deployment/credito-api
```

## Demostración de Kubernetes

```powershell
kubectl get nodes
kubectl -n credito-mlops get pods -l app=credito-api
./scripts/demo.ps1 -Etapa Escalar -Replicas 5
./scripts/demo.ps1 -Etapa Escalar -Replicas 3
python scripts/verificar_cluster.py balanceo
python scripts/verificar_cluster.py autorreparacion
```

El auditor registra cada respuesta real, comprueba los EndpointSlices y verifica
que el run y la versión coinciden con `salidas/experimentos.json`. La reparación
elimina un único Pod del namespace del proyecto mientras envía inferencias;
falla si observa un error de conexión o HTTP. El botón «Comprobar reparto» permite
mostrar desde el navegador doce consultas al Service y los Pods que respondieron.

## Resultados verificados

- Cinco runs comparables; dos versiones del modelo `credito-riesgo`.
- Alias `produccion`: versión 2, run `1e80a5489e3d4a4c82e58d10baf530d6`.
- Ganador: bosque-4, F1 de validación 0,7025 y de prueba 0,6756.
- Tres réplicas Running; 30 inferencias HTTP 200, repartidas 8/9/13.
- Eliminación y reposición de un Pod; 52 inferencias observadas sin errores.
- Escalamiento 3 → 5 → 3, con cinco réplicas disponibles durante la prueba.
- Data drift: lote normal VERDE (salida 0), deriva inyectada ROJO (salida 2).
- Concept drift: alarma desde el lote 6, caída F1 > 0,10 en dos lotes seguidos.
- Seis pruebas automatizadas; ejecución local y GitHub Actions verificadas.

Estos son resultados de la ejecución entregada. Al repetirla cambian los run IDs,
las versiones y los nombres de Pods; se deben consultar los archivos recién
generados. Los registros entregados permanecen en `evidencias/registros`.

## Documentación y defensa

- [Consigna original](docs/CONSIGNA_ORIGINAL.md).
- [Decisiones y reparto individual](docs/ARQUITECTURA.md).
- [Guion de defensa y preguntas](docs/DEFENSA.md).
- Capturas auténticas en `evidencias/capturas`; salidas TXT/JSON en
  `evidencias/registros`. Los artefactos también están asociados al run en MLflow.
- [Informe Word con consigna, solución y evidencias](entrega/Proyecto_Final_MLOps_Consigna_Solucion_Evidencias.docx).
- [PowerPoint de defensa con notas del expositor](entrega/Defensa_Proyecto_Final_MLOps.pptx).

El laboratorio queda operativo para la defensa. Tres réplicas en un nodo no
garantizan continuidad si se apaga Docker Desktop. MLflow usa SQLite y un PVC
local; una operación real requiere infraestructura y controles adicionales.

## Finalizar

Después de la defensa, este comando elimina todos los recursos del namespace,
incluido el PVC con el registro y los artefactos de MLflow:

```powershell
./scripts/demo.ps1 -Etapa Limpiar
```

No ejecutarlo antes de mostrar MLflow en vivo.
