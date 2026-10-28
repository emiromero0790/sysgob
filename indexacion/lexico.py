import gzip
import json
import math
from collections import Counter, defaultdict

import config
from procesamiento.limpieza import tokenizar


class IndiceLexico:
    def __init__(self):
        self.ids = []
        self.longitudes = []
        self.promedio = 0.0
        self.postings = {}
        self.idf = {}

    def construir(self, ids, textos):
        self.ids = list(ids)
        postings = defaultdict(list)
        self.longitudes = []
        for posicion, texto in enumerate(textos):
            tokens = tokenizar(texto)
            self.longitudes.append(len(tokens))
            for termino, frecuencia in Counter(tokens).items():
                postings[termino].append([posicion, frecuencia])
        self.postings = dict(postings)
        self.promedio = sum(self.longitudes) / max(1, len(self.longitudes))
        n = len(self.ids)
        self.idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}
        return self

    def guardar(self, ruta=None):
        ruta = ruta or config.INDICE_LEXICO
        ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = {
            "k1": config.BM25_K1,
            "b": config.BM25_B,
            "ids": self.ids,
            "longitudes": self.longitudes,
            "promedio": self.promedio,
            "idf": self.idf,
            "postings": self.postings
        }
        with gzip.open(ruta, "wt", encoding="utf-8") as salida:
            json.dump(datos, salida, ensure_ascii=False)

    @classmethod
    def cargar(cls, ruta=None):
        ruta = ruta or config.INDICE_LEXICO
        if not ruta.exists():
            raise FileNotFoundError("No existe el indice lexico. Ejecuta: python main.py indexar")
        with gzip.open(ruta, "rt", encoding="utf-8") as entrada:
            datos = json.load(entrada)
        indice = cls()
        indice.ids = datos["ids"]
        indice.longitudes = datos["longitudes"]
        indice.promedio = datos["promedio"]
        indice.idf = datos["idf"]
        indice.postings = datos["postings"]
        return indice

    def buscar(self, consulta, permitidos=None):
        k1, b = config.BM25_K1, config.BM25_B
        puntajes = defaultdict(float)
        for termino in set(tokenizar(consulta)):
            idf = self.idf.get(termino)
            if idf is None:
                continue
            for posicion, frecuencia in self.postings[termino]:
                norma = 1 - b + b * self.longitudes[posicion] / (self.promedio or 1)
                puntajes[posicion] += idf * frecuencia * (k1 + 1) / (frecuencia + k1 * norma)
        resultados = [(self.ids[p], s) for p, s in puntajes.items() if permitidos is None or self.ids[p] in permitidos]
        resultados.sort(key=lambda par: (-par[1], par[0]))
        return resultados
