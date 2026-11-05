# Presentación web de la defensa

Abrir `index.html` con doble clic. No necesita servidor, instalación ni Internet para recorrer los pasos y ver las imágenes. Mantener esta carpeta junto a `evidencias` dentro del repositorio.

También se puede abrir desde PowerShell, en la raíz del proyecto:

```powershell
Invoke-Item .\presentacion\index.html
```

- Anterior y Siguiente recorren los 15 pasos. Las flechas del teclado hacen lo mismo.
- La dirección conserva la posición mediante `#paso-N`.
- Ampliar abre la captura completa; Escape la cierra.
- Copiar lleva el comando comentado al portapapeles. En filtros y JSON se copia solo el contenido válido. La web no ejecuta comandos.
- Los enlaces de MLflow y de la API requieren Docker Desktop y el laboratorio activos.
- Los enlaces de GitHub requieren Internet.

La presentación usa la ejecución entregada: `credito-riesgo`, versión 2, run `1e80a5489e3d4a4c82e58d10baf530d6`. Después de un reentrenamiento, revisar esa referencia y las capturas. Las capturas muestran resultados guardados, no un indicador de estado en vivo.
