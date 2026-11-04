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
