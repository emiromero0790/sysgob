import config
from acopio.base import Recolector


class Remotive(Recolector):
    nombre = "remotive"
    api = "https://remotive.com/api/remote-jobs"

    def recolectar(self):
        r = self.obtener(self.api)
        if r is None:
            return
        try:
            trabajos = r.json().get("jobs") or []
        except ValueError:
            return
        for t in trabajos:
            categoria = str(t.get("category") or "").lower()
            if not any(p in categoria for p in config.REMOTIVE_CATEGORIAS):
                continue
            yield self.registro(
                url=t.get("url"),
                titulo=t.get("title"),
                empresa=t.get("company_name"),
                descripcion_html=t.get("description"),
                ubicacion=t.get("candidate_required_location"),
                modalidad="remoto",
                etiquetas=(t.get("tags") or []) + [t.get("category"), t.get("job_type")],
                fecha_publicacion=t.get("publication_date")
            )
