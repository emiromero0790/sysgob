import csv
import sqlite3

import config

CAMPOS = ["id", "fuente", "url", "titulo", "empresa", "ubicacion", "modalidad", "nivel", "area",
          "tecnologias", "idioma", "fecha_publicacion", "fecha_extraccion", "descripcion"]
FILTROS_SIMPLES = ["modalidad", "nivel", "fuente", "area", "idioma"]

ESQUEMA_RELACIONAL = {
    "fuentes": [("id", "INTEGER", "PK"), ("nombre", "TEXT", "UNIQUE")],
    "empresas": [("id", "INTEGER", "PK"), ("nombre", "TEXT", "UNIQUE")],
    "tecnologias": [("id", "INTEGER", "PK"), ("nombre", "TEXT", "UNIQUE")],
    "ofertas": [
        ("id", "TEXT", "PK"), ("fuente_id", "INTEGER", "FK"), ("empresa_id", "INTEGER", "FK"),
        ("url", "TEXT", ""), ("titulo", "TEXT", ""), ("ubicacion", "TEXT", ""),
        ("modalidad", "TEXT", ""), ("nivel", "TEXT", ""), ("area", "TEXT", ""),
        ("idioma", "TEXT", ""), ("fecha_publicacion", "TEXT", ""),
        ("fecha_extraccion", "TEXT", ""), ("descripcion", "TEXT", ""),
    ],
    "oferta_tecnologia": [("oferta_id", "TEXT", "PK/FK"), ("tecnologia_id", "INTEGER", "PK/FK"), ("posicion", "INTEGER", "")],
}


def empacar(lista):
    return "|" + "|".join(lista) + "|" if lista else ""


def desempacar(texto):
    return [t for t in (texto or "").split("|") if t]


def _ids(conexion, tabla, valores):
    valores = sorted({v for v in valores if v})
    conexion.executemany(f"INSERT OR IGNORE INTO {tabla} (nombre) VALUES (?)", [(v,) for v in valores])
    return {nombre: identificador for identificador, nombre in conexion.execute(f"SELECT id, nombre FROM {tabla}")}


def _crear_esquema(conexion):
    conexion.executescript(
        """
        DROP VIEW IF EXISTS vista_ofertas;
        DROP TABLE IF EXISTS oferta_tecnologia;
        DROP TABLE IF EXISTS ofertas;
        DROP TABLE IF EXISTS tecnologias;
        DROP TABLE IF EXISTS empresas;
        DROP TABLE IF EXISTS fuentes;

        CREATE TABLE fuentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        );
        CREATE TABLE empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        );
        CREATE TABLE tecnologias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        );
        CREATE TABLE ofertas (
            id TEXT PRIMARY KEY,
            fuente_id INTEGER REFERENCES fuentes(id),
            empresa_id INTEGER REFERENCES empresas(id),
            url TEXT,
            titulo TEXT,
            ubicacion TEXT,
            modalidad TEXT,
            nivel TEXT,
            area TEXT,
            idioma TEXT,
            fecha_publicacion TEXT,
            fecha_extraccion TEXT,
            descripcion TEXT
        );
        CREATE TABLE oferta_tecnologia (
            oferta_id TEXT NOT NULL REFERENCES ofertas(id),
            tecnologia_id INTEGER NOT NULL REFERENCES tecnologias(id),
            posicion INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (oferta_id, tecnologia_id)
        );
        CREATE INDEX idx_ofertas_modalidad ON ofertas (modalidad);
        CREATE INDEX idx_ofertas_nivel ON ofertas (nivel);
        CREATE INDEX idx_ofertas_area ON ofertas (area);
        CREATE INDEX idx_ofertas_idioma ON ofertas (idioma);
        CREATE INDEX idx_ofertas_fecha ON ofertas (fecha_publicacion);
        CREATE INDEX idx_ofertas_fuente ON ofertas (fuente_id);
        CREATE INDEX idx_ot_tecnologia ON oferta_tecnologia (tecnologia_id);

        CREATE VIEW vista_ofertas AS
        SELECT o.id, f.nombre AS fuente, o.url, o.titulo, COALESCE(e.nombre, '') AS empresa,
               o.ubicacion, o.modalidad, o.nivel, o.area, o.idioma,
               o.fecha_publicacion, o.fecha_extraccion, o.descripcion,
               COALESCE((
                   SELECT group_concat(t.nombre, '|')
                   FROM oferta_tecnologia ot
                   JOIN tecnologias t ON t.id = ot.tecnologia_id
                   WHERE ot.oferta_id = o.id
                   ORDER BY ot.posicion
               ), '') AS tecnologias
        FROM ofertas o
        LEFT JOIN fuentes f ON f.id = o.fuente_id
        LEFT JOIN empresas e ON e.id = o.empresa_id;
        """
    )


def guardar(ofertas):
    config.PROCESADO.mkdir(parents=True, exist_ok=True)
    filas = [{**o, "tecnologias": empacar(o["tecnologias"])} for o in ofertas]
    with open(config.CSV_OFERTAS, "w", newline="", encoding="utf-8") as salida:
        escritor = csv.DictWriter(salida, fieldnames=CAMPOS, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)

    conexion = sqlite3.connect(config.BD)
    try:
        with conexion:
            _crear_esquema(conexion)
            fuentes = _ids(conexion, "fuentes", [o.get("fuente", "") for o in ofertas])
            empresas = _ids(conexion, "empresas", [o.get("empresa", "") for o in ofertas])
            tecnologias = _ids(
                conexion, "tecnologias",
                [t for o in ofertas for t in (o.get("tecnologias") or [])]
            )
            conexion.executemany(
                """INSERT INTO ofertas
                   (id, fuente_id, empresa_id, url, titulo, ubicacion, modalidad, nivel, area,
                    idioma, fecha_publicacion, fecha_extraccion, descripcion)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        o["id"], fuentes.get(o.get("fuente")), empresas.get(o.get("empresa")),
                        o.get("url", ""), o.get("titulo", ""), o.get("ubicacion", ""),
                        o.get("modalidad", ""), o.get("nivel", ""), o.get("area", ""),
                        o.get("idioma", ""), o.get("fecha_publicacion", ""),
                        o.get("fecha_extraccion", ""), o.get("descripcion", ""),
                    )
                    for o in ofertas
                ],
            )
            relaciones = []
            for oferta in ofertas:
                for posicion, tecnologia in enumerate(oferta.get("tecnologias") or []):
                    identificador = tecnologias.get(tecnologia)
                    if identificador is not None:
                        relaciones.append((oferta["id"], identificador, posicion))
            conexion.executemany(
                "INSERT OR IGNORE INTO oferta_tecnologia (oferta_id, tecnologia_id, posicion) VALUES (?, ?, ?)",
                relaciones,
            )
    finally:
        conexion.close()


def cargar():
    if not config.BD.exists():
        raise FileNotFoundError("No existe la base de datos procesada. Ejecuta: python main.py procesar")
    conexion = sqlite3.connect(config.BD)
    conexion.row_factory = sqlite3.Row
    try:
        columnas = {f[1] for f in conexion.execute("PRAGMA table_info(ofertas)")}
        if "fuente_id" not in columnas:
            # Compatibilidad con bases creadas por versiones anteriores.
            filas = [dict(f) for f in conexion.execute("SELECT * FROM ofertas")]
            for fila in filas:
                fila["tecnologias"] = desempacar(fila["tecnologias"])
            return filas
        filas = [dict(f) for f in conexion.execute(
            """SELECT o.id, COALESCE(f.nombre, '') AS fuente, o.url, o.titulo,
                      COALESCE(e.nombre, '') AS empresa, o.ubicacion, o.modalidad, o.nivel,
                      o.area, o.idioma, o.fecha_publicacion, o.fecha_extraccion, o.descripcion
               FROM ofertas o
               LEFT JOIN fuentes f ON f.id = o.fuente_id
               LEFT JOIN empresas e ON e.id = o.empresa_id"""
        )]
        tecnologias = {fila["id"]: [] for fila in filas}
        for oferta_id, nombre in conexion.execute(
            """SELECT ot.oferta_id, t.nombre
               FROM oferta_tecnologia ot
               JOIN tecnologias t ON t.id = ot.tecnologia_id
               ORDER BY ot.oferta_id, ot.posicion"""
        ):
            tecnologias.setdefault(oferta_id, []).append(nombre)
        for fila in filas:
            fila["tecnologias"] = tecnologias.get(fila["id"], [])
        return filas
    finally:
        conexion.close()


def ids_filtrados(filtros):
    condiciones, valores = [], []
    for campo in FILTROS_SIMPLES:
        if filtros.get(campo):
            columna = "f.nombre" if campo == "fuente" else f"o.{campo}"
            condiciones.append(f"{columna} = ?")
            valores.append(filtros[campo])
    tecnologias = [t for t in filtros.get("tecnologias") or [] if t]
    if tecnologias:
        marcas = ", ".join("?" for _ in tecnologias)
        condiciones.append(
            f"""o.id IN (
                SELECT ot.oferta_id FROM oferta_tecnologia ot
                JOIN tecnologias t ON t.id = ot.tecnologia_id
                WHERE t.nombre IN ({marcas})
                GROUP BY ot.oferta_id
                HAVING COUNT(DISTINCT t.nombre) = ?
            )"""
        )
        valores.extend(tecnologias)
        valores.append(len(set(tecnologias)))
    if not condiciones:
        return None
    conexion = sqlite3.connect(config.BD)
    try:
        filas = conexion.execute(
            "SELECT o.id FROM ofertas o LEFT JOIN fuentes f ON f.id = o.fuente_id WHERE " + " AND ".join(condiciones),
            valores,
        )
        return {f[0] for f in filas}
    finally:
        conexion.close()


def conteos():
    """Conteos rápidos para la vista de datos y el esquema relacional."""
    if not config.BD.exists():
        return {}
    conexion = sqlite3.connect(config.BD)
    try:
        tablas = [f[0] for f in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        return {tabla: conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] for tabla in tablas}
    finally:
        conexion.close()
