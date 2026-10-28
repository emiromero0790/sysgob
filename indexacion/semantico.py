import json

import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import normalize

import config
from procesamiento.limpieza import tokenizar


def elegir_backend():
    if config.BACKEND_EMBEDDINGS in ("sbert", "lsa"):
        return config.BACKEND_EMBEDDINGS
    try:
        import sentence_transformers
        return "sbert"
    except Exception as error:
        print(f"sentence-transformers no disponible ({type(error).__name__}); se usa el respaldo LSA.")
        return "lsa"


def cargar_faiss():
    try:
        import faiss
        return faiss
    except Exception:
        return None


class Codificador:
    def __init__(self, backend):
        self.backend = backend
        self.modelo = None

    def preparar_sbert(self):
        if self.modelo is None:
            from sentence_transformers import SentenceTransformer
            self.modelo = SentenceTransformer(config.MODELO_EMBEDDINGS)
            self.modelo.max_seq_length = config.LONGITUD_MAXIMA_MODELO

    def ajustar(self, textos):
        if self.backend == "sbert":
            self.preparar_sbert()
            return self.codificar(textos, progreso=True)
        vectorizador = TfidfVectorizer(analyzer=tokenizar, sublinear_tf=True, min_df=1)
        matriz = vectorizador.fit_transform(textos)
        dimensiones = max(2, min(config.DIM_LSA, matriz.shape[0] - 1, matriz.shape[1] - 1))
        reductor = TruncatedSVD(n_components=dimensiones, random_state=0)
        vectores = reductor.fit_transform(matriz)
        self.modelo = make_pipeline(vectorizador, reductor)
        joblib.dump(self.modelo, config.INDICE_LSA)
        return normalize(vectores).astype("float32")

    def cargar(self):
        if self.backend == "sbert":
            self.preparar_sbert()
        else:
            self.modelo = joblib.load(config.INDICE_LSA)
        return self

    def codificar(self, textos, progreso=False):
        if self.backend == "sbert":
            vectores = self.modelo.encode(list(textos), batch_size=32, normalize_embeddings=True,
                                          convert_to_numpy=True, show_progress_bar=progreso)
            return np.asarray(vectores, dtype="float32")
        return normalize(self.modelo.transform(list(textos))).astype("float32")


class IndiceSemantico:
    def __init__(self):
        self.ids = []
        self.vectores = None
        self.codificador = None
        self.faiss = None
        self.indice_faiss = None
        self.meta = {}

    def construir(self, ids, textos):
        config.INDICES.mkdir(parents=True, exist_ok=True)
        backend = elegir_backend()
        self.ids = list(ids)
        self.codificador = Codificador(backend)
        self.vectores = np.ascontiguousarray(self.codificador.ajustar(list(textos)), dtype="float32")
        self.faiss = cargar_faiss()
        if self.faiss is not None:
            self.indice_faiss = self.faiss.IndexFlatIP(int(self.vectores.shape[1]))
            self.indice_faiss.add(self.vectores)
        self.meta = {
            "backend": backend,
            "modelo": config.MODELO_EMBEDDINGS if backend == "sbert" else "TF-IDF + SVD truncada (LSA)",
            "dimensiones": int(self.vectores.shape[1]),
            "documentos": len(self.ids),
            "motor_vectorial": "FAISS IndexFlatIP" if self.faiss is not None else "NumPy (producto punto exacto)",
            "ids": self.ids
        }
        return self

    def guardar(self):
        np.save(config.INDICE_VECTORES, self.vectores)
        if self.indice_faiss is not None:
            self.faiss.write_index(self.indice_faiss, str(config.INDICE_FAISS))
        elif config.INDICE_FAISS.exists():
            config.INDICE_FAISS.unlink()
        config.INDICE_META.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def cargar(cls):
        if not config.INDICE_META.exists() or not config.INDICE_VECTORES.exists():
            raise FileNotFoundError("No existe el indice semantico. Ejecuta: python main.py indexar")
        indice = cls()
        indice.meta = json.loads(config.INDICE_META.read_text(encoding="utf-8"))
        indice.ids = indice.meta["ids"]
        indice.vectores = np.load(config.INDICE_VECTORES)
        indice.codificador = Codificador(indice.meta["backend"]).cargar()
        indice.faiss = cargar_faiss()
        if indice.faiss is not None and config.INDICE_FAISS.exists():
            indice.indice_faiss = indice.faiss.read_index(str(config.INDICE_FAISS))
        return indice

    def buscar(self, consulta, permitidos=None):
        vector = np.ascontiguousarray(self.codificador.codificar([consulta]), dtype="float32")
        if not np.any(vector):
            return []
        if self.indice_faiss is not None:
            similitudes, posiciones = self.indice_faiss.search(vector, len(self.ids))
            pares = zip(posiciones[0].tolist(), similitudes[0].tolist())
        else:
            similitudes = self.vectores @ vector[0]
            orden = np.argsort(-similitudes, kind="stable")
            pares = zip(orden.tolist(), similitudes[orden].tolist())
        return [(self.ids[p], float(s)) for p, s in pares
                if p >= 0 and (permitidos is None or self.ids[p] in permitidos)]
