import json
import time

import config
from indexacion.lexico import IndiceLexico
from indexacion.semantico import IndiceSemantico
from procesamiento import almacen


def texto_lexico(oferta):
    return f"{oferta['titulo']} {oferta['titulo']} {oferta['empresa']} {' '.join(oferta['tecnologias'])} {oferta['descripcion']}"


def texto_semantico(oferta):
    partes = [oferta["titulo"]]
    if oferta["nivel"] != "no especificado":
        partes.append(f"Nivel {oferta['nivel']}")
    if oferta["modalidad"] != "no especificada":
        partes.append(f"Modalidad {oferta['modalidad']}")
    if oferta["tecnologias"]:
        partes.append("Tecnologias: " + ", ".join(oferta["tecnologias"][:12]))
    partes.append(oferta["descripcion"].replace("\n", " ")[:2000])
    return ". ".join(partes)


def indexar():
    ofertas = almacen.cargar()
    ids = [o["id"] for o in ofertas]
    inicio = time.time()
    lexico = IndiceLexico().construir(ids, [texto_lexico(o) for o in ofertas])
    lexico.guardar()
    t_lexico = time.time() - inicio
    print(f"Indice lexico: {len(ids)} documentos, {len(lexico.postings)} terminos, "
          f"{sum(len(p) for p in lexico.postings.values())} postings ({t_lexico:.1f} s)")
    inicio = time.time()
    semantico = IndiceSemantico().construir(ids, [texto_semantico(o) for o in ofertas])
    semantico.meta["lexico"] = {
        "documentos": len(ids),
        "terminos": len(lexico.postings),
        "postings": sum(len(p) for p in lexico.postings.values()),
        "longitud_promedio": round(lexico.promedio, 1),
        "modelo": f"BM25 (k1={config.BM25_K1}, b={config.BM25_B})"
    }
    semantico.guardar()
    print(f"Indice semantico: {semantico.meta['modelo']}, {semantico.meta['dimensiones']} dimensiones, "
          f"{semantico.meta['motor_vectorial']} ({time.time() - inicio:.1f} s)")
    print(f"Indices guardados en {config.INDICES}")
    return semantico.meta
