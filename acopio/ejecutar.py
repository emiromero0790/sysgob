import config
from acopio.arbeitnow import Arbeitnow
from acopio.demo import Demo
from acopio.getonboard import GetOnBoard
from acopio.manual import Manual
from acopio.remotive import Remotive
from acopio.sitio_html import SitioHTML


def catalogo():
    fuentes = {
        "getonboard": GetOnBoard,
        "remotive": Remotive,
        "arbeitnow": Arbeitnow,
        "manual": Manual,
        "demo": Demo
    }
    for sitio in config.SITIOS_HTML:
        fuentes[sitio["nombre"]] = lambda limite=None, s=sitio: SitioHTML(s, limite)
    return fuentes


def acopiar(nombres=None, limite=None):
    fuentes = catalogo()
    nombres = nombres or config.FUENTES_POR_DEFECTO
    resumenes = []
    for nombre in nombres:
        if nombre not in fuentes:
            print(f"Fuente desconocida: {nombre}. Disponibles: {', '.join(fuentes)}")
            continue
        print(f"Acopiando {nombre}...")
        resumen = fuentes[nombre](limite).ejecutar()
        resumenes.append(resumen)
        print(f"  nuevas: {resumen['nuevas']}  ya guardadas: {resumen['ya_guardadas']}  "
              f"peticiones: {resumen['peticiones']}  errores: {resumen['errores']}  "
              f"tiempo: {resumen['segundos']} s")
    total = sum(r["nuevas"] for r in resumenes)
    print(f"Acopio terminado: {total} ofertas nuevas en {config.CRUDO}")
    return resumenes
