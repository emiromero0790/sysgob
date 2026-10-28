"""Exportación del corpus a formatos relacionales y no relacionales.

Genera, a partir de la misma lista de ofertas:
  - CSV planos (ofertas, tecnologías, empresas, fuentes y relación N:M)
  - JSON (arreglo) y JSONL (un documento por línea)
  - SQLite normalizado (lo escribe procesamiento.almacen)
  - Documentos listos para MongoDB / Elasticsearch en data/no_relacional
"""

import csv
import json
from collections import Counter

import config
from procesamiento import almacen


def documento(oferta):
    """Documento anidado listo para una base no relacional."""
    return {
        "_id": oferta["id"],
        "titulo": oferta.get("titulo", ""),
        "empresa": {"nombre": oferta.get("empresa", "")},
        "fuente": oferta.get("fuente", ""),
        "url": oferta.get("url", ""),
        "ubicacion": oferta.get("ubicacion", ""),
        "clasificacion": {
            "modalidad": oferta.get("modalidad", ""),
            "nivel": oferta.get("nivel", ""),
            "area": oferta.get("area", ""),
            "idioma": oferta.get("idioma", ""),
        },
        "tecnologias": oferta.get("tecnologias") or [],
        "fechas": {
            "publicacion": oferta.get("fecha_publicacion", ""),
            "extraccion": oferta.get("fecha_extraccion", ""),
        },
        "descripcion": oferta.get("descripcion", ""),
        "metadatos": {
            "caracteres": len(oferta.get("descripcion") or ""),
            "num_tecnologias": len(oferta.get("tecnologias") or []),
        },
    }


def _escribir_csv(ruta, campos, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as salida:
        escritor = csv.DictWriter(salida, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)


def _colecciones(ofertas):
    empresas = {}
    fuentes = Counter()
    tecnologias = {}
    for oferta in ofertas:
        nombre = oferta.get("empresa") or "Sin empresa"
        empresa = empresas.setdefault(nombre, {
            "_id": nombre, "total_ofertas": 0, "fuentes": Counter(),
            "modalidades": Counter(), "tecnologias": Counter(),
        })
        empresa["total_ofertas"] += 1
        empresa["fuentes"][oferta.get("fuente", "")] += 1
        empresa["modalidades"][oferta.get("modalidad", "")] += 1
        for tecnologia in oferta.get("tecnologias") or []:
            empresa["tecnologias"][tecnologia] += 1
            tecnologias.setdefault(tecnologia, {"_id": tecnologia, "total_ofertas": 0, "areas": Counter()})
            tecnologias[tecnologia]["total_ofertas"] += 1
            tecnologias[tecnologia]["areas"][oferta.get("area", "")] += 1
        fuentes[oferta.get("fuente", "")] += 1

    def serializar(coleccion):
        return [
            {**valor, **{k: dict(v) for k, v in valor.items() if isinstance(v, Counter)}}
            for valor in coleccion.values()
        ]

    return {
        "empresas": serializar(empresas),
        "fuentes": [{"_id": nombre, "total_ofertas": total} for nombre, total in fuentes.most_common()],
        "tecnologias": sorted(serializar(tecnologias), key=lambda x: -x["total_ofertas"]),
    }


IMPORTADOR = '''"""Importa los documentos de SysJobs a MongoDB.

Uso:
    pip install pymongo
    python data/no_relacional/importar_mongo.py
    python data/no_relacional/importar_mongo.py --uri mongodb://localhost:27017 --db sysjobs --drop
"""
import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def leer(nombre):
    ruta = BASE / nombre
    if not ruta.exists():
        return []
    if nombre.endswith(".jsonl"):
        return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]
    return json.loads(ruta.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Carga el corpus SysJobs en MongoDB")
    parser.add_argument("--uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", default="sysjobs")
    parser.add_argument("--drop", action="store_true", help="Borra las colecciones antes de importar")
    args = parser.parse_args()
    try:
        from pymongo import MongoClient
    except ImportError:
        print("Falta pymongo. Instálalo con:  pip install pymongo")
        print("También puedes usar:  mongoimport --db sysjobs --collection ofertas --file ofertas.jsonl")
        return
    cliente = MongoClient(args.uri)
    bd = cliente[args.db]
    for coleccion, archivo in (
        ("ofertas", "ofertas.jsonl"),
        ("empresas", "empresas.json"),
        ("fuentes", "fuentes.json"),
        ("tecnologias", "tecnologias.json"),
    ):
        datos = leer(archivo)
        if not datos:
            continue
        if args.drop:
            bd[coleccion].drop()
        bd[coleccion].delete_many({})
        bd[coleccion].insert_many(datos)
        print(f"{coleccion}: {len(datos)} documentos")
    print(f"Listo: {args.uri}/{args.db}")


if __name__ == "__main__":
    main()
'''


def exportar(ofertas):
    """Escribe JSON, JSONL, CSV auxiliares y el modelo documental."""
    config.PROCESADO.mkdir(parents=True, exist_ok=True)
    documentos = [documento(o) for o in ofertas]

    config.JSON_OFERTAS.write_text(
        json.dumps(documentos, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with open(config.JSONL_OFERTAS, "w", encoding="utf-8") as salida:
        for item in documentos:
            salida.write(json.dumps(item, ensure_ascii=False) + "\n")

    relaciones = [
        {"oferta_id": o["id"], "tecnologia": t, "posicion": posicion}
        for o in ofertas for posicion, t in enumerate(o.get("tecnologias") or [])
    ]
    _escribir_csv(config.CSV_OFERTA_TECNOLOGIA, ["oferta_id", "tecnologia", "posicion"], relaciones)
    _escribir_csv(
        config.CSV_TECNOLOGIAS, ["tecnologia", "total_ofertas"],
        [{"tecnologia": t, "total_ofertas": n} for t, n in Counter(
            t for o in ofertas for t in (o.get("tecnologias") or [])
        ).most_common()],
    )
    _escribir_csv(
        config.CSV_EMPRESAS, ["empresa", "total_ofertas"],
        [{"empresa": e, "total_ofertas": n} for e, n in Counter(
            o.get("empresa") or "Sin empresa" for o in ofertas
        ).most_common()],
    )
    _escribir_csv(
        config.CSV_FUENTES, ["fuente", "total_ofertas"],
        [{"fuente": f, "total_ofertas": n} for f, n in Counter(
            o.get("fuente", "") for o in ofertas
        ).most_common()],
    )

    config.NO_RELACIONAL.mkdir(parents=True, exist_ok=True)
    with open(config.NO_RELACIONAL / "ofertas.jsonl", "w", encoding="utf-8") as salida:
        for item in documentos:
            salida.write(json.dumps(item, ensure_ascii=False) + "\n")
    colecciones = _colecciones(ofertas)
    for nombre, datos in colecciones.items():
        (config.NO_RELACIONAL / f"{nombre}.json").write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    (config.NO_RELACIONAL / "importar_mongo.py").write_text(IMPORTADOR, encoding="utf-8")
    (config.NO_RELACIONAL / "README.txt").write_text(
        """SYSJOBS - MODELO DOCUMENTAL (NO RELACIONAL)
==========================================

ofertas.jsonl      Un documento JSON por oferta (formato de carga masiva).
empresas.json      Colección de empresas con agregados.
fuentes.json       Colección de portales de origen.
tecnologias.json   Colección de tecnologías con áreas asociadas.
importar_mongo.py  Importador opcional con pymongo.

Carga con MongoDB Database Tools:
    mongoimport --db sysjobs --collection ofertas --file ofertas.jsonl
    mongoimport --db sysjobs --collection empresas --file empresas.json --jsonArray
    mongoimport --db sysjobs --collection fuentes --file fuentes.json --jsonArray
    mongoimport --db sysjobs --collection tecnologias --file tecnologias.json --jsonArray

Carga con Python:
    pip install pymongo
    python importar_mongo.py --drop

Consulta de ejemplo:
    db.ofertas.find({ "tecnologias": "python", "clasificacion.modalidad": "remoto" })
    db.ofertas.aggregate([
      { $unwind: "$tecnologias" },
      { $group: { _id: "$tecnologias", total: { $sum: 1 } } },
      { $sort: { total: -1 } }
    ])
""",
        encoding="utf-8",
    )
    print(f"Exportado: JSON, JSONL, CSV y modelo documental en {config.PROCESADO} y {config.NO_RELACIONAL}")
    return {
        "ofertas": len(ofertas),
        "json": str(config.JSON_OFERTAS),
        "jsonl": str(config.JSONL_OFERTAS),
        "no_relacional": str(config.NO_RELACIONAL),
    }


def exportar_todo():
    ofertas = almacen.cargar()
    almacen.guardar(ofertas)
    return exportar(ofertas)
