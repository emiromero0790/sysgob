# SysJobs

Buscador semántico de vacantes y residencias profesionales para el área de
Ingeniería en Sistemas. El proyecto cubre el ciclo completo de recuperación de
información: acopio, limpieza y normalización del texto, análisis lingüístico,
indexación léxica y vectorial, evaluación y una interfaz web.

La interfaz está en español y los datos pueden estar en español, inglés, alemán
o francés. El corpus incluido tiene **467 ofertas** procesadas.

## Características

- Acopio automatizado de Get on Board, Remotive, Arbeitnow y Computrabajo, más
  carga manual desde CSV.
- Limpieza de HTML, URLs, correos, emojis, signos y números; normalización
  Unicode, tokenización y palabras vacías en español, inglés, alemán y francés.
- Lematización y derivación (stemming) con reglas propias de español e inglés,
  sin depender de spaCy ni NLTK.
- Estadísticas de contenido: frecuencias, vocabulario, hapax, diversidad léxica,
  n-gramas (bigramas y trigramas), nube de palabras y muestras del pipeline.
- Búsqueda léxica BM25, búsqueda semántica con embeddings multilingües (384
  dimensiones) y ranking híbrido ponderado.
- Vectorización explícita: matriz TF-IDF dispersa (CSR), vocabulario con IDF,
  índice invertido y embeddings densos.
- Exportación del mismo corpus a CSV, JSON, JSONL, SQLite normalizado y
  documentos listos para MongoDB.
- Interfaz con cinco vistas (Buscar, Comparar, Texto, Datos, Corpus), tema claro
  y oscuro, filtros con conteos y dictado/lectura por voz con la Web Speech API.

## Requisitos

- Python 3.10, 3.11 o 3.12.
- Windows, macOS o Linux.
- ~3 GB libres si se instala la versión completa (PyTorch).
- Conexión a internet solo para instalar dependencias, hacer acopio y descargar
  el modelo de embeddings la primera vez.

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Si la versión completa falla, `requirements-minimo.txt` instala todo lo necesario
para trabajar con LSA y NumPy en lugar de Sentence-Transformers y FAISS.

## Inicio rápido

```powershell
python main.py demo        # corpus sintético para probar sin internet
python main.py construir   # procesar + analizar + indexar + evaluar
python main.py web         # http://127.0.0.1:5000
```

Con datos reales:

```powershell
python main.py acopio      # recolecta de las fuentes configuradas
python main.py construir   # pipeline completo
python main.py web
```

También puede ejecutarse cada etapa por separado:

| Comando | Qué hace | Salidas principales |
| --- | --- | --- |
| `python main.py acopio` | Recolecta ofertas nuevas | `data/crudo/<fuente>/...` |
| `python main.py procesar` | Limpia, extrae entidades, deduplica y guarda | `data/procesado/ofertas.csv`, `sysjobs.db`, JSON, JSONL |
| `python main.py analizar` | Estadísticas del corpus y del texto | `data/analisis/estadisticas.json`, `texto.json` |
| `python main.py indexar` | Índice BM25, embeddings, FAISS y TF-IDF | `data/indices/*` |
| `python main.py evaluar` | Métricas de las tres estrategias | `data/evaluacion/resultados.json` |
| `python main.py exportar` | Regenera todos los formatos desde SQLite | CSV, JSON, JSONL y `data/no_relacional/*` |
| `python main.py construir` | Ejecuta procesar, analizar, indexar y evaluar | Todo lo anterior |
| `python main.py todo` | Acopio + construir | Todo lo anterior |
| `python main.py buscar "python remoto"` | Búsqueda desde la terminal | Resultados en consola |
| `python main.py web` | Servidor Flask | `http://127.0.0.1:5000` |

Opciones útiles:

```powershell
python main.py acopio --fuentes getonboard remotive --limite 150
python main.py buscar "ingeniero de apis" --modo semantico -k 5
python main.py web --puerto 8000
```

## Flujo de datos

```text
data/crudo/*.json
      │
      ├─ limpieza de HTML, normalización y tokenización
      ├─ entidades: tecnologías, modalidad, nivel, área e idioma
      ├─ duplicados exactos y casi duplicados (TF-IDF + coseno)
      ▼
data/procesado/  →  CSV · JSON · JSONL · SQLite · documentos MongoDB
      │
      ├─ estadísticas y análisis de texto
      ├─ índice invertido BM25
      ├─ matriz TF-IDF dispersa + vocabulario
      └─ embeddings densos + FAISS
      ▼
Buscador web (léxico / semántico / híbrido)
```

## Preprocesamiento del texto

El mismo recorrido se aplica a las ofertas y a la consulta:

1. **Limpieza**: se quita HTML, scripts, URLs, correos, emojis, signos y números
   sueltos, conservando términos técnicos como `c++`, `c#`, `node.js` y `.net`.
2. **Normalización**: minúsculas, Unicode NFC/NFD y eliminación de acentos.
3. **Tokenización**: separación en palabras con longitud mínima configurable.
4. **Palabras vacías**: listas en español, inglés, alemán y francés.
5. **Lematización**: diccionarios de formas irregulares y reglas de plural,
   género y conjugación para español e inglés.
6. **Derivación**: raíz más agresiva para agrupar variantes de una misma palabra.
7. **N-gramas**: bigramas y trigramas consecutivos para detectar expresiones.

La estrategia de indexación se controla en `config.py` con `ESTRATEGIA_TOKENS`
(`lema`, `derivada` o `palabra`). En la corrida incluida se obtuvieron 189,141
tokens útiles, 15,648 lemas distintos y una reducción de ruido del 32.7 %.

## Vectorización e índices

- `data/indices/lexico.json.gz`: índice invertido `término → [[documento, frecuencia]]`
  con IDF y longitudes de documento para BM25.
- `data/indices/matriz_tfidf.npz`: matriz CSR de 467 × 15,693 con 119,430 valores
  no cero (densidad 1.63 %).
- `data/indices/vocabulario.json.gz`: término, índice, frecuencia documental e IDF.
- `data/indices/vectores.npy`: embeddings densos de 467 × 384, normalizados L2.
- `data/indices/vectorial.faiss`: índice `IndexFlatIP` para similitud coseno.
- `data/indices/estructura.json`: resumen legible de todas las estructuras, con un
  vector de ejemplo y los componentes de mayor peso.

`data/indices/estructura.json` es la vista recomendada para explicar cómo una
oferta se convierte en una fila de números: incluye dimensiones, densidad, valores
no cero y los términos con mayor peso TF-IDF.

## Formatos de datos

| Formato | Archivo | Uso |
| --- | --- | --- |
| CSV | `data/procesado/ofertas.csv` | Hojas de cálculo, Excel, pandas |
| JSON | `data/procesado/ofertas.json` | APIs y documentos anidados |
| JSONL | `data/procesado/ofertas.jsonl` | Carga masiva y streaming |
| SQLite | `data/procesado/sysjobs.db` | Modelo relacional normalizado |
| MongoDB | `data/no_relacional/*.json(l)` | Colecciones documentales |

El modelo relacional tiene cinco tablas (`fuentes`, `empresas`, `tecnologias`,
`ofertas`, `oferta_tecnologia`) y la vista `vista_ofertas` que reconstruye cada
oferta con su fuente, empresa y tecnologías.

El modelo no relacional incluye `ofertas.jsonl`, `empresas.json`, `fuentes.json`,
`tecnologias.json`, un `importar_mongo.py` opcional y un `README.txt` con consultas
de ejemplo.

```powershell
# SQLite
sqlite3 data/procesado/sysjobs.db
SELECT * FROM vista_ofertas LIMIT 5;

# MongoDB (opcional)
pip install pymongo
python data/no_relacional/importar_mongo.py --drop
```

## Interfaz web

- **Buscar**: consulta en lenguaje natural, tres modos de orden, filtros por
  modalidad, nivel, área, tecnología, idioma y fuente, y dictado por micrófono.
- **Comparar**: rankings léxico y semántico lado a lado, marcando las ofertas que
  solo aparecen en uno de los dos.
- **Texto**: pipeline paso a paso, comparación antes/después, frecuencias, nube de
  lemas, n-gramas y ejemplos de lematización/derivación.
- **Datos**: tamaños, descargas, esquema relacional, documento de ejemplo,
  consultas listas y regeneración de exportaciones.
- **Corpus**: embudo de limpieza, distribución por fuente/modalidad/nivel/área,
  tecnologías, índice léxico, índice semántico, vectorización y evaluación.

La voz usa las APIs del navegador: `SpeechRecognition` para dictar la consulta y
`speechSynthesis` para escuchar ofertas y resúmenes. Funciona mejor en Chrome o
Edge y requiere permisos de micrófono. No se envía audio al servidor.

Atajos: `1`–`5` cambian de vista, `/` enfoca el buscador y `Esc` cierra el detalle,
los filtros o detiene la lectura.

## API REST

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/` | Interfaz web |
| GET | `/api/buscar` | `q`, `modo`, `k`, `modalidad`, `nivel`, `area`, `idioma`, `fuente`, `tecnologias` |
| GET | `/api/comparar?q=` | Comparación léxico vs semántico |
| GET | `/api/oferta/<id>` | Detalle de una oferta |
| GET | `/api/corpus` | Estadísticas, índices, evaluación, texto y vectorización |
| GET | `/api/texto` | Análisis de texto |
| GET | `/api/vectorizacion` | Resumen de la matriz TF-IDF y embeddings |
| GET | `/api/datos` | Inventario de archivos, esquema y comandos |
| POST | `/api/exportar` | Regenera CSV, JSON, JSONL, SQLite y MongoDB |
| GET | `/descargas/<grupo>/<archivo>` | Descarga de un archivo generado |

## Estructura del proyecto

```text
sysjobs/
├─ main.py                 comandos de terminal
├─ config.py               rutas, parámetros y fuentes
├─ acopio/                 recolectores por portal
├─ procesamiento/          limpieza, lematización, entidades, estadísticas y exportación
├─ indexacion/             BM25, embeddings, FAISS y vectorización TF-IDF
├─ busqueda/               motor híbrido y detalle de ofertas
├─ evaluacion/             consultas, métricas y resultados
├─ web/                    Flask, plantilla, CSS y JavaScript
└─ data/
   ├─ crudo/               ofertas originales en JSON
   ├─ procesado/           CSV, JSON, JSONL y SQLite
   ├─ analisis/            estadísticas y texto
   ├─ indices/             índices léxico, semántico y TF-IDF
   ├─ no_relacional/       documentos para MongoDB
   └─ evaluacion/          métricas
```

## Evaluación

`python main.py evaluar` ejecuta 13 consultas de prueba en los tres modos y mide
precisión, recall, MAP y nDCG@10. Los juicios de relevancia son automáticos: una
oferta cuenta como relevante si sus campos extraídos cumplen los criterios de
`evaluacion/consultas.json`. En la corrida incluida, el nDCG@10 promedio fue
0.298 (léxico), 0.334 (semántico) y 0.353 (híbrido).

Las métricas sirven para comparar estrategias entre sí, no como una medida
absoluta de calidad. Para un análisis más riguroso conviene etiquetar a mano una
muestra de resultados.

## Notas y limitaciones

- Sin Sentence-Transformers o FAISS el sistema sigue funcionando con LSA y NumPy;
  la vista Corpus indica qué backend se usó realmente.
- LinkedIn y OCC no se automatizan por restricciones de sus términos o por cargar
  las ofertas con JavaScript. Se pueden integrar por `data/manual`.
- El dictado por voz depende del navegador y de una conexión a internet en algunos
  navegadores; la lectura en voz alta usa las voces instaladas en el sistema.
- El texto se guarda en UTF-8. Algunas terminales de Windows muestran mal los
  acentos, pero los archivos y la interfaz son correctos.

## Documentación adicional

- `LEEME_PASOS.txt`: instalación y ejecución paso a paso.
- `EXPLICACION.txt`: qué hace cada archivo y las decisiones de diseño.
