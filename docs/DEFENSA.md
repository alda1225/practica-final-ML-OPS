# Guion de defensa individual

Autor: Aldair. Duración sugerida: 12 a 15 minutos más preguntas.

## Recorrido de la presentación

1. Presentar el objetivo: servir un modelo reproducible, trazable y monitoreado.
2. Explicar los 3.000 datos artificiales, cinco variables y división 60/20/20.
3. Recorrer el flujo entrenamiento → MLflow → alias → API → Service → navegador.
4. Comparar los cinco experimentos por F1 de validación. El test no selecciona.
5. Mostrar las dos versiones y seguir `produccion` hasta el run de bosque-4.
6. Explicar Dockerfile, versiones bloqueadas y arranque sin Python en el host.
7. Mostrar los tres Pods y el Service. Distinguir réplica de nodo.
8. Comprobar balanceo, eliminar un Pod con tráfico y escalar a cinco y tres.
9. Evaluar una solicitud en la interfaz real de Kubernetes.
10. Mostrar la prueba de entradas: normal verde y deriva roja en cinco variables.
11. Mostrar la curva F1 con etiquetas cambiadas; alarma desde el lote 6.
12. Explicar qué puede observarse mientras no llegan las etiquetas reales.
13. Cerrar con los límites: datos sintéticos, un nodo, MLflow único y alarma manual.

## Preparar la defensa

Mantener Docker Desktop y Kubernetes encendidos. No ejecutar Limpiar. Antes de
presentar, comprobar:

```powershell
kubectl config current-context
kubectl get nodes
kubectl -n credito-mlops get pods
./scripts/demo.ps1 -Etapa Probar
```

Abrir http://localhost:30500 y http://localhost:30081. Si el navegador no llega,
revisar Pods, Services y eventos con kubectl antes de repetir el entrenamiento.
No reentrenar durante la defensa sin necesidad: generaría otros IDs y versiones.

## MLflow en vivo

Entrar en Experiments → credito-experimentos. Cada run es un conjunto distinto de
hiperparámetros del mismo algoritmo, datos y partición. En Columns mostrar
`val_f1` y `test_f1`; ordenar `val_f1` de mayor a menor. Aplicar el filtro
`metrics.val_f1 >= 0.70`, seleccionar ambos candidatos y pulsar Compare.

Explicar que bosque-4 tiene F1 0,7025 y bosque-5 tiene 0,7009. La diferencia es
pequeña; el criterio se fijó antes de mirar prueba. Mostrar profundidad 6 frente
a 10 y 150 frente a 200 árboles. No defender una mejora estadísticamente probada.

Ir a Models → credito-riesgo. Hay versiones 1 y 2. La versión 2 tiene alias
`produccion`; Source Run lleva a bosque-4. El run completo es
`1e80a5489e3d4a4c82e58d10baf530d6`. Abrir la interfaz y comprobar el mismo run
en la respuesta. En Artifacts están modelo, división de datos, baseline,
selección, monitoreo y evidencias verificadas.

## Kubernetes en vivo

El botón de reparto hace doce solicitudes al Service. Su resumen puede variar:
el balanceo no garantiza un reparto exactamente igual. Mostrar al menos dos
Pods diferentes y las doce respuestas HTTP 200.

Para eliminar un Pod mientras se envían inferencias, usar el auditor:

```powershell
python scripts/verificar_cluster.py autorreparacion
./scripts/demo.ps1 -Etapa Escalar -Replicas 5
./scripts/demo.ps1 -Etapa Escalar -Replicas 3
```

Alternativa sin Python en el host: abrir dos terminales manualmente. En una
mantener consultas al Service y, en la otra, ejecutar `kubectl delete pod` sobre
un Pod de `credito-mlops`, seguido de `kubectl get pods -w`. No borrar MLflow.
El Deployment conserva tres réplicas deseadas y crea el reemplazo.

## Drift en vivo

```powershell
./scripts/demo.ps1 -Etapa Monitorear
```

La puerta verde debe retornar 0 y la roja 2. El script comprueba esos códigos.
Los tests de pytest deben quedar verdes porque esperan correctamente el caso
derivado. Abrir `monitoreo/concept_drift.png` en los artefactos del run.
Se mantuvieron iguales las entradas y se invirtieron etiquetas; el detector de
data drift sigue verde mientras F1 cae. Señalar los lotes 5 y 6: dos caídas
consecutivas superiores a diez puntos disparan la alarma.

## Preguntas y respuestas para practicar

**¿Por qué no elegir solo por accuracy?** Hay 28,47 % de morosos. Acertar la clase
mayoritaria no basta; F1 resume precision y recall de la clase relevante.

**¿Hay fuga entre entrenamiento y prueba?** Las particiones son estratificadas,
fijas y disjuntas. Los cinco candidatos se comparan en validación. Solo se evalúa
el ganador en test; los lotes de monitoreo usan semillas nuevas.

**¿Qué hace reproducible el entrenamiento?** La semilla, los índices de división,
el hash del dataset, los hiperparámetros, versiones de dependencias, imagen base
fijada y commit registrado. Los IDs de MLflow y nombres de Pods no son deterministas.

**¿El modelo está guardado con pickle a mano?** No. Se registra con
`mlflow.sklearn.log_model`; MLflow administra su formato y registro. La API resuelve
`models:/credito-riesgo@produccion`, no una ruta local a un archivo suelto.

**¿Qué diferencia hay entre imagen y versión del modelo?** La imagen versiona
código y dependencias. La versión del Model Registry identifica el modelo y su run.
Las respuestas indican la versión efectivamente cargada por cada réplica.

**¿Qué pasa si cambio el alias?** Las réplicas existentes conservan su modelo.
Hay que hacer un rollout para cargar la nueva versión; después verificar todos
los Pods y sus respuestas. Para revertir, mover el alias a una versión validada
y reiniciar gradualmente. No cambiarlo en esta defensa si no se pide.

**¿Por qué NodePort y no port-forward?** El NodePort pasa por el Service y reparte
conexiones a los endpoints Ready. Un port-forward hacia un Pod no demuestra
balanceo del Service. Reutilizar una conexión puede enviar varias consultas al
mismo Pod; por eso se observan conexiones independientes.

**¿Tres Pods dan alta disponibilidad completa?** Dan redundancia de aplicación
ante la pérdida de un Pod. El nodo local y MLflow siguen siendo puntos únicos
de fallo. Se comprobó una ventana concreta sin errores, no disponibilidad infinita.

**¿Por qué KS para unas entradas y chi-cuadrado para plazo?** KS compara las
distribuciones numéricas sin exigir normalidad. El plazo tiene categorías
discretas; chi-cuadrado compara sus frecuencias. La variación total mide cuánto
cambió esa distribución. Se comprueba el tamaño de muestra y frecuencia esperada.

**¿De dónde vienen 0,01 y 0,10?** 0,01 es 0,05 dividido entre cinco comparaciones.
0,10 exige un cambio de distribución con magnitud práctica para el laboratorio.
Se midieron cien controles sin deriva con cero falsas alarmas observadas. No
significa que esos valores sean adecuados para cualquier sistema real.

**¿Data drift obliga a reentrenar?** No necesariamente. Puede cambiar P(X) y
mantenerse la calidad. Hay que investigar el origen y esperar etiquetas para
evaluar desempeño, además de revisar calidad y cobertura.

**¿Cómo puede haber concept drift sin data drift?** Cambia P(y|X) aunque X sea
igual. En la simulación se conservan las mismas solicitudes y cambian etiquetas;
la curva F1 cae sin que se detecte una distribución de entradas distinta.

**¿Qué hacemos si no llegan etiquetas?** Declarar la métrica pendiente, vigilar
entradas, predicciones y salud técnica, y después unir resultados con su ID de
predicción. No asumir que ausencia de data drift garantiza buen desempeño.

**¿Por qué no reentrenar automáticamente al primer rojo?** Un lote puede tener
ruido, mala calidad o etiquetas incompletas. Se exige persistencia de la pérdida
y revisión del candidato antes de promover otra versión. La práctica implementa
la alarma; no afirma una integración real con una cartera ni sustitución automática.

**¿Qué aportan CI y los seis tests?** Se comprueban datos reproducibles y división,
contrato y validaciones de la API, drift por variable, persistencia de alarmas,
calidad del lote y carga de un alias real en un registro temporal MLflow.
La auditoría de Kubernetes es una verificación adicional contra el servicio vivo.
