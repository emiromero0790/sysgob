import json
import re
from urllib.parse import urljoin, urldefrag

from bs4 import BeautifulSoup

from acopio.base import Recolector


def buscar_json_ld(sopa):
    for bloque in sopa.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            datos = json.loads(bloque.string or bloque.get_text() or "")
        except ValueError:
            continue
        pila = [datos]
        while pila:
            actual = pila.pop()
            if isinstance(actual, list):
                pila.extend(actual)
            elif isinstance(actual, dict):
                tipo = actual.get("@type")
                if tipo == "JobPosting" or (isinstance(tipo, list) and "JobPosting" in tipo):
                    return actual
                pila.extend(v for v in actual.values() if isinstance(v, (dict, list)))
    return None


def texto_de(valor, clave="name"):
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    if isinstance(valor, dict):
        return str(valor.get(clave) or "")
    return str(valor or "")


def lugar_de(valor):
    if isinstance(valor, list):
        valor = valor[0] if valor else None
    if not isinstance(valor, dict):
        return ""
    direccion = valor.get("address")
    if isinstance(direccion, dict):
        partes = [direccion.get("addressLocality"), direccion.get("addressRegion")]
        return ", ".join(str(p) for p in partes if p)
    return str(direccion or "")


class SitioHTML(Recolector):
    respeta_robots = True

    def __init__(self, sitio, limite=None):
        self.nombre = sitio["nombre"]
        self.sitio = sitio
        super().__init__(limite)

    def enlaces(self):
        patron = re.compile(self.sitio["patron_enlace"])
        vistos = set()
        for listado in self.sitio["listados"]:
            for pagina in range(1, self.sitio.get("paginas", 1) + 1):
                params = {self.sitio["parametro_pagina"]: pagina} if pagina > 1 else None
                r = self.obtener(listado, params)
                if r is None:
                    break
                sopa = BeautifulSoup(r.text, "html.parser")
                encontrados = 0
                for ancla in sopa.find_all("a", href=True):
                    if not patron.search(ancla["href"]):
                        continue
                    url = urldefrag(urljoin(r.url, ancla["href"]))[0]
                    if url not in vistos:
                        vistos.add(url)
                        encontrados += 1
                        yield url
                if not encontrados:
                    break

    def extraer(self, url, html):
        sopa = BeautifulSoup(html, "html.parser")
        ld = buscar_json_ld(sopa)
        if ld and ld.get("title") and ld.get("description"):
            modalidad = "remoto" if "TELECOMMUTE" in str(ld.get("jobLocationType") or "").upper() else ""
            return self.registro(
                url=url,
                titulo=str(ld.get("title")),
                empresa=texto_de(ld.get("hiringOrganization")),
                descripcion_html=str(ld.get("description")),
                ubicacion=lugar_de(ld.get("jobLocation")),
                modalidad=modalidad,
                etiquetas=[texto_de(ld.get("employmentType"))],
                fecha_publicacion=ld.get("datePosted")
            )
        titulo = sopa.find("h1")
        contenedor = None
        for selector in self.sitio.get("selector_descripcion", "main").split(","):
            contenedor = sopa.select_one(selector.strip())
            if contenedor:
                break
        empresa = None
        for selector in self.sitio.get("selector_empresa", "").split(","):
            if selector.strip():
                empresa = sopa.select_one(selector.strip())
                if empresa:
                    break
        if not titulo or not contenedor:
            return None
        return self.registro(
            url=url,
            titulo=titulo.get_text(" ", strip=True),
            empresa=empresa.get_text(" ", strip=True) if empresa else "",
            descripcion_html=str(contenedor)
        )

    def recolectar(self):
        fallos = 0
        for url in self.enlaces():
            r = self.obtener(url)
            if r is None:
                fallos += 1
                if fallos >= 5:
                    self.aviso("el sitio rechaza las peticiones; se omite el resto de esta fuente")
                    return
                continue
            fallos = 0
            yield self.extraer(url, r.text)
