"""Vectorización explícita del corpus.

Además del índice semántico (Sentence-Transformers + FAISS), el proyecto deja
guardada la matriz TF-IDF dispersa y un resumen de su estructura para poder
explicar cómo se convierte cada palabra en un número.
"""

import gzip
import json

import numpy as np
from scipy.sparse import save_npz
from sklearn.feature_extraction.text import TfidfVectorizer

import config
from procesamiento.limpieza import tokenizar


def texto_lexico(oferta):
    return (
        f"{oferta['titulo']} {oferta['titulo']} {oferta['empresa']} "
        f"{' '.join(oferta['tecnologias'])} {oferta['descripcion']}"
    )


def _vector_ejemplo(matriz, vocabulario, ids, ofertas, posicion=0):
    fila = matriz.getrow(posicion)
    inverso = {indice: termino for termino, indice in vocabulario.items()}
    componentes = sorted(
        ((inverso[i], float(v)) for i, v in zip(fila.indices, fila.data)),
        key=lambda par: -par[1],
    )
    return {
        "id": ids[posicion],
        "titulo": ofertas[posicion]["titulo"],
        "dimensiones": int(matriz.shape[1]),
        "componentes_no_cero": int(fila.nnz),
        "densidad_pct": round(100 * fila.nnz / max(1, matriz.shape[1]), 2),
        "componentes": [[t, round(v, 4)] for t, v in componentes[:18]],
    }


def _postings_ejemplo(termino="python", limite=6):
    if not config.INDICE_LEXICO.exists():
        return {}
    try:
        with gzip.open(config.INDICE_LEXICO, "rt", encoding="utf-8") as entrada:
            datos = json.load(entrada)
    except (OSError, ValueError):
        return {}
    postings = datos.get("postings", {}).get(termino)
    if not postings:
        return {}
    ids = datos.get("ids", [])
    return {
        "termino": termino,
        "documentos": [[ids[p], f] for p, f in postings[:limite]],
        "total_documentos": len(postings),
        "idf": round(datos.get("idf", {}).get(termino, 0.0), 4),
    }


def construir_estructura(ofertas, meta_semantico=None):
    textos = [texto_lexico(o) for o in ofertas]
    ids = [o["id"] for o in ofertas]
    vectorizador = TfidfVectorizer(
        analyzer=tokenizar, sublinear_tf=True, min_df=1, norm="l2", dtype=np.float32
    )
    matriz = vectorizador.fit_transform(textos).tocsr()
    vocabulario = vectorizador.vocabulary_
    idf = vectorizador.idf_

    config.INDICES.mkdir(parents=True, exist_ok=True)
    save_npz(config.INDICE_TFIDF, matriz)

    documentos_por_termino = np.asarray((matriz > 0).sum(axis=0)).ravel()
    terminos = [
        {
            "termino": termino,
            "indice": int(indice),
            "df": int(documentos_por_termino[indice]),
            "idf": round(float(idf[indice]), 4),
        }
        for termino, indice in vocabulario.items()
    ]
    terminos.sort(key=lambda t: (-t["df"], t["termino"]))
    with gzip.open(config.INDICE_VOCABULARIO, "wt", encoding="utf-8") as salida:
        json.dump({
            "dimensiones": len(vocabulario),
            "documentos": len(ids),
            "terminos": terminos,
            "ids": ids,
        }, salida, ensure_ascii=False)

    meta_semantico = meta_semantico or {}
    vectores = None
    if config.INDICE_VECTORES.exists():
        try:
            vectores = np.load(config.INDICE_VECTORES)
        except (OSError, ValueError):
            vectores = None
    embedding_ejemplo = {}
    if vectores is not None and len(vectores):
        embedding_ejemplo = {
            "dimensiones": int(vectores.shape[1]),
            "valores": [round(float(v), 4) for v in vectores[0][:16]],
            "norma": round(float(np.linalg.norm(vectores[0])), 4),
            "tipo": "float32 L2-normalizado",
        }

    estructura = {
        "matriz": {
            "modelo": "TF-IDF con sublinear_tf y norma L2",
            "formato": "scipy.sparse.csr_matrix",
            "archivo": str(config.INDICE_TFIDF.relative_to(config.BASE)),
            "documentos": int(matriz.shape[0]),
            "dimensiones": int(matriz.shape[1]),
            "valores_no_cero": int(matriz.nnz),
            "densidad_pct": round(100 * matriz.nnz / max(1, matriz.shape[0] * matriz.shape[1]), 2),
            "celdas_totales": int(matriz.shape[0] * matriz.shape[1]),
            "tfidf_medio": round(float(matriz.data.mean()), 4) if matriz.nnz else 0,
            "tfidf_maximo": round(float(matriz.data.max()), 4) if matriz.nnz else 0,
        },
        "vocabulario": {
            "terminos": len(vocabulario),
            "archivo": str(config.INDICE_VOCABULARIO.relative_to(config.BASE)),
            "muestra": terminos[:40],
        },
        "vector_ejemplo": _vector_ejemplo(matriz, vocabulario, ids, ofertas),
        "indice_invertido": _postings_ejemplo(),
        "embeddings": {
            **(meta_semantico or {}),
            "ids": None,
            "ejemplo": embedding_ejemplo,
            "metrica": "similitud coseno (producto punto sobre vectores normalizados)",
        },
        "esquema": [
            {"nombre": "Índice invertido", "estructura": "término → [[documento, frecuencia]]", "uso": "BM25 léxico"},
            {"nombre": "Matriz TF-IDF", "estructura": "CSR dispersa documentos × términos", "uso": "vectorización clásica"},
            {"nombre": "Embeddings", "estructura": "matriz densa documentos × 384 float32", "uso": "similitud semántica"},
            {"nombre": "FAISS", "estructura": "IndexFlatIP sobre vectores normalizados", "uso": "búsqueda vectorial rápida"},
        ],
        "generado": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    if isinstance(estructura["embeddings"].get("ids"), list):
        estructura["embeddings"].pop("ids", None)
    config.INDICE_ESTRUCTURA.write_text(
        json.dumps(estructura, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Vectorización: matriz {matriz.shape[0]}×{matriz.shape[1]} "
        f"({matriz.nnz} valores no cero), vocabulario {len(vocabulario)} términos"
    )
    return estructura
