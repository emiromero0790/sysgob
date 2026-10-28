import json

import config
from busqueda.motor import MODOS, Motor
from evaluacion.metricas import ndcg_k, precision_k, precision_promedio, recall_k


def cumple(oferta, criterios):
    for campo in ("area", "nivel", "modalidad"):
        if campo in criterios and oferta[campo] not in criterios[campo]:
            return False
    tecnologias = set(oferta["tecnologias"])
    if not set(criterios.get("tecnologias_todas", [])) <= tecnologias:
        return False
    if "tecnologias_alguna" in criterios and not tecnologias & set(criterios["tecnologias_alguna"]):
        return False
    return True


def evaluar():
    motor = Motor()
    k = config.CORTE_EVALUACION
    consultas = json.loads(config.CONSULTAS_EVALUACION.read_text(encoding="utf-8"))
    filas, omitidas = [], []
    for entrada in consultas:
        relevantes = {i for i, o in motor.ofertas.items() if cumple(o, entrada["criterios"])}
        if not relevantes:
            omitidas.append(entrada["consulta"])
            continue
        fila = {"consulta": entrada["consulta"], "relevantes": len(relevantes)}
        for modo in MODOS:
            ranking = [i for i, *_ in motor.ranking(entrada["consulta"], modo)]
            fila[modo] = {
                "precision": round(precision_k(ranking, relevantes, k), 4),
                "recall": round(recall_k(ranking, relevantes, k), 4),
                "map": round(precision_promedio(ranking, relevantes), 4),
                "ndcg": round(ndcg_k(ranking, relevantes, k), 4)
            }
        filas.append(fila)
    promedio = {
        modo: {m: round(sum(f[modo][m] for f in filas) / len(filas), 4) for m in ("precision", "recall", "map", "ndcg")}
        for modo in MODOS
    } if filas else {}
    resultados = {
        "corte": k,
        "embeddings": motor.semantico.meta["modelo"],
        "documentos": len(motor.ofertas),
        "consultas_evaluadas": len(filas),
        "consultas_omitidas": omitidas,
        "promedio": promedio,
        "detalle": filas
    }
    config.EVALUACION.mkdir(parents=True, exist_ok=True)
    config.RESULTADOS_EVALUACION.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Consultas evaluadas: {len(filas)}  (omitidas sin documentos relevantes: {len(omitidas)})")
    print(f"{'Modo':<12}{'P@' + str(k):>9}{'R@' + str(k):>9}{'MAP':>9}{'nDCG@' + str(k):>10}")
    for modo, valores in promedio.items():
        print(f"{modo:<12}{valores['precision']:>9.3f}{valores['recall']:>9.3f}{valores['map']:>9.3f}{valores['ndcg']:>10.3f}")
    print(f"Guardado en {config.RESULTADOS_EVALUACION}")
    return resultados
