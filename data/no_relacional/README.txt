SYSJOBS - MODELO DOCUMENTAL (NO RELACIONAL)
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
