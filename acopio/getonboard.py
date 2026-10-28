import config
from acopio.base import Recolector

NIVELES = {1: "practicante", 2: "junior", 3: "semi-senior", 4: "senior", 5: "senior"}
MODALIDADES = {
    "fully_remote": "remoto",
    "remote_local": "remoto",
    "hybrid": "hibrido",
    "no_remote": "presencial"
}


def anidado(dato, *claves):
    for clave in claves:
        if not isinstance(dato, dict):
            return None
        dato = dato.get(clave)
    return dato


class GetOnBoard(Recolector):
    nombre = "getonboard"
    api = "https://www.getonbrd.com/api/v0"

    def categorias(self):
        r = self.obtener(f"{self.api}/categories", {"per_page": 100})
        ids = []
        if r is not None:
            try:
                ids = [str(c.get("id", "")) for c in r.json().get("data", [])]
            except ValueError:
                ids = []
        elegidas = [c for c in ids if any(p in c for p in config.GETONBOARD_PALABRAS)]
        return elegidas or ["programming"]

    def convertir(self, dato):
        a = dato.get("attributes") or {}
        partes = [a.get(c) for c in ("description", "projects", "functions", "desirable", "benefits")]
        descripcion = "\n".join(p for p in partes if isinstance(p, str) and p.strip())
        empresa = anidado(a, "company", "data", "attributes", "name") or ""
        nivel_id = anidado(a, "seniority", "data", "id")
        modalidad = MODALIDADES.get(a.get("remote_modality") or "", "")
        if not modalidad and a.get("remote") is True:
            modalidad = "remoto"
        paises = a.get("countries")
        ubicacion = ", ".join(p for p in paises if isinstance(p, str)) if isinstance(paises, list) else ""
        if not ubicacion:
            ubicacion = a.get("remote_zone") or ""
        url = anidado(dato, "links", "public_url") or f"https://www.getonbrd.com/jobs/{dato.get('id', '')}"
        return self.registro(
            url=url,
            titulo=a.get("title"),
            empresa=empresa,
            descripcion_html=descripcion,
            ubicacion=ubicacion if isinstance(ubicacion, str) else "",
            modalidad=modalidad,
            nivel=NIVELES.get(nivel_id, "") if isinstance(nivel_id, int) else "",
            etiquetas=[a.get("category_name")],
            fecha_publicacion=a.get("published_at")
        )

    def recolectar(self):
        categorias = self.categorias()
        cupo = max(1, self.limite // len(categorias))
        self.aviso(f"categorias: {', '.join(categorias)}")
        for categoria in categorias:
            pagina, tomadas = 1, 0
            while tomadas < cupo:
                r = self.obtener(
                    f"{self.api}/categories/{categoria}/jobs",
                    {"per_page": 100, "page": pagina, "expand": '["company"]'}
                )
                if r is None:
                    break
                try:
                    cuerpo = r.json()
                except ValueError:
                    break
                datos = cuerpo.get("data") or []
                if not datos:
                    break
                for dato in datos:
                    if tomadas >= cupo:
                        break
                    tomadas += 1
                    yield self.convertir(dato)
                if pagina >= (anidado(cuerpo, "meta", "total_pages") or pagina):
                    break
                pagina += 1
