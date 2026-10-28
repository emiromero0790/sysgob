import json
from collections import Counter
from statistics import mean, median

import config
from procesamiento import almacen
from procesamiento.limpieza import tokenizar


def conteo(ofertas, campo):
    return dict(Counter(o[campo] or "sin dato" for o in ofertas).most_common())


def analizar():
    ofertas = almacen.cargar()
    longitudes, frecuencia_documental, tecnologias, meses = [], Counter(), Counter(), Counter()
    for oferta in ofertas:
        tokens = tokenizar(f"{oferta['titulo']} {oferta['descripcion']}")
        longitudes.append(len(tokens))
        frecuencia_documental.update(set(tokens))
        tecnologias.update(oferta["tecnologias"])
        if oferta["fecha_publicacion"]:
            meses[oferta["fecha_publicacion"][:7]] += 1
    estadisticas = {
        "total": len(ofertas),
        "empresas": len({o["empresa"] for o in ofertas if o["empresa"]}),
        "por_fuente": conteo(ofertas, "fuente"),
        "por_modalidad": conteo(ofertas, "modalidad"),
        "por_nivel": conteo(ofertas, "nivel"),
        "por_area": conteo(ofertas, "area"),
        "por_idioma": conteo(ofertas, "idioma"),
        "por_mes": dict(sorted(meses.items())),
        "tecnologias": dict(tecnologias.most_common()),
        "sin_tecnologias": sum(1 for o in ofertas if not o["tecnologias"]),
        "longitud_media": round(mean(longitudes), 1) if longitudes else 0,
        "longitud_mediana": median(longitudes) if longitudes else 0,
        "vocabulario": len(frecuencia_documental),
        "terminos_frecuentes": [[t, n] for t, n in frecuencia_documental.most_common(25)]
    }
    if config.RESUMEN_PROCESO.exists():
        estadisticas["proceso"] = json.loads(config.RESUMEN_PROCESO.read_text(encoding="utf-8"))
    config.ANALISIS.mkdir(parents=True, exist_ok=True)
    config.ESTADISTICAS.write_text(json.dumps(estadisticas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ofertas: {estadisticas['total']}  |  empresas: {estadisticas['empresas']}  |  "
          f"vocabulario: {estadisticas['vocabulario']} terminos  |  longitud media: {estadisticas['longitud_media']} terminos")
    for titulo, campo in (("Fuente", "por_fuente"), ("Modalidad", "por_modalidad"), ("Nivel", "por_nivel"), ("Area", "por_area")):
        print(f"{titulo}: " + ", ".join(f"{k} {v}" for k, v in estadisticas[campo].items()))
    print("Tecnologias mas pedidas: " + ", ".join(f"{k} {v}" for k, v in list(estadisticas["tecnologias"].items())[:12]))
    print(f"Guardado en {config.ESTADISTICAS}")
    return estadisticas
