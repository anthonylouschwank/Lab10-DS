# Lab 10 · Visualización interactiva

Tablero en **Streamlit + Plotly** del observatorio de turismo sostenible. Muestra la llegada de
viajeros internacionales a Guatemala entre enero de 2009 y junio de 2026. Curso CC3066 Data
Science, UVG.

Los datos y los modelos vienen de los Laboratorios 1 y 2
([DM-Laboratorio-1.-Series-de-Tiempo](https://github.com/Isabella1911/DM-Laboratorio-1.-Series-de-Tiempo)).
En este laboratorio no se entrenan modelos nuevos.

## Equipo

- Anthony Lou Schwank
- Christa Isabella Obando Guzmán
- Fabian Prado Dluzniewski
- Luis Fernando Mendoza Alvarez

## Contenido

7 páginas y **11 visualizaciones interactivas**, 10 de ellas en cinco pares enlazados
(un clic en la gráfica de origen cambia la de detalle):

| Página | Visualizaciones |
|---|---|
| Resumen | Indicadores, llegadas mensuales con promedio móvil, lectura principal |
| Evolución y origen | 1. Evolución por vía → 2. Origen / puesto de ingreso de la selección |
| Temporadas | 3. Mapa de calor año × mes → 4. Perfil mensual por vía del año elegido |
| Mercados y recuperación | 5. Índice de recuperación (2019 = 100) → 6. Árbol región → país |
| Pronósticos de llegadas | 7. Real vs. pronóstico por modelo → 8. Error por modelo en los periodos elegidos |
| Comparar modelos | 9. Mapa de errores serie × modelo → 10. Error por año; 11. Ajuste de la LSTM; tabla comparativa |
| Acerca del tablero | Glosario, colores, limitaciones, equipo |

Modelos (de los Laboratorios 1 y 2, **no se entrena nada nuevo**): Holt-Winters, SARIMA, Prophet,
LSTM y una referencia ingenua.

## Estructura

```text
app.py                      Punto de entrada: navegación entre páginas
paginas/                    Una página por archivo (inicio, explorar, temporadas, mercados,
                            modelos = pronósticos, comparar, acerca = glosario)
src/
  preparar_datos.py         xlsx -> parquet (data/procesados/viajeros.parquet)
  preparar_modelos.py       Resultados Labs 1 y 2 -> data/modelos/*.parquet
  datos.py / modelos.py     Carga con caché, filtros, métricas de error
  estilo.py                 Paleta de colores y estilo común de las gráficas
  graficas.py               Funciones que construyen cada figura (app y documento)
  ui.py                     Componentes de interfaz: encabezados, tarjetas, indicadores, filtros
  exportar_figuras.py       Exporta las figuras a report/figures/ (kaleido + Chrome)
data/
  raw/                      Base original (uso académico, no son cifras oficiales)
  procesados/               Parquet de viajeros
  modelos/                  Pronósticos de prueba, series y tuneo LSTM de los Labs 1 y 2
static/                     Tipografía IBM Plex (licencia OFL) y logotipo
report/
  documento_diseno.html/.pdf  Documento de diseño (entregable)
  generar_pdf.py            HTML -> PDF con Chromium (Playwright)
  figures/, fuentes/        Figuras exportadas y boceto de la interfaz
tests/test_app.py           Pruebas de humo de todas las páginas (streamlit.testing)
.streamlit/config.toml      Tema de la aplicación
```

## Cómo correrlo

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows
.venv/bin/pip install -r requirements.txt         # Linux/Mac
streamlit run app.py
python -m pytest tests                            # pruebas
```

Si no existe el parquet de viajeros, la app lo genera desde el Excel la primera vez que carga.

## Pipeline de estimaciones (Laboratorio 11)

Estima los visitantes internacionales mensuales del **Lago de Atitlán (Sololá)**, grupo 3. Todo
se configura en [config/config.yaml](config/config.yaml): rutas, periodos, fórmula, factor de
reparto, semilla y umbrales de aceptación.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-pipeline.txt
python -m pipeline                                 # usa config/config.yaml
python -m pipeline --fuente RUTA/A/LA/BASE.xlsx    # o la variable de entorno OBS_FUENTE
python -m pytest tests/test_pipeline.py            # controles con datos sintéticos
```

Etapas: lectura → validación (6 controles) → preparación → ajuste → evaluación → estimación →
almacenamiento → publicación. Cada ejecución deja en `salidas/ejecuciones/<id>/` el reporte de
calidad (`calidad.md`, `calidad.json`), las estimaciones, las métricas, los parámetros, la
configuración usada, el registro y un `manifiesto.json` con el commit, la huella SHA-256 de la
fuente y las versiones de las dependencias. Solo una versión que cumple la regla de aceptación se
copia a `salidas/versiones/<id>/` y queda apuntada en `salidas/vigente.json`. Si falla un control
crítico, el pipeline se detiene antes de estimar y la versión vigente no cambia.

Código de salida: 0 publicada, 2 rechazada por la regla de aceptación, 1 fallida.

## Resultados de los modelos

`data/modelos/` ya está versionado. Para regenerarlo desde el repositorio de los laboratorios
([DM-Laboratorio-1.-Series-de-Tiempo](https://github.com/Isabella1911/DM-Laboratorio-1.-Series-de-Tiempo)),
ejecutar allí el pipeline del Lab 1 (`L.run()` y `M.ejecutar_parte2()`, Python 3.11/3.12) y luego:

```bash
python -m src.preparar_modelos RUTA_AL_REPO_DE_LOS_LABS
```

## Documento de diseño

```bash
python -m src.exportar_figuras        # regenera report/figures/ (BROWSER_PATH=ruta a Chrome si hace falta)
python report/generar_pdf.py          # report/documento_diseno.pdf
```

## Paleta de colores

Cada color significa lo mismo en todo el tablero:

| Uso | Color |
|---|---|
| Vía aérea | `#2a78d6` azul |
| Vía terrestre | `#eb6834` naranja |
| Vía marítima | `#1baf7a` aqua |
| Magnitud (mapas de calor) | escala de un solo azul, de claro a oscuro |
| Índice de recuperación | divergente: rojo (por debajo) – gris (igual) – azul (por encima) |
| Modelos | violeta Holt-Winters, rosa SARIMA, amarillo Prophet, verde LSTM, gris referencia; cada uno con su tipo de línea |
| Valor real | negro |

Los tres colores de las vías están validados para que se distingan entre sí con los tipos
comunes de daltonismo. El azul, el naranja y el aqua, además, no se confunden con los colores de
estado (verde, amarillo y rojo). El texto va siempre en gris o negro, nunca en el color de la
serie.
