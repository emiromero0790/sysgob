import csv
import sqlite3

import config

CAMPOS = ["id", "fuente", "url", "titulo", "empresa", "ubicacion", "modalidad", "nivel", "area",
          "tecnologias", "idioma", "fecha_publicacion", "fecha_extraccion", "descripcion"]
FILTROS_SIMPLES = ["modalidad", "nivel", "fuente", "area", "idioma"]


def empacar(lista):
    return "|" + "|".join(lista) + "|" if lista else ""


def desempacar(texto):
    return [t for t in (texto or "").split("|") if t]


def guardar(ofertas):
    config.PROCESADO.mkdir(parents=True, exist_ok=True)
    filas = [{**o, "tecnologias": empacar(o["tecnologias"])} for o in ofertas]
    with open(config.CSV_OFERTAS, "w", newline="", encoding="utf-8") as salida:
        escritor = csv.DictWriter(salida, fieldnames=CAMPOS, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)
    conexion = sqlite3.connect(config.BD)
    with conexion:
        conexion.execute("DROP TABLE IF EXISTS ofertas")
        columnas = ", ".join(f"{c} TEXT" + (" PRIMARY KEY" if c == "id" else "") for c in CAMPOS)
        conexion.execute(f"CREATE TABLE ofertas ({columnas})")
        marcas = ", ".join("?" for _ in CAMPOS)
        conexion.executemany(f"INSERT INTO ofertas VALUES ({marcas})", [[f[c] for c in CAMPOS] for f in filas])
        for campo in FILTROS_SIMPLES:
            conexion.execute(f"CREATE INDEX idx_{campo} ON ofertas ({campo})")
    conexion.close()


def cargar():
    if not config.BD.exists():
        raise FileNotFoundError("No existe la base de datos procesada. Ejecuta: python main.py procesar")
    conexion = sqlite3.connect(config.BD)
    conexion.row_factory = sqlite3.Row
    filas = [dict(f) for f in conexion.execute("SELECT * FROM ofertas")]
    conexion.close()
    for fila in filas:
        fila["tecnologias"] = desempacar(fila["tecnologias"])
    return filas


def ids_filtrados(filtros):
    condiciones, valores = [], []
    for campo in FILTROS_SIMPLES:
        if filtros.get(campo):
            condiciones.append(f"{campo} = ?")
            valores.append(filtros[campo])
    for tecnologia in filtros.get("tecnologias") or []:
        condiciones.append("tecnologias LIKE ?")
        valores.append(f"%|{tecnologia}|%")
    if not condiciones:
        return None
    conexion = sqlite3.connect(config.BD)
    ids = {f[0] for f in conexion.execute("SELECT id FROM ofertas WHERE " + " AND ".join(condiciones), valores)}
    conexion.close()
    return ids
