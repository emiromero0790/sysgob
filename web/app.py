import json
import sqlite3
import threading
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

import config
from busqueda.motor import Motor
from procesamiento import almacen

GRUPOS = {
    "procesado": config.PROCESADO,
    "no_relacional": config.NO_RELACIONAL,
    "analisis": config.ANALISIS,
    "indices": config.INDICES,
    "evaluacion": config.EVALUACION,
}

DESCRIPCIONES = {
    "ofertas.csv": "Tabla plana del corpus, una fila por oferta.",
    "ofertas.json": "Arreglo JSON con documentos anidados.",
    "ofertas.jsonl": "Un documento JSON por línea; ideal para carga masiva.",
    "sysjobs.db": "Base relacional SQLite normalizada (5 tablas y 1 vista).",
    "resumen.json": "Conteo del pipeline de limpieza y deduplicación.",
    "tecnologias.csv": "Catálogo de tecnologías con su frecuencia.",
    "empresas.csv": "Catálogo de empresas con número de ofertas.",
    "fuentes.csv": "Portales de origen y volumen acopiado.",
    "ofertas_tecnologias.csv": "Relación N:M entre ofertas y tecnologías.",
    "estadisticas.json": "Agregados del corpus por fuente, área, nivel y modalidad.",
    "texto.json": "Frecuencias, n-gramas, palabras vacías y muestras del preprocesamiento.",
    "resultados.json": "Precisión, recall, MAP y nDCG de las tres estrategias.",
    "lexico.json.gz": "Índice invertido comprimido (término → postings).",
    "vectores.npy": "Matriz densa de embeddings (documentos × 384).",
    "vectorial.faiss": "Índice FAISS IndexFlatIP.",
    "matriz_tfidf.npz": "Matriz TF-IDF dispersa en formato CSR.",
    "vocabulario.json.gz": "Vocabulario TF-IDF con índice, df e idf.",
    "estructura.json": "Resumen de la vectorización y estructuras de datos.",
    "meta.json": "Metadatos del índice semántico y del léxico.",
    "lsa.joblib": "Respaldo LSA cuando no hay Sentence-Transformers.",
    "ofertas.jsonl": "Documentos listos para MongoDB.",
    "empresas.json": "Colección documental de empresas.",
    "fuentes.json": "Colección documental de fuentes.",
    "tecnologias.json": "Colección documental de tecnologías.",
    "importar_mongo.py": "Script opcional de importación con pymongo.",
    "README.txt": "Instrucciones de carga y consultas de ejemplo en MongoDB.",
}

FORMATOS = ("csv", "json", "jsonl", "db", "gz", "npy", "npz", "faiss", "joblib", "txt", "py")
BLOQUEO = threading.Lock()


def leer_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def _bytes_legibles(n):
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024
    return f"{n:.1f} GB"


def _archivos():
    archivos = []
    for grupo, carpeta in GRUPOS.items():
        if not carpeta.exists():
            continue
        for ruta in sorted(carpeta.rglob("*")):
            if not ruta.is_file() or ruta.suffix.lstrip(".").lower() not in FORMATOS:
                continue
            relativa = ruta.relative_to(carpeta).as_posix()
            archivos.append({
                "nombre": relativa,
                "grupo": grupo,
                "formato": ruta.suffix.lstrip(".").upper() or "SIN EXTENSIÓN",
                "bytes": ruta.stat().st_size,
                "tamano": _bytes_legibles(ruta.stat().st_size),
                "descripcion": DESCRIPCIONES.get(ruta.name, "Archivo generado por el pipeline."),
                "descarga": f"/descargas/{grupo}/{relativa}",
            })
    return archivos


def _esquema():
    if not config.BD.exists():
        return []
    conexion = sqlite3.connect(config.BD)
    try:
        tablas = [f[0] for f in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        esquema = []
        for tabla in tablas:
            columnas = []
            for columna in conexion.execute(f"PRAGMA table_info({tabla})"):
                rol = "PK" if columna[5] else ""
                if columna[3] == 0 and tabla == "ofertas":
                    rol = "PK"
                columnas.append({"nombre": columna[1], "tipo": columna[2], "rol": rol})
            filas = conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            esquema.append({"tabla": tabla, "filas": filas, "columnas": columnas})
        return esquema
    finally:
        conexion.close()


def _documento_ejemplo():
    if not config.JSONL_OFERTAS.exists():
        return None
    with open(config.JSONL_OFERTAS, encoding="utf-8") as entrada:
        linea = entrada.readline().strip()
    return json.loads(linea) if linea else None


def datos_corpus():
    conteos = almacen.conteos()
    archivos = _archivos()
    return {
        "archivos": archivos,
        "total_bytes": sum(a["bytes"] for a in archivos),
        "total_legible": _bytes_legibles(sum(a["bytes"] for a in archivos)),
        "conteos": conteos,
        "esquema_relacional": _esquema(),
        "documento_ejemplo": _documento_ejemplo(),
        "comandos": [
            {
                "titulo": "Consultar la base relacional",
                "lenguaje": "SQL",
                "codigo": "SELECT o.titulo, e.nombre AS empresa, o.modalidad, o.nivel\nFROM ofertas o\nJOIN empresas e ON e.id = o.empresa_id\nWHERE o.modalidad = 'remoto'\nORDER BY o.fecha_publicacion DESC\nLIMIT 10;",
            },
            {
                "titulo": "Abrir SQLite desde la terminal",
                "lenguaje": "Bash",
                "codigo": "sqlite3 data/procesado/sysjobs.db\n.tables\nSELECT * FROM vista_ofertas LIMIT 5;",
            },
            {
                "titulo": "Cargar documentos en MongoDB",
                "lenguaje": "Bash",
                "codigo": "mongoimport --db sysjobs --collection ofertas \\\n  --file data/no_relacional/ofertas.jsonl\n\npip install pymongo\npython data/no_relacional/importar_mongo.py --drop",
            },
            {
                "titulo": "Explorar con Python",
                "lenguaje": "Python",
                "codigo": "import json\nfrom pathlib import Path\n\nruta = Path('data/procesado/ofertas.jsonl')\nofertas = [json.loads(l) for l in ruta.read_text(encoding='utf-8').splitlines()]\nprint(len(ofertas), ofertas[0]['tecnologias'])",
            },
        ],
        "formatos": [
            {"id": "csv", "nombre": "CSV", "descripcion": "Hojas de cálculo, Excel, pandas y cargas masivas.", "archivo": "ofertas.csv"},
            {"id": "json", "nombre": "JSON", "descripcion": "Documentos anidados para APIs y JavaScript.", "archivo": "ofertas.json"},
            {"id": "jsonl", "nombre": "JSONL", "descripcion": "Un documento por línea; MongoDB, Elasticsearch y streaming.", "archivo": "ofertas.jsonl"},
            {"id": "sqlite", "nombre": "SQLite", "descripcion": "Modelo relacional normalizado con claves foráneas y vista.", "archivo": "sysjobs.db"},
            {"id": "mongodb", "nombre": "MongoDB", "descripcion": "Colecciones documentales listas para importar.", "archivo": "ofertas.jsonl"},
        ],
    }


def crear_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    motor = Motor()

    @app.get("/")
    def inicio():
        return render_template("index.html")

    @app.get("/api/buscar")
    def buscar():
        filtros = {
            campo: request.args.get(campo, "").strip()
            for campo in ("modalidad", "nivel", "fuente", "area", "idioma")
        }
        filtros["tecnologias"] = [t for t in request.args.get("tecnologias", "").split(",") if t]
        try:
            k = max(1, min(100, int(request.args.get("k", config.RESULTADOS_POR_PAGINA))))
        except ValueError:
            k = config.RESULTADOS_POR_PAGINA
        return jsonify(motor.buscar(request.args.get("q", ""), request.args.get("modo", "hibrido"), filtros, k))

    @app.get("/api/comparar")
    def comparar():
        consulta = request.args.get("q", "").strip()
        if not consulta:
            return jsonify({"error": "Escribe una consulta para comparar."}), 400
        return jsonify(motor.comparar(consulta))

    @app.get("/api/oferta/<identificador>")
    def oferta(identificador):
        dato = motor.detalle(identificador)
        if dato is None:
            return jsonify({"error": "La oferta no existe en el corpus."}), 404
        return jsonify(dato)

    @app.get("/api/corpus")
    def corpus():
        meta = dict(motor.semantico.meta)
        meta.pop("ids", None)
        return jsonify({
            "estadisticas": leer_json(config.ESTADISTICAS),
            "indices": meta,
            "evaluacion": leer_json(config.RESULTADOS_EVALUACION),
            "texto": leer_json(config.ANALISIS_TEXTO),
            "vectorizacion": leer_json(config.INDICE_ESTRUCTURA),
            "peso_semantico": config.PESO_SEMANTICO,
        })

    @app.get("/api/texto")
    def texto():
        return jsonify(leer_json(config.ANALISIS_TEXTO) or {})

    @app.get("/api/vectorizacion")
    def vectorizacion():
        return jsonify(leer_json(config.INDICE_ESTRUCTURA) or {})

    @app.get("/api/datos")
    def datos():
        return jsonify(datos_corpus())

    @app.post("/api/exportar")
    def exportar():
        with BLOQUEO:
            try:
                from procesamiento.exportar import exportar_todo
                resultado = exportar_todo()
            except Exception as error:  # pragma: no cover - se informa al cliente
                return jsonify({"error": f"No se pudo regenerar: {type(error).__name__}: {error}"}), 500
        return jsonify({"mensaje": f"Exportaciones regeneradas para {resultado['ofertas']} ofertas.", "datos": datos_corpus()})

    @app.get("/descargas/<grupo>/<path:nombre>")
    def descargar(grupo, nombre):
        carpeta = GRUPOS.get(grupo)
        if carpeta is None:
            abort(404)
        return send_from_directory(carpeta, nombre, as_attachment=True)

    @app.errorhandler(404)
    def no_encontrado(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Ruta no encontrada."}), 404
        return "No encontrado", 404

    return app
