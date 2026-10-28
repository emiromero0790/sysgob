import config
from acopio.base import Recolector


class Arbeitnow(Recolector):
    nombre = "arbeitnow"
    api = "https://www.arbeitnow.com/api/job-board-api"
    paginas = 8

    def recolectar(self):
        for pagina in range(1, self.paginas + 1):
            r = self.obtener(self.api, {"page": pagina})
            if r is None:
                break
            try:
                datos = r.json().get("data") or []
            except ValueError:
                break
            if not datos:
                break
            for t in datos:
                etiquetas = t.get("tags") or []
                contexto = (str(t.get("title") or "") + " " + " ".join(map(str, etiquetas))).lower() + " "
                if not any(p in contexto for p in config.PALABRAS_TI):
                    continue
                yield self.registro(
                    url=t.get("url"),
                    titulo=t.get("title"),
                    empresa=t.get("company_name"),
                    descripcion_html=t.get("description"),
                    ubicacion=t.get("location"),
                    modalidad="remoto" if t.get("remote") is True else "",
                    etiquetas=etiquetas + (t.get("job_types") or []),
                    fecha_publicacion=t.get("created_at")
                )
