"""Lematización y derivación ligera, sin dependencias externas.

El corpus de SysJobs mezcla español e inglés, así que el módulo aplica reglas
de ambos idiomas en una secuencia conservadora:

1. Diccionario de formas irregulares y de vocabulario técnico.
2. Reducción de plural (español e inglés).
3. Reducción de género y de formas verbales no personales.
4. Derivación (stemming) opcional sobre el lema ya obtenido.

No pretende ser un lematizador morfológico completo: es un enfoque basado en
reglas, reproducible y explicable, adecuado para un ejercicio académico de
Recuperación de Información.
"""

import re

# Formas que no deben tocarse: tecnología, siglas y palabras muy cortas.
TECNICOS = {
    "python", "java", "javascript", "typescript", "js", "ts", "c", "c++", "c#",
    "csharp", "dotnet", ".net", "php", "ruby", "rails", "go", "golang", "rust",
    "kotlin", "swift", "scala", "dart", "html", "html5", "css", "css3", "sass",
    "scss", "react", "reactjs", "angular", "angularjs", "vue", "vuejs", "svelte",
    "nextjs", "next.js", "nestjs", "node", "nodejs", "node.js", "django", "flask",
    "fastapi", "spring", "springboot", "laravel", "wordpress", "flutter", "android",
    "ios", "sql", "mysql", "mariadb", "postgresql", "postgres", "mssql", "oracle",
    "plsql", "mongodb", "mongo", "redis", "elasticsearch", "firebase", "kafka",
    "graphql", "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
    "jenkins", "linux", "ubuntu", "debian", "bash", "git", "github", "gitlab",
    "bitbucket", "scrum", "agile", "kanban", "jira", "ml", "ai", "ia", "bi",
    "tensorflow", "pytorch", "pandas", "spark", "pyspark", "powerbi", "tableau",
    "selenium", "cypress", "figma", "sap", "abap", "salesforce", "unity", "redes",
    "networking", "cisco", "ccna", "devops", "sre", "sysadmin", "qa", "sdet",
    "api", "rest", "restful", "microservicios", "microservices", "saas",
    "paas", "iaas", "etl", "elt", "bi", "crm", "erp", "http", "https", "json",
    "xml", "yaml", "csv", "sqlite", "nosql", "mongodb", "postgres", "nginx",
    "apache", "gitflow", "ci", "cd", "cicd", "llm", "nlp", "ux", "ui", "sdk",
    "jwt", "oauth", "sso", "vm", "vms", "gpu", "cpu", "ram", "ssd", "http2",
    "websocket", "websockets", "grpc", "soap", "swagger", "postman", "junit",
    "pytest", "jest", "maven", "gradle", "npm", "yarn", "pip", "conda", "venv",
    "ansible", "chef", "puppet", "prometheus", "grafana", "datadog", "splunk",
}

IRREGULARES = {
    # Español
    "soy": "ser", "eres": "ser", "es": "ser", "somos": "ser", "son": "ser",
    "era": "ser", "eran": "ser", "fue": "ser", "fueron": "ser", "sido": "ser",
    "siendo": "ser", "tengo": "tener", "tienes": "tener", "tiene": "tener",
    "tenemos": "tener", "tienen": "tener", "tuve": "tener", "tenido": "tener",
    "hago": "hacer", "haces": "hacer", "hace": "hacer", "hacemos": "hacer",
    "hacen": "hacer", "hecho": "hacer", "puedo": "poder", "puedes": "poder",
    "puede": "poder", "podemos": "poder", "pueden": "poder",
    "analisis": "analisis", "practica": "practica", "practicas": "practica",
    "practico": "practico", "practicos": "practico", "practica profesional": "practica",
    "datos": "dato", "dato": "dato", "empresas": "empresa", "empresa": "empresa",
    "lenguajes": "lenguaje", "lenguaje": "lenguaje", "frameworks": "framework",
    "buscamos": "buscar", "ofrecemos": "ofrecer", "requerimos": "requerir",
    "valoramos": "valorar", "buscando": "buscar", "ofreciendo": "ofrecer",
    "construyen": "construir", "construye": "construir", "construyo": "construir",
    "incluyen": "incluir", "incluye": "incluir", "contribuyen": "contribuir",
    "contribuye": "contribuir", "postulate": "postular", "postularse": "postular",
    "conocimientos": "conocimiento", "conocimiento": "conocimiento",
    "requisitos": "requisito", "requisito": "requisito",
    "responsabilidades": "responsabilidad", "responsabilidad": "responsabilidad",
    "habilidades": "habilidad", "habilidad": "habilidad",
    "beneficios": "beneficio", "beneficio": "beneficio",
    "herramientas": "herramienta", "herramienta": "herramienta",
    "experiencias": "experiencia", "experiencia": "experiencia",
    "anos": "ano", "ano": "ano",
    # Inglés
    "children": "child", "people": "person", "men": "man", "women": "woman",
    "analyses": "analysis", "theses": "thesis", "criteria": "criterion",
    "indices": "index", "matrices": "matrix", "vertices": "vertex",
    "leaves": "leaf", "knives": "knife", "wives": "wife", "lives": "life",
    "teeth": "tooth", "feet": "foot", "geese": "goose", "mice": "mouse",
    "was": "be", "were": "be", "been": "be", "being": "be", "has": "have",
    "had": "have", "does": "do", "did": "do", "done": "do", "went": "go",
    "gone": "go", "made": "make", "took": "take", "taken": "take",
    "gave": "give", "given": "give", "got": "get", "gotten": "get",
    "said": "say", "saw": "see", "seen": "see", "came": "come",
    "became": "become", "built": "build", "led": "lead", "ran": "run",
    "wrote": "write", "written": "write", "chose": "choose", "chosen": "choose",
    "spoke": "speak", "spoken": "speak", "thought": "think", "brought": "bring",
    "bought": "buy", "taught": "teach", "found": "find", "held": "hold",
    "kept": "keep", "left": "leave", "meant": "mean", "met": "meet",
    "paid": "pay", "sent": "send", "shown": "show", "sold": "sell",
    "spent": "spend", "stood": "stand", "told": "tell", "understood": "understand",
    "won": "win", "wore": "wear", "worn": "wear",
}

# Plurales españoles que se resuelven con una terminación conocida.
PLURALES_ES = (
    ("ciones", "cion"), ("siones", "sion"), ("dores", "dor"),
    ("tores", "tor"), ("ores", "or"), ("ones", "on"), ("anes", "an"),
    ("enes", "en"), ("inos", "ino"), ("ales", "al"), ("iles", "il"),
    ("ares", "ar"), ("eres", "er"), ("ires", "ir"), ("ades", "ad"),
    ("edes", "ed"), ("ides", "id"), ("udes", "ud"), ("eses", "es"),
    ("ges", "ge"), ("jes", "je"), ("ces", "z"),
)

VOCALES = set("aeiou")

RESTAURAR_E = {
    "cod", "hir", "us", "mak", "tak", "giv", "hav", "writ", "manag", "driv",
    "mov", "serv", "creat", "updat", "scal", "deploy", "test", "practic",
    "organiz", "optimiz", "implement", "integrat", "automat", "migrat",
}

SUFIJOS_DERIVACION_ES = (
    "amientos", "amiento", "imientos", "imiento", "aciones", "acion",
    "uciones", "ucion", "ciones", "cion", "idades", "idad", "mente",
    "ancias", "ancia", "encias", "encia", "adores", "adoras", "ador",
    "adora", "dores", "doras", "dor", "dora", "istas", "ista",
    "ismos", "ismo", "ivas", "ivos", "iva", "ivo", "osas", "osos",
    "osa", "oso", "ales", "al", "ares", "ar", "eres", "er", "ires", "ir",
    "ando", "iendo", "ado", "ada", "ido", "ida", "es", "s",
)

SUFIJOS_DERIVACION_EN = (
    "ational", "tional", "ization", "isation", "fulness", "ousness",
    "iveness", "ements", "ement", "ments", "ment", "ances", "ance",
    "ences", "ence", "ables", "able", "ibles", "ible", "ingly", "edly",
    "ies", "ing", "ied", "ed", "ly", "es", "s",
)

NO_PLURAL = {"is", "us", "sis", "ss", "news", "series", "species"}


def _solo_letras(token):
    return token.isalpha()


def _protegido(token):
    return (
        not token
        or token in TECNICOS
        or token in IRREGULARES
        or len(token) <= 3
        or any(c in token for c in "+#./")
        or any(c.isdigit() for c in token)
    )


def _plural_es(token):
    if token.endswith("s") and token not in NO_PLURAL and len(token) > 3:
        if token.endswith("es") and len(token) > 4:
            for sufijo, reemplazo in PLURALES_ES:
                if token.endswith(sufijo):
                    return token[: -len(sufijo)] + reemplazo
        return token[:-1]
    return token


def _plural_en(token):
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith(("ses", "xes", "zes", "ches", "shes")) and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and token not in NO_PLURAL and not token.endswith(("ss", "us", "is")) and len(token) > 3:
        return token[:-1]
    return token


def _genero_es(token):
    for sufijo, reemplazo in (
        ("arias", "ario"), ("aria", "ario"), ("orias", "orio"), ("oria", "orio"),
        ("oras", "or"), ("ora", "or"), ("eras", "ero"), ("era", "ero"),
        ("inas", "ino"), ("ina", "ino"), ("ivas", "ivo"), ("iva", "ivo"),
        ("osos", "oso"), ("osa", "oso"),
    ):
        if token.endswith(sufijo) and len(token) > len(sufijo) + 2:
            return token[: -len(sufijo)] + reemplazo
    return token


def _verbal_es(token):
    if len(token) < 6:
        return token
    for sufijo, reemplazo in (
        ("andose", "ar"), ("iendose", "er"),
        ("iendo", "er"), ("ando", "ar"),
        ("amos", "ar"), ("emos", "er"), ("imos", "ir"),
        ("ados", "ar"), ("adas", "ar"), ("ado", "ar"), ("ada", "ar"),
        ("idos", "er"), ("idas", "er"), ("ido", "er"), ("ida", "er"),
    ):
        if token.endswith(sufijo) and len(token) > len(sufijo) + 2:
            return token[: -len(sufijo)] + reemplazo
    return token


def _verbal_en(token):
    if len(token) < 4:
        return token
    if token.endswith("ying") and len(token) > 5:
        return token[:-4] + "y"
    if token.endswith("ing") and len(token) >= 5:
        raiz = token[:-3]
        if len(raiz) > 2 and raiz[-1] == raiz[-2] and raiz[-1] not in VOCALES:
            raiz = raiz[:-1]
        if raiz in RESTAURAR_E:
            raiz += "e"
        return raiz
    if token.endswith("ied") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ed") and len(token) > 4:
        raiz = token[:-2]
        if len(raiz) > 2 and raiz[-1] == raiz[-2] and raiz[-1] not in VOCALES:
            raiz = raiz[:-1]
        if raiz in RESTAURAR_E:
            raiz += "e"
        return raiz
    if token.endswith("ly") and len(token) > 5:
        return token[:-2]
    return token


def lematizar(token):
    """Devuelve el lema probable de una palabra ya normalizada (sin acentos)."""
    if not token:
        return token
    token = token.strip().lower()
    if _protegido(token):
        return IRREGULARES.get(token, token)
    if not _solo_letras(token):
        return token

    # El plural inglés en -ies debe resolverse antes que el español.
    if token.endswith("ies") and len(token) > 4:
        base = _plural_en(token)
    else:
        base = _plural_es(token)
        if base == token:
            base = _plural_en(token)
    if base == token:
        base = _genero_es(token)
    if base == token:
        base = _verbal_es(token)
    if base == token:
        base = _verbal_en(token)
    if base != token and len(base) >= 2:
        return base
    return token


def derivar(token, lema=None):
    """Derivación ligera (stemming) sobre el lema de una palabra."""
    palabra = lema or lematizar(token)
    if not palabra or _protegido(palabra):
        return palabra
    if not _solo_letras(palabra):
        return palabra

    raiz = palabra
    cambio = True
    while cambio and len(raiz) > 3:
        cambio = False
        for sufijo in SUFIJOS_DERIVACION_ES:
            if raiz.endswith(sufijo) and len(raiz) - len(sufijo) >= 3:
                nueva = raiz[: -len(sufijo)]
                if nueva != raiz:
                    raiz = nueva
                    cambio = True
                    break
        if cambio:
            continue
        for sufijo in SUFIJOS_DERIVACION_EN:
            if raiz.endswith(sufijo) and len(raiz) - len(sufijo) >= 3:
                reemplazo = ""
                if sufijo == "ies":
                    reemplazo = "y"
                elif sufijo in ("ization", "isation"):
                    reemplazo = "ize"
                elif sufijo in ("ational", "tional"):
                    reemplazo = "tion"
                nueva = raiz[: -len(sufijo)] + reemplazo
                if nueva != raiz:
                    raiz = nueva
                    cambio = True
                    break

    if raiz.endswith("e") and len(raiz) > 4:
        raiz = raiz[:-1]
    return raiz or palabra


def analizar_palabra(token):
    """Devuelve las tres representaciones usadas en el proyecto."""
    return {"palabra": token, "lema": lematizar(token), "derivada": derivar(token)}


def es_tecnico(token):
    return token in TECNICOS or any(c in token for c in "+#./")


def ejemplos_lematizacion(palabras, limite=18):
    """Pares palabra -> lema que realmente cambiaron, para mostrar en la web."""
    vistos, pares = set(), []
    for palabra in palabras:
        if palabra in vistos or _protegido(palabra):
            continue
        lema = lematizar(palabra)
        if lema != palabra:
            vistos.add(palabra)
            pares.append([palabra, lema, derivar(palabra, lema)])
        if len(pares) >= limite:
            break
    return pares
