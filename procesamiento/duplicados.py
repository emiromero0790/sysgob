import hashlib

from sklearn.feature_extraction.text import TfidfVectorizer

import config
from procesamiento.limpieza import normalizar, tokenizar


def huella(oferta):
    base = normalizar(f"{oferta['titulo']}|{oferta['empresa']}|{oferta['descripcion'][:300]}")
    return hashlib.sha1(" ".join(base.split()).encode("utf-8")).hexdigest()


def quitar_exactos(ofertas):
    vistas, unicas = set(), []
    for oferta in ofertas:
        clave = huella(oferta)
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(oferta)
    return unicas, len(ofertas) - len(unicas)


def quitar_casi_duplicados(ofertas, umbral=None):
    umbral = umbral or config.UMBRAL_CASI_DUPLICADO
    if len(ofertas) < 2:
        return ofertas, 0
    textos = [f"{o['titulo']} {o['empresa']} {o['descripcion']}" for o in ofertas]
    matriz = TfidfVectorizer(analyzer=tokenizar).fit_transform(textos).tocsr()
    eliminadas = set()
    paso = 500
    for inicio in range(0, matriz.shape[0], paso):
        similitudes = (matriz[inicio:inicio + paso] @ matriz.T).tocoo()
        for fila, columna, valor in zip(similitudes.row, similitudes.col, similitudes.data):
            i = inicio + fila
            if columna < i and valor >= umbral and columna not in eliminadas:
                eliminadas.add(i)
    unicas = [o for i, o in enumerate(ofertas) if i not in eliminadas]
    return unicas, len(eliminadas)
