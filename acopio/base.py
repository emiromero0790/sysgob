import hashlib
import json
import time
from datetime import date, datetime, timezone
from urllib.parse import urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests

import config


def fecha_iso(valor):
    if valor in (None, ""):
        return ""
    if isinstance(valor, (int, float)):
        try:
            return datetime.fromtimestamp(valor, tz=timezone.utc).date().isoformat()
        except (ValueError, OSError, OverflowError):
            return ""
    texto = str(valor).strip()
    return texto[:10] if len(texto) >= 10 and texto[4] == "-" else ""


class Recolector:
    nombre = "base"
    respeta_robots = False

    def __init__(self, limite=None):
        self.limite = limite or config.LIMITE_POR_FUENTE
        self.sesion = requests.Session()
        self.sesion.headers.update({
            "User-Agent": config.AGENTE,
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.6"
        })
        self.robots = {}
        self.errores = 0
        self.peticiones = 0
        self.bloqueadas = 0
        self.carpeta = config.CRUDO / self.nombre / date.today().isoformat()
        self.conocidos = {p.stem for p in (config.CRUDO / self.nombre).glob("*/*.json")}

    def aviso(self, mensaje):
        print(f"  [{self.nombre}] {mensaje}")

    def permitido(self, url):
        if not self.respeta_robots:
            return True
        partes = urlparse(url)
        raiz = f"{partes.scheme}://{partes.netloc}"
        if raiz not in self.robots:
            analizador = RobotFileParser()
            try:
                r = self.sesion.get(raiz + "/robots.txt", timeout=config.TIEMPO_ESPERA)
                analizador.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                analizador.parse([])
            self.robots[raiz] = analizador
        return self.robots[raiz].can_fetch(config.AGENTE, url)

    def obtener(self, url, params=None):
        if not self.permitido(url):
            self.bloqueadas += 1
            self.aviso(f"robots.txt no permite {url}")
            return None
        for intento in range(1, config.REINTENTOS + 1):
            time.sleep(config.PAUSA)
            self.peticiones += 1
            try:
                r = self.sesion.get(url, params=params, timeout=config.TIEMPO_ESPERA)
            except requests.RequestException as error:
                self.aviso(f"intento {intento}: {type(error).__name__}")
                time.sleep(config.PAUSA * intento)
                continue
            if r.status_code == 200:
                return r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(config.PAUSA * intento * 2)
                continue
            self.aviso(f"HTTP {r.status_code} en {r.url}")
            break
        self.errores += 1
        return None

    def registro(self, url, titulo, empresa, descripcion_html, ubicacion="", modalidad="",
                 nivel="", etiquetas=None, fecha_publicacion="", fuente=None):
        url = urldefrag(url or "")[0]
        semilla = url or f"{titulo}|{empresa}"
        identificador = hashlib.sha1(semilla.encode("utf-8")).hexdigest()[:14]
        return {
            "id": f"{fuente or self.nombre}-{identificador}",
            "fuente": fuente or self.nombre,
            "url": url,
            "titulo": (titulo or "").strip(),
            "empresa": (empresa or "").strip(),
            "descripcion_html": descripcion_html or "",
            "ubicacion": (ubicacion or "").strip(),
            "modalidad_origen": modalidad or "",
            "nivel_origen": nivel or "",
            "etiquetas": [str(e) for e in (etiquetas or []) if e],
            "fecha_publicacion": fecha_iso(fecha_publicacion),
            "fecha_extraccion": datetime.now().isoformat(timespec="seconds")
        }

    def guardar(self, oferta):
        if oferta["id"] in self.conocidos:
            return False
        self.carpeta.mkdir(parents=True, exist_ok=True)
        ruta = self.carpeta / f"{oferta['id']}.json"
        ruta.write_text(json.dumps(oferta, ensure_ascii=False, indent=2), encoding="utf-8")
        self.conocidos.add(oferta["id"])
        return True

    def recolectar(self):
        return iter(())

    def ejecutar(self):
        inicio = time.time()
        nuevas = repetidas = descartadas = 0
        try:
            for oferta in self.recolectar():
                if not oferta or not oferta["titulo"] or len(oferta["descripcion_html"]) < 40:
                    descartadas += 1
                    continue
                if self.guardar(oferta):
                    nuevas += 1
                else:
                    repetidas += 1
                if nuevas + repetidas >= self.limite:
                    break
        except Exception as error:
            self.errores += 1
            self.aviso(f"acopio interrumpido: {type(error).__name__}: {error}")
        resumen = {
            "fuente": self.nombre,
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "nuevas": nuevas,
            "ya_guardadas": repetidas,
            "descartadas": descartadas,
            "peticiones": self.peticiones,
            "errores": self.errores,
            "bloqueadas_por_robots": self.bloqueadas,
            "segundos": round(time.time() - inicio, 1)
        }
        config.CRUDO.mkdir(parents=True, exist_ok=True)
        with open(config.BITACORA, "a", encoding="utf-8") as bitacora:
            bitacora.write(json.dumps(resumen, ensure_ascii=False) + "\n")
        return resumen
