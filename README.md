# Lab 10 · Visualización interactiva

Tablero en **Streamlit + Plotly** del observatorio de turismo sostenible. Muestra la llegada de
viajeros internacionales a Guatemala entre enero de 2009 y junio de 2026. Curso CC3066 Data
Science, UVG.

Los datos y los modelos vienen de los Laboratorios 1 y 2
([DM-Laboratorio-1.-Series-de-Tiempo](https://github.com/Isabella1911/DM-Laboratorio-1.-Series-de-Tiempo)).
En este laboratorio no se entrenan modelos nuevos.

## Estructura

```text
app.py                      Punto de entrada: navegación entre páginas
paginas/
  inicio.py                 Preguntas de gestión y guía de navegación
  explorar.py               Visualizaciones enlazadas: evolución por vía -> origen / frontera
  modelos.py                Pronósticos y comparación de modelos (entrega final)
  acerca.py                 Glosario y limitaciones de los datos
src/
  preparar_datos.py         xlsx -> parquet (data/procesados/viajeros.parquet)
  datos.py                  Carga con caché, filtros y niveles de detalle temporal
  estilo.py                 Paleta de colores y estilo común de las gráficas
  graficas.py               Funciones que construyen cada figura (app y documento)
  exportar_figuras.py       Exporta las figuras a report/figures/ (requiere kaleido + Chrome)
data/
  raw/                      Base original (uso académico, no son cifras oficiales)
  procesados/               Parquet generado por src/preparar_datos.py
report/
  main.tex, main.pdf        Documento de diseño (avance)
  figures/                  Figuras exportadas del tablero
.streamlit/config.toml      Tema de la aplicación
```

## Documento de diseño

```bash
python -m src.exportar_figuras                    # regenera report/figures/
cd report && pdflatex main.tex && pdflatex main.tex
```

## Cómo correrlo

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows
.venv/bin/pip install -r requirements.txt         # Linux/Mac
python -m src.preparar_datos                      # solo la primera vez (genera el parquet)
streamlit run app.py
```

Si no existe el parquet, la app lo genera desde el Excel la primera vez que carga.

## Paleta de colores

Cada color significa lo mismo en todo el tablero:

| Uso | Color |
|---|---|
| Vía aérea | `#2a78d6` azul |
| Vía terrestre | `#eb6834` naranja |
| Vía marítima | `#1baf7a` aqua |
| Magnitud (mapas de calor) | escala de un solo azul, de claro a oscuro |

Los tres colores de las vías están validados para que se distingan entre sí con los tipos
comunes de daltonismo. El azul, el naranja y el aqua, además, no se confunden con los colores de
estado (verde, amarillo y rojo). El texto va siempre en gris o negro, nunca en el color de la
serie.
