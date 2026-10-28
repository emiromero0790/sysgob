import config
from indexacion.lexico import IndiceLexico
from indexacion.semantico import IndiceSemantico
from procesamiento import almacen
from procesamiento.limpieza import tokenizar

MODOS = ("hibrido", "semantico", "lexico")


class Motor:
    def __init__(self):
        self.ofertas = {o["id"]: o for o in almacen.cargar()}
        self.lexico = IndiceLexico.cargar()
        self.semantico = IndiceSemantico.cargar()
        if set(self.lexico.ids) != set(self.ofertas) or set(self.semantico.ids) != set(self.ofertas):
            raise FileNotFoundError("Los indices no corresponden al corpus actual. Ejecuta: python main.py indexar")

    def senales(self, consulta, permitidos=None):
        lexico = dict(self.lexico.buscar(consulta, permitidos))
        maximo = max(lexico.values(), default=0.0)
        lexico = {i: s / maximo for i, s in lexico.items()} if maximo > 0 else {}
        semantico = {i: min(1.0, max(0.0, s)) for i, s in self.semantico.buscar(consulta, permitidos)}
        return lexico, semantico

    def ranking(self, consulta, modo="hibrido", permitidos=None):
        lexico, semantico = self.senales(consulta, permitidos)
        if modo == "lexico":
            puntajes = dict(lexico)
        elif modo == "semantico":
            puntajes = {i: s for i, s in semantico.items() if s > 0}
        else:
            peso = config.PESO_SEMANTICO
            candidatos = set(lexico) | {i for i, s in semantico.items() if s > 0}
            puntajes = {i: peso * semantico.get(i, 0.0) + (1 - peso) * lexico.get(i, 0.0) for i in candidatos}
        orden = sorted(((i, p) for i, p in puntajes.items() if p >= 0.005), key=lambda par: (-par[1], par[0]))
        return [(i, p, lexico.get(i, 0.0), semantico.get(i, 0.0)) for i, p in orden]

    def resumen(self, oferta, consulta=""):
        texto = oferta["descripcion"].replace("\n", " ")
        terminos = set(tokenizar(consulta))
        inicio = 0
        if terminos:
            palabras = texto.split(" ")
            acumulado = 0
            for palabra in palabras:
                if set(tokenizar(palabra)) & terminos:
                    inicio = max(0, acumulado - 90)
                    break
                acumulado += len(palabra) + 1
        fragmento = texto[inicio:inicio + 260].strip()
        if inicio > 0:
            fragmento = "…" + fragmento[fragmento.find(" ") + 1:]
        return fragmento + ("…" if inicio + 260 < len(texto) else "")

    def tarjeta(self, identificador, puntaje, lexico, semantico, consulta):
        oferta = self.ofertas[identificador]
        return {
            **{c: oferta[c] for c in ("id", "fuente", "url", "titulo", "empresa", "ubicacion", "modalidad",
                                      "nivel", "area", "tecnologias", "idioma", "fecha_publicacion")},
            "resumen": self.resumen(oferta, consulta),
            "relevancia": round(puntaje * 100, 1),
            "lexico": round(lexico * 100, 1),
            "semantico": round(semantico * 100, 1)
        }

    def buscar(self, consulta, modo="hibrido", filtros=None, k=None):
        k = k or config.RESULTADOS_POR_PAGINA
        modo = modo if modo in MODOS else "hibrido"
        permitidos = almacen.ids_filtrados(filtros or {})
        consulta = (consulta or "").strip()
        if not consulta:
            recientes = [o for o in self.ofertas.values() if permitidos is None or o["id"] in permitidos]
            recientes.sort(key=lambda o: (o["fecha_publicacion"], o["id"]), reverse=True)
            return {
                "consulta": "", "modo": "recientes", "total": len(recientes),
                "resultados": [{**self.tarjeta(o["id"], 0, 0, 0, ""), "relevancia": None} for o in recientes[:k]]
            }
        orden = self.ranking(consulta, modo, permitidos)
        return {
            "consulta": consulta, "modo": modo, "total": len(orden),
            "resultados": [self.tarjeta(i, p, l, s, consulta) for i, p, l, s in orden[:k]]
        }

    def comparar(self, consulta, k=8):
        lexico = self.buscar(consulta, "lexico", k=k)["resultados"]
        semantico = self.buscar(consulta, "semantico", k=k)["resultados"]
        ids_lexico, ids_semantico = {r["id"] for r in lexico}, {r["id"] for r in semantico}
        for r in lexico:
            r["exclusivo"] = r["id"] not in ids_semantico
        for r in semantico:
            r["exclusivo"] = r["id"] not in ids_lexico
        return {"consulta": consulta, "lexico": lexico, "semantico": semantico,
                "coincidencias": len(ids_lexico & ids_semantico)}

    def detalle(self, identificador):
        return self.ofertas.get(identificador)
