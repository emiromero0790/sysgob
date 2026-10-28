import json

import config
from procesamiento import almacen, entidades
from procesamiento.duplicados import quitar_casi_duplicados, quitar_exactos
from procesamiento.exportar import exportar
from procesamiento.limpieza import html_a_texto, idioma


def leer_crudos():
    if not config.CRUDO.exists():
        return []
    carpetas = sorted(p.name for p in config.CRUDO.iterdir() if p.is_dir() and any(p.glob("*/*.json")))
    if len(carpetas) > 1 and "demo" in carpetas:
        carpetas.remove("demo")
        print("Hay datos reales: se ignoran las ofertas de demostracion.")
    crudos = {}
    for carpeta in carpetas:
        for ruta in sorted((config.CRUDO / carpeta).glob("*/*.json")):
            try:
                crudos[ruta.stem] = json.loads(ruta.read_text(encoding="utf-8"))
            except ValueError:
                continue
    return list(crudos.values())


def transformar(crudo):
    titulo = " ".join(html_a_texto(crudo.get("titulo", "")).split())
    descripcion = html_a_texto(crudo.get("descripcion_html", ""))
    etiquetas = " ".join(crudo.get("etiquetas") or [])
    tecnologias = entidades.tecnologias(f"{titulo}\n{descripcion}\n{etiquetas}")
    return {
        "id": crudo["id"],
        "fuente": crudo.get("fuente", ""),
        "url": crudo.get("url", ""),
        "titulo": titulo,
        "empresa": " ".join((crudo.get("empresa") or "").split()),
        "ubicacion": " ".join((crudo.get("ubicacion") or "").split()),
        "modalidad": entidades.modalidad(titulo, descripcion, crudo.get("modalidad_origen", "")),
        "nivel": entidades.nivel(titulo, descripcion, crudo.get("nivel_origen", "")),
        "area": entidades.area(titulo, tecnologias),
        "tecnologias": tecnologias,
        "idioma": idioma(descripcion),
        "fecha_publicacion": crudo.get("fecha_publicacion", ""),
        "fecha_extraccion": crudo.get("fecha_extraccion", ""),
        "descripcion": descripcion
    }


def procesar():
    crudos = leer_crudos()
    if not crudos:
        raise FileNotFoundError("No hay ofertas crudas. Ejecuta primero: python main.py acopio  (o python main.py demo)")
    ofertas = [transformar(c) for c in crudos]
    con_texto = [o for o in ofertas if o["titulo"] and len(o["descripcion"]) >= 80]
    sin_exactos, exactos = quitar_exactos(con_texto)
    finales, casi = quitar_casi_duplicados(sin_exactos)
    finales.sort(key=lambda o: (o["fecha_publicacion"], o["id"]), reverse=True)
    almacen.guardar(finales)
    exportar(finales)
    resumen = {
        "crudas": len(crudos),
        "sin_texto_suficiente": len(ofertas) - len(con_texto),
        "duplicados_exactos": exactos,
        "casi_duplicados": casi,
        "finales": len(finales)
    }
    config.RESUMEN_PROCESO.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Crudas: {resumen['crudas']}  |  sin texto: {resumen['sin_texto_suficiente']}  |  "
          f"duplicados exactos: {exactos}  |  casi duplicados: {casi}  |  finales: {resumen['finales']}")
    print(f"Guardado en {config.CSV_OFERTAS} y {config.BD}")
    return resumen
