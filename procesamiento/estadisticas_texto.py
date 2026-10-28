"""Estadísticas del contenido textual del corpus.

Produce un JSON con frecuencias de palabras, n-gramas, palabras vacías,
longitudes, ejemplos del pipeline y una muestra "antes / después" que la
interfaz web utiliza para explicar el preprocesamiento.
"""

import json
from collections import Counter
from statistics import mean, median

import config
from procesamiento import almacen
from procesamiento.lematizador import derivar, ejemplos_lematizacion, lematizar
from procesamiento.limpieza import (
    STOPWORDS,
    limpiar_texto,
    ngramas,
    normalizar,
    palabras,
    tokenizar,
    tokenizar_detalle,
)


def texto_oferta(oferta):
    tecnologias = " ".join(oferta.get("tecnologias") or [])
    return f"{oferta.get('titulo', '')}\n{oferta.get('descripcion', '')}\n{tecnologias}"


def _recorte(texto, limite=620):
    texto = (texto or "").strip()
    return texto if len(texto) <= limite else texto[:limite].rstrip() + "…"


def _muestra(oferta):
    texto = texto_oferta(oferta)
    detalle = tokenizar_detalle(texto)
    utiles = [d for d in detalle if not d["vacia"]]
    lemas = [d["lema"] for d in utiles]
    derivadas = [d["derivada"] for d in utiles]
    return {
        "id": oferta["id"],
        "titulo": oferta["titulo"],
        "idioma": oferta.get("idioma", ""),
        "original": _recorte(f"{oferta['titulo']}\n{oferta['descripcion']}"),
        "limpio": _recorte(limpiar_texto(f"{oferta['titulo']} {oferta['descripcion']}")),
        "normalizado": _recorte(normalizar(limpiar_texto(f"{oferta['titulo']} {oferta['descripcion']}"))),
        "detalle": detalle[:22],
        "lemas": lemas[:36],
        "derivadas": derivadas[:36],
        "ngramas": [g for g in ngramas(lemas, 2)][:10],
        "estadisticas": {
            "tokens_brutos": len(detalle),
            "tokens_utiles": len(utiles),
            "palabras_vacias": len(detalle) - len(utiles),
            "tipos": len(set(lemas)),
            "caracteres_original": len(texto),
            "caracteres_limpio": len(limpiar_texto(texto)),
        },
    }


def analizar_texto(ofertas=None, limite_muestras=4):
    ofertas = ofertas or almacen.cargar()
    if not ofertas:
        raise FileNotFoundError("No hay ofertas procesadas. Ejecuta: python main.py procesar")

    frecuencia = Counter()
    frecuencia_documental = Counter()
    frecuencia_derivada = Counter()
    derivada_documental = Counter()
    frecuencia_bruta = Counter()
    vacias = Counter()
    longitudes = []
    todas_palabras = []
    caracteres_original = caracteres_limpio = 0
    longitudes_palabra = Counter()
    ngramas_total = {str(n): Counter() for n in config.NGRAMAS}
    ngramas_documental = {str(n): Counter() for n in config.NGRAMAS}
    idiomas = Counter()
    tecnologias = Counter()

    for oferta in ofertas:
        texto = texto_oferta(oferta)
        crudo = palabras(texto)
        lemas = tokenizar(texto)
        derivadas = tokenizar(texto, "derivada")
        limpias = limpiar_texto(texto)

        longitudes.append(len(lemas))
        todas_palabras.extend(crudo)
        frecuencia.update(lemas)
        frecuencia_documental.update(set(lemas))
        frecuencia_derivada.update(derivadas)
        derivada_documental.update(set(derivadas))
        frecuencia_bruta.update(crudo)
        vacias.update(t for t in crudo if t in STOPWORDS)
        caracteres_original += len(texto)
        caracteres_limpio += len(limpias)
        idiomas[oferta.get("idioma") or "desconocido"] += 1
        tecnologias.update(oferta.get("tecnologias") or [])

        for token in crudo:
            longitudes_palabra[len(token)] += 1
        for n in config.NGRAMAS:
            gramos = ngramas(lemas, n)
            ngramas_total[str(n)].update(gramos)
            ngramas_documental[str(n)].update(set(gramos))

    resumen = {
        "documentos": len(ofertas),
        "tokens_brutos": sum(longitudes_palabra.values()),
        "tokens": sum(frecuencia.values()),
        "tipos": len(frecuencia),
        "hapax": sum(1 for v in frecuencia.values() if v == 1),
        "ttr": round(len(frecuencia) / max(1, sum(frecuencia.values())), 4),
        "palabras_vacias_distintas": len(vacias),
        "palabras_vacias_totales": sum(vacias.values()),
        "longitud_media": round(mean(longitudes), 1) if longitudes else 0,
        "longitud_mediana": median(longitudes) if longitudes else 0,
        "longitud_maxima": max(longitudes, default=0),
        "longitud_minima": min(longitudes, default=0),
        "longitud_palabra_media": round(
            sum(l * n for l, n in longitudes_palabra.items()) / max(1, sum(longitudes_palabra.values())), 2
        ),
        "caracteres_original": caracteres_original,
        "caracteres_limpio": caracteres_limpio,
        "reduccion_caracteres": round(100 * (1 - caracteres_limpio / max(1, caracteres_original)), 1),
        "reduccion_tokens": round(
            100 * (1 - sum(frecuencia.values()) / max(1, sum(longitudes_palabra.values()))), 1
        ),
        "vocabulario_bruto": len(frecuencia_bruta),
        "vocabulario_lemas": len(frecuencia),
        "vocabulario_derivadas": len(frecuencia_derivada),
        "estrategia": config.ESTRATEGIA_TOKENS,
        "stopwords": len(STOPWORDS),
        "ngramas_distintos": {n: len(c) for n, c in ngramas_total.items()},
    }

    def top(contador, documental=None, limite=config.TOP_TERMINOS):
        filas = []
        for termino, total in contador.most_common(limite):
            df = documental[termino] if documental else total
            filas.append([termino, total, df])
        return filas

    # Muestras: una por idioma, priorizando descripciones largas, sin repetir.
    muestras, vistos = [], set()
    for oferta in sorted(ofertas, key=lambda o: len(o.get("descripcion") or ""), reverse=True):
        clave = oferta.get("idioma") or "desconocido"
        if clave in vistos:
            continue
        vistos.add(clave)
        muestras.append(_muestra(oferta))
        if len(muestras) >= limite_muestras:
            break

    pipeline = [
        {"id": "limpieza", "nombre": "Limpieza", "descripcion": "Quita HTML, URLs, correos, emojis, signos y números sueltos.",
         "detalle": f"{resumen['caracteres_original']:,} → {resumen['caracteres_limpio']:,} caracteres".replace(",", ".")},
        {"id": "normalizacion", "nombre": "Normalización", "descripcion": "Minúsculas, sin acentos, sin espacios dobles.",
         "detalle": "NFKD + minúsculas"},
        {"id": "tokenizacion", "nombre": "Tokenización", "descripcion": "Separa palabras conservando términos como c++, c#, node.js o ci/cd.",
         "detalle": f"{resumen['tokens_brutos']:,} tokens".replace(",", ".")},
        {"id": "vacias", "nombre": "Palabras vacías", "descripcion": "Elimina artículos, preposiciones y conectores en español e inglés.",
         "detalle": f"{resumen['palabras_vacias_totales']:,} eliminadas de {resumen['stopwords']} palabras".replace(",", ".")},
        {"id": "lematizacion", "nombre": "Lematización", "descripcion": "Reduce plurales, género y formas verbales a un lema común.",
         "detalle": f"{resumen['vocabulario_lemas']:,} lemas".replace(",", ".")},
        {"id": "derivacion", "nombre": "Derivación", "descripcion": "Calcula la raíz (stemming) como representación alternativa.",
         "detalle": f"{resumen['vocabulario_derivadas']:,} raíces".replace(",", ".")},
    ]

    datos = {
        "resumen": resumen,
        "pipeline": pipeline,
        "frecuencias": top(frecuencia, frecuencia_documental),
        "derivadas": top(frecuencia_derivada, derivada_documental, 45),
        "frecuencias_brutas": top(frecuencia_bruta, None, 30),
        "palabras_vacias": [[t, n] for t, n in vacias.most_common(24)],
        "ngramas": {
            n: [[g, total, ngramas_documental[n][g]] for g, total in contador.most_common(config.TOP_NGRAMAS)]
            for n, contador in ngramas_total.items()
        },
        "longitudes_palabra": dict(sorted(longitudes_palabra.items())),
        "tecnologias": dict(tecnologias.most_common(30)),
        "por_idioma": dict(idiomas.most_common()),
        "nube": [[t, n] for t, n in frecuencia.most_common(70)],
        "lematizacion": ejemplos_lematizacion(todas_palabras),
        "muestras": muestras,
        "generado": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    return datos


def analizar_y_guardar(ofertas=None):
    datos = analizar_texto(ofertas)
    config.ANALISIS.mkdir(parents=True, exist_ok=True)
    config.ANALISIS_TEXTO.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    r = datos["resumen"]
    print(
        f"Texto: {r['tokens']:,} tokens utiles, {r['tipos']:,} lemas, "
        f"{r['ngramas_distintos'].get('2', 0):,} bigramas distintos, "
        f"TTR {r['ttr']}, reduccion de tokens {r['reduccion_tokens']}%"
    )
    print(f"Guardado en {config.ANALISIS_TEXTO}")
    return datos
