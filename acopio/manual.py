import csv
import html

import config
from acopio.base import Recolector


class Manual(Recolector):
    nombre = "manual"

    def recolectar(self):
        config.MANUAL.mkdir(parents=True, exist_ok=True)
        for archivo in sorted(config.MANUAL.glob("*.csv")):
            with open(archivo, newline="", encoding="utf-8-sig") as entrada:
                for fila in csv.DictReader(entrada):
                    fila = {(k or "").strip().lower(): (v or "").strip() for k, v in fila.items()}
                    if not fila.get("titulo"):
                        continue
                    parrafos = "".join(f"<p>{html.escape(p)}</p>" for p in fila.get("descripcion", "").splitlines() if p.strip())
                    yield self.registro(
                        url=fila.get("url"),
                        titulo=fila.get("titulo"),
                        empresa=fila.get("empresa"),
                        descripcion_html=parrafos,
                        ubicacion=fila.get("ubicacion"),
                        modalidad=fila.get("modalidad"),
                        nivel=fila.get("nivel"),
                        fecha_publicacion=fila.get("fecha_publicacion"),
                        fuente=fila.get("fuente") or "manual"
                    )
