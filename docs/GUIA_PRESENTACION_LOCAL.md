# Guía de presentación local de MLOps

Guía para las 15 diapositivas de Aldair Guzman. Preparar el equipo 15 minutos antes; reservar de 15 a 20 minutos para exponer.

## 1 Antes de comenzar

Guardar el trabajo abierto. Cerrar o minimizar aplicaciones ajenas al proyecto y activar No molestar en Windows.

Mantener Docker Desktop funcionando durante la defensa. Esperar a que Kubernetes esté listo y comprobar el laboratorio con estos comandos.

Abrir una ventana de PowerShell, llamada Terminal A en esta guía. Copiar:

```powershell
Set-Location 'D:\Alda\Documents\ChatGPT\14. MLOPS\practica-final-ML-OPS'
kubectl config current-context
kubectl get nodes
kubectl -n credito-mlops get deployments
Invoke-RestMethod http://localhost:30081/health
```

Se espera contexto docker-desktop, nodo Ready, credito-api 3/3 y mlflow 1/1. La salud debe indicar status ok, versión 2 y un nombre de Pod. Los nombres y edades de los Pods pueden cambiar.

Abrir entrega/Defensa_Proyecto_Final_MLOps.pptx en modo presentación. En videollamada, cambiar también la ventana compartida al pasar al navegador o la terminal.

Abrir un navegador con tres pestañas, en este orden:

1. MLflow: http://localhost:30500
2. Interfaz: http://localhost:30081
3. Swagger: http://localhost:30081/docs

Abrir una segunda PowerShell, Terminal B, en la misma carpeta para observar los Pods. No hace falta iniciar un servidor Python local.

No ejecutar Entrenar ni Limpiar: el laboratorio ya existe. Entrenar crea versiones nuevas; Limpiar borra también el registro de MLflow.

<!-- PAGINA -->

## 2 Inicio y experimentos en MLflow

Diapositivas 1 a 3. Mostrar únicamente PowerPoint. Explicar el objetivo, los datos sintéticos y el recorrido entrenamiento, registro, API y Kubernetes. Frase de apoyo: «La prioridad es demostrar que puedo identificar qué modelo está desplegado, mantener el servicio disponible y detectar degradación».

Diapositiva 4. Cambiar al navegador y abrir la pestaña MLflow.

1. Entrar en Experiments y abrir credito-experimentos.
2. Mostrar los cinco runs bosque-1 a bosque-5. Si hacen falta columnas, usar Columns para mostrar val_f1 y test_f1.
3. Ordenar val_f1 de mayor a menor, hasta que bosque-4 quede primero.
4. En la búsqueda de runs escribir el filtro siguiente y aplicarlo:

```text
metrics.val_f1 >= 0.70
```

5. Seleccionar bosque-4 y bosque-5 y abrir Compare. Mostrar sus hiperparámetros y F1 de validación. Después volver al experimento y quitar el filtro para recuperar los cinco runs.

Decir: «Se comparó el mismo algoritmo con la misma partición de datos. Elegí bosque-4 por F1 de validación: 0,7025 frente a 0,7009. La diferencia es pequeña; no demuestra una superioridad estadística. Test se reservó para la evaluación final».

Diapositiva 5. En MLflow entrar en Models y abrir credito-riesgo. Mostrar las versiones 1 y 2. Abrir la versión 2 y señalar el alias produccion. Seguir Source Run hasta el experimento bosque-4.

La traza de esta entrega es:

```text
Modelo: credito-riesgo
Referencia: models:/credito-riesgo@produccion
Versión: 2
Run: 1e80a5489e3d4a4c82e58d10baf530d6
```

Cambiar brevemente a la interfaz, pulsar Evaluar solicitud y comparar su versión y run con MLflow. Volver al PowerPoint. Dejar MLflow abierto para las preguntas.

<!-- PAGINA -->

## 3 Contenedor réplicas y escalamiento

Diapositiva 6. En Terminal A mostrar el tamaño de la imagen:

```powershell
docker images credito-mlops:1.3
```

Se espera la imagen propia credito-mlops:1.3, aproximadamente 942 MB. Explicar que incluye código y dependencias fijadas. Si preguntan por el empaquetado, abrir Dockerfile y requirements.lock.txt desde el repositorio. Cerrarlos o minimizarlos al terminar. docker ps no es la prueba de las réplicas de Kubernetes; para ellas se utiliza kubectl.

Diapositiva 7. En Terminal A ejecutar:

```powershell
kubectl get nodes
kubectl -n credito-mlops get pods -l app=credito-api
kubectl -n credito-mlops get service credito-api
```

Mostrar tres Pods Running y READY 1/1. El Service publica el puerto local 30081. En Docker Desktop entrar en Kubernetes y seleccionar el namespace credito-mlops; mostrar el Deployment credito-api disponible con 3/3. Es una alternativa visual a la terminal.

En Terminal B ejecutar el seguimiento continuo:

```powershell
kubectl -n credito-mlops get pods -l app=credito-api -w
```

En Terminal A escalar y esperar el resultado:

```powershell
./scripts/demo.ps1 -Etapa Escalar -Replicas 5
```

Esperar cinco Pods Ready y Deployment 5/5. Mostrarlo en Terminal A o actualizar la vista de Docker Desktop. Decir: «El Deployment mantiene la cantidad deseada de réplicas; el Service selecciona los Pods por su etiqueta».

Restablecer tres réplicas en Terminal A:

```powershell
./scripts/demo.ps1 -Etapa Escalar -Replicas 3
```

Esperar hasta que desaparezcan los Pods Terminating. En Terminal B pulsar Ctrl+C: detiene solamente el seguimiento, no los Pods. Volver al PowerPoint y conservar ambas terminales abiertas.

<!-- PAGINA -->

## 4 Balanceo y autorreparación

Diapositiva 8. Primero mostrar el reparto en el navegador. En la interfaz http://localhost:30081 pulsar Comprobar reparto. Se envían doce consultas al mismo Service. Mostrar doce respuestas HTTP 200 y más de un nombre de Pod. El reparto puede variar; si solo aparece uno, repetir y usar la auditoría siguiente para comprobar conexiones independientes.

En Terminal A ejecutar la auditoría de inferencias:

```powershell
python scripts/verificar_cluster.py balanceo
```

Se esperan 30 respuestas HTTP 200, al menos dos Pods, dos casos válidos HTTP 200 y un caso inválido HTTP 422. Python está instalado en este equipo; este auditor usa su biblioteca estándar. El modelo continúa ejecutándose dentro de Kubernetes.

Para demostrar la recuperación, iniciar otra vez el seguimiento en Terminal B:

```powershell
kubectl -n credito-mlops get pods -l app=credito-api -w
```

En Terminal A ejecutar:

```powershell
python scripts/verificar_cluster.py autorreparacion
```

El auditor envía inferencias mientras elimina un único Pod de credito-api. No elimina MLflow. Esperar a que termine; mostrar el nombre eliminado, un nombre nuevo y errores igual a 0. El número de solicitudes depende del tiempo de recuperación y no tiene que ser 52 como en la evidencia anterior.

Decir: «El Deployment reemplaza el Pod eliminado. Durante esta ventana de observación el resto atendió las solicitudes sin errores». No afirmar que esto protege frente a la caída de todo Docker Desktop.

En Terminal B pulsar Ctrl+C. En Terminal A comprobar:

```powershell
kubectl -n credito-mlops get pods -l app=credito-api
```

Deben quedar tres Pods Ready. Los nuevos resultados se guardan en salidas/balanceo.json y salidas/autorreparacion.json. Las evidencias entregadas en evidencias/registros conservan la ejecución anterior. Volver al PowerPoint.

<!-- PAGINA -->

## 5 Inferencia desde la interfaz y Swagger

Diapositiva 9. Cambiar a la pestaña de la interfaz. Para un ejemplo de bajo riesgo completar:

```text
Ingreso mensual: 5000
Deuda actual: 100
Antigüedad laboral: 15
Monto solicitado: 1000
Plazo: 48
```

Pulsar Evaluar solicitud. Mostrar la predicción de cumplimiento, la probabilidad y, debajo, Pod, versión y run. Explicar: «La página consume la API del Service de Kubernetes; no hay un proceso FastAPI ejecutándose directamente en Windows».

Si solicitan ver la API, cambiar a Swagger, abrir POST /predecir y pulsar Try it out. Reemplazar el JSON por este caso de alto riesgo y pulsar Execute:

```json
{
  "ingreso_mensual": 500,
  "deuda_actual": 12000,
  "antiguedad_laboral": 0,
  "monto_solicitado": 20000,
  "plazo_meses": 6
}
```

Mostrar HTTP 200, moroso igual a 1 y la traza del modelo. Para el caso inválido, cambiar solamente ingreso_mensual a -1 y ejecutar otra vez. Se espera HTTP 422: la validación rechaza la entrada. Restaurar el valor 500 al terminar.

La interfaz impide ciertos valores inválidos desde el formulario; por eso se usa Swagger para demostrar el rechazo de la API. En esta entrega las predicciones 0 y 1 son ejemplos comprobados, no promesas para cualquier conjunto de datos.

Volver al PowerPoint. Mantener abiertas las tres pestañas; no cerrar Docker Desktop ni detener los Deployments.

Si una demostración no se resuelve en un minuto, mostrar las evidencias de entrega/Proyecto_Final_MLOps_Consigna_Solucion_Evidencias.docx y aclarar qué parte no pudo repetirse en vivo.

<!-- PAGINA -->

## 6 Demostración de drift y cierre de la exposición

Diapositiva 10. En Terminal A ejecutar:

```powershell
./scripts/demo.ps1 -Etapa Monitorear
```

Esperar a que termine. El script genera los lotes y evalúa el modelo registrado; no entrena una versión nueva. Actualiza los resultados de salidas y los artefactos de monitoreo del run. En la salida mostrar el lote normal VERDE con código 0 y el lote derivado ROJO con código 2. El código 2 es la alarma esperada, no un fallo del montaje.

Explicar: «Se comparan las cinco entradas con el baseline de entrenamiento. Usamos KS para las cuatro numéricas y chi-cuadrado con variación total para el plazo discreto. Exigimos p menor que 0,01 y un efecto mayor que 0,10».

Diapositiva 11. Abrir la gráfica actual desde Terminal A:

```powershell
Invoke-Item .\salidas\concept_drift.png
```

Se abrirá en el visor de imágenes configurado en Windows. También puede verse en MLflow: abrir el run de producción, entrar en Artifacts, carpeta monitoreo, archivo concept_drift.png. Actualizar la página si se muestran resultados antiguos.

Señalar la curva F1 y la alarma desde el lote 6. Decir: «Las entradas son iguales entre lotes, pero cambiamos las etiquetas. El F1 cae más de 0,10 en dos lotes consecutivos. Esto demuestra cambio en la relación entre entrada y resultado». Los lotes son simulados; no son diez fechas reales de producción.

Cerrar el visor de imágenes y volver a PowerPoint. Diapositiva 12: explicar que sin etiquetas reales no puede calcularse un F1 fiable. Mientras llegan se vigilan las entradas, las predicciones y la salud del servicio; después se evalúa el desempeño.

Diapositiva 13: resumir lo que ya se mostró. No repetir todo el recorrido. Si el docente pide pruebas automatizadas, ejecutar este paso opcional en Terminal A:

```powershell
./scripts/demo.ps1 -Etapa Probar
```

Se esperan seis tests correctos y el reparto de consultas de salud. Diapositivas 14 y 15: reconocer datos sintéticos, un solo nodo y MLflow único; cerrar con los resultados y dejar las aplicaciones abiertas para las preguntas.

<!-- PAGINA -->

## 7 Qué cerrar al terminar y cómo resolver un problema

Salir del modo presentación y mantener MLflow y la interfaz disponibles durante las preguntas. Al terminar:

1. Si quedaron cinco réplicas, restablecer tres en Terminal A: ./scripts/demo.ps1 -Etapa Escalar -Replicas 3.
2. Detener el seguimiento con Ctrl+C y cerrar las terminales. Esto no apaga la API.
3. Cerrar navegador, visor de imágenes y PowerPoint; guardar los cambios que se desee conservar.
4. Para seguir practicando, dejar Docker Desktop funcionando. Para apagar el laboratorio, usar su opción de salida; localhost dejará de responder. No restablecer Kubernetes ni borrar volúmenes.

Solo para eliminar definitivamente los recursos del proyecto, ejecutar:

```powershell
./scripts/demo.ps1 -Etapa Limpiar
```

Elimina credito-mlops, su PVC y el registro de MLflow. No hace falta para cerrar la exposición. Después habría que preparar, entrenar y desplegar nuevamente.

### Si algo falla durante la defensa

Si localhost no responde, comprobar Docker Desktop y ejecutar:

```powershell
kubectl config current-context
kubectl -n credito-mlops get pods
kubectl -n credito-mlops get services
kubectl -n credito-mlops get events --sort-by=.metadata.creationTimestamp
```

Si el contexto es otro: kubectl config use-context docker-desktop. Para esperar el arranque: kubectl -n credito-mlops rollout status deployment/credito-api --timeout=240s. Para ver errores: kubectl -n credito-mlops logs deployment/credito-api --tail=40. No borrar ni reentrenar a ciegas.

Si PowerShell bloquea demo.ps1, abrir una sesión temporal con powershell -NoProfile -ExecutionPolicy Bypass, volver al repositorio y repetir. La política permanente no cambia.

