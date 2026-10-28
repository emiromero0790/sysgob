import argparse
import sys

import config


def paso_acopio(args):
    from acopio.ejecutar import acopiar
    acopiar(args.fuentes, args.limite)


def paso_demo(args):
    from acopio.ejecutar import acopiar
    acopiar(["demo"], args.limite)


def paso_procesar(args):
    from procesamiento.pipeline import procesar
    procesar()


def paso_analizar(args):
    from procesamiento.analisis import analizar
    analizar()


def paso_indexar(args):
    from indexacion.construir import indexar
    indexar()


def paso_exportar(args):
    from procesamiento.exportar import exportar_todo
    exportar_todo()


def paso_evaluar(args):
    from evaluacion.evaluar import evaluar
    evaluar()


def paso_buscar(args):
    from busqueda.motor import Motor
    respuesta = Motor().buscar(" ".join(args.consulta), args.modo, k=args.k)
    print(f"{respuesta['total']} resultados para \"{respuesta['consulta']}\" (modo {respuesta['modo']})")
    for posicion, r in enumerate(respuesta["resultados"], start=1):
        print(f"{posicion:>2}. {r['relevancia']:>5}%  {r['titulo']}  |  {r['empresa']}  |  {r['modalidad']}  |  {r['fuente']}")


def paso_web(args):
    from web.app import crear_app
    app = crear_app()
    print(f"SysJobs en http://{config.SERVIDOR}:{args.puerto}")
    app.run(host=config.SERVIDOR, port=args.puerto, debug=False)


def paso_construir(args):
    paso_procesar(args)
    paso_analizar(args)
    paso_indexar(args)
    paso_evaluar(args)


def paso_todo(args):
    paso_acopio(args)
    paso_construir(args)


def principal():
    parser = argparse.ArgumentParser(prog="main.py", description="SysJobs: buscador semantico de empleo y practicas")
    comandos = parser.add_subparsers(dest="comando", required=True)

    for nombre, funcion in (("acopio", paso_acopio), ("todo", paso_todo)):
        p = comandos.add_parser(nombre)
        p.add_argument("--fuentes", nargs="+", default=None)
        p.add_argument("--limite", type=int, default=None)
        p.set_defaults(funcion=funcion)

    p = comandos.add_parser("demo")
    p.add_argument("--limite", type=int, default=None)
    p.set_defaults(funcion=paso_demo)

    for nombre, funcion in (("procesar", paso_procesar), ("analizar", paso_analizar), ("indexar", paso_indexar),
                            ("evaluar", paso_evaluar), ("exportar", paso_exportar), ("construir", paso_construir)):
        comandos.add_parser(nombre).set_defaults(funcion=funcion)

    p = comandos.add_parser("buscar")
    p.add_argument("consulta", nargs="+")
    p.add_argument("--modo", choices=["hibrido", "semantico", "lexico"], default="hibrido")
    p.add_argument("-k", type=int, default=10)
    p.set_defaults(funcion=paso_buscar)

    p = comandos.add_parser("web")
    p.add_argument("--puerto", type=int, default=config.PUERTO)
    p.set_defaults(funcion=paso_web)

    args = parser.parse_args()
    try:
        args.funcion(args)
    except FileNotFoundError as error:
        print(f"Falta un paso previo: {error}")
        sys.exit(1)


if __name__ == "__main__":
    principal()
