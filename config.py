from pathlib import Path

BASE = Path(__file__).resolve().parent
DATOS = BASE / "data"
CRUDO = DATOS / "crudo"
MANUAL = DATOS / "manual"
PROCESADO = DATOS / "procesado"
INDICES = DATOS / "indices"
ANALISIS = DATOS / "analisis"
EVALUACION = DATOS / "evaluacion"

BITACORA = CRUDO / "bitacora.jsonl"
CSV_OFERTAS = PROCESADO / "ofertas.csv"
BD = PROCESADO / "sysjobs.db"
RESUMEN_PROCESO = PROCESADO / "resumen.json"
ESTADISTICAS = ANALISIS / "estadisticas.json"
RESULTADOS_EVALUACION = EVALUACION / "resultados.json"
CONSULTAS_EVALUACION = BASE / "evaluacion" / "consultas.json"

INDICE_LEXICO = INDICES / "lexico.json.gz"
INDICE_VECTORES = INDICES / "vectores.npy"
INDICE_FAISS = INDICES / "vectorial.faiss"
INDICE_LSA = INDICES / "lsa.joblib"
INDICE_META = INDICES / "meta.json"

AGENTE = "SysJobsBot/1.0 (proyecto academico de Recuperacion de Informacion, TecNM campus Morelia)"
PAUSA = 1.5
TIEMPO_ESPERA = 25
REINTENTOS = 3
LIMITE_POR_FUENTE = 300

FUENTES_POR_DEFECTO = ["getonboard", "remotive", "arbeitnow", "computrabajo", "manual"]

GETONBOARD_PALABRAS = ["programming", "devops", "sysadmin", "mobile", "data", "machine", "cyber", "qa"]

REMOTIVE_CATEGORIAS = ["software", "devops", "sysadmin", "data", "qa"]

PALABRAS_TI = [
    "developer", "engineer", "software", "programmer", "devops", "data", "backend", "frontend",
    "fullstack", "full stack", "full-stack", "entwickler", "python", "java", "cloud", "qa",
    "security", "sysadmin", "administrator", "machine learning", "web", "mobile", "it "
]

SITIOS_HTML = [
    {
        "nombre": "computrabajo",
        "listados": [
            "https://mx.computrabajo.com/trabajo-de-programador",
            "https://mx.computrabajo.com/trabajo-de-desarrollador-de-software",
            "https://mx.computrabajo.com/trabajo-de-practicante-de-sistemas",
            "https://mx.computrabajo.com/trabajo-de-ingeniero-en-sistemas"
        ],
        "parametro_pagina": "p",
        "paginas": 3,
        "patron_enlace": r"/ofertas-de-trabajo/oferta-de-trabajo-de-",
        "selector_descripcion": "div[div-link='oferta'], div.box_detail, main",
        "selector_empresa": "a.dIB.fs16.js-o-link, div.info_company a, p.fs16"
    }
]

UMBRAL_CASI_DUPLICADO = 0.9

BM25_K1 = 1.5
BM25_B = 0.75

BACKEND_EMBEDDINGS = "auto"
MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
LONGITUD_MAXIMA_MODELO = 256
DIM_LSA = 200

PESO_SEMANTICO = 0.6
RESULTADOS_POR_PAGINA = 30
CORTE_EVALUACION = 10

SERVIDOR = "127.0.0.1"
PUERTO = 5000
