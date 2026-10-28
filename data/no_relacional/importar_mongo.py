"""Importa los documentos de SysJobs a MongoDB.

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
