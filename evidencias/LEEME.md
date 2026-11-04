# Evidencias de la ejecución

Las capturas JPG son imágenes auténticas del navegador: MLflow, la interfaz de
inferencia, Swagger y GitHub Actions. No muestran el puntero de Codex. Los PNG
en `capturas/recortes` solo extraen áreas de esas mismas imágenes para mejorar
su lectura en el informe; no se reconstruyeron ni alteraron los resultados.

`capturas/nativas` contiene dos capturas directas de Docker Desktop: tres y
cinco réplicas disponibles, junto al nodo Ready. El puntero se ubicó en el margen
izquierdo, fuera del área capturada. `17_deployment_detalle.png` es un recorte
de la captura de tres réplicas para la presentación. El registro de esta
verificación está en `registros/capturas_nativas_cluster.txt`; al finalizar
se restablecieron tres réplicas. La tarjeta de Pods tiene una altura limitada:
la disponibilidad de cinco réplicas se comprueba en el contador 5/5 del Deployment
y en la salida completa de kubectl del registro.

Las salidas de Kubernetes y Docker se guardaron después de ejecutar los comandos
reales. Se asociaron al run de MLflow como artefactos y se capturó su visor web.
Estas imágenes muestran los registros de una prueba realizada; el archivo de
cinco réplicas no pretende representar el estado final, que quedó en tres.

`registros/balanceo.json` contiene las 30 respuestas de inferencia, los tres
casos de API y los EndpointSlices comprobados. `autorreparacion.json` conserva
las 52 solicitudes muestreadas durante la eliminación y sustitución de un Pod,
con sus tiempos, respuestas y latencias. Los archivos con sufijo `inicial`
corresponden a una ejecución anterior también real, previa a la imagen 1.3.

`balanceo_reparacion.txt` y `drift_resumen.txt` resumen los resultados de esos
JSON para consultarlos en el visor de MLflow. Las puertas individuales
`puerta_verde.txt` y `puerta_roja.txt` son la salida de las comprobaciones de
drift, con códigos 0 y 2 guardados en `codigos_drift.json`.

Los PNG `data_drift.png` y `concept_drift.png` de `registros` son gráficas
calculadas por el monitor, no capturas de terminal. La captura 13 muestra una
vista parcial de la gráfica en MLflow; el archivo PNG y el PowerPoint contienen
la serie completa. El informe selecciona quince figuras de las evidencias.

Identidad del modelo mostrado: `credito-riesgo`, versión 2, alias `produccion`,
run `1e80a5489e3d4a4c82e58d10baf530d6`. Los IDs de Pods y horas de las imágenes
pertenecen al momento en que se tomó cada captura. Los registros de servidor
utilizan UTC y la interfaz del navegador muestra la zona horaria del equipo.
