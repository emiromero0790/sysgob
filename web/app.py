import json

from flask import Flask, jsonify, render_template, request

import config
from busqueda.motor import Motor


def leer_json(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


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
        filtros = {campo: request.args.get(campo, "").strip() for campo in ("modalidad", "nivel", "fuente", "area")}
        filtros["tecnologias"] = [t for t in request.args.get("tecnologias", "").split(",") if t]
        return jsonify(motor.buscar(request.args.get("q", ""), request.args.get("modo", "hibrido"), filtros))

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
            "peso_semantico": config.PESO_SEMANTICO
        })

    return app
