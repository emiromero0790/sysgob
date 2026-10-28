import re

from procesamiento.limpieza import normalizar

TECNOLOGIAS = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "c#": ["c#", "c sharp", "csharp"],
    "c++": [r"c\+\+"],
    ".net": [r"\.net", "dotnet", r"asp\.net", "net core"],
    "php": ["php"],
    "ruby": ["ruby"],
    "rails": ["rails", "ruby on rails"],
    "go": ["golang"],
    "rust": ["rust"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "scala": ["scala"],
    "dart": ["dart"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "sass": ["sass", "scss"],
    "react": ["react", "reactjs", r"react\.js"],
    "react native": ["react native"],
    "angular": ["angular", "angularjs"],
    "vue": ["vue", "vuejs", r"vue\.js"],
    "next.js": [r"next\.js", "nextjs"],
    "svelte": ["svelte"],
    "node.js": ["node", "nodejs", r"node\.js"],
    "nestjs": ["nestjs", "nest"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi"],
    "spring": ["spring", "spring boot", "springboot"],
    "laravel": ["laravel"],
    "wordpress": ["wordpress"],
    "flutter": ["flutter"],
    "android": ["android"],
    "ios": ["ios"],
    "sql": ["sql"],
    "mysql": ["mysql", "mariadb"],
    "postgresql": ["postgresql", "postgres"],
    "sql server": ["sql server", "mssql", "t-sql"],
    "oracle": ["oracle", "pl/sql", "plsql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "firebase": ["firebase"],
    "kafka": ["kafka"],
    "graphql": ["graphql"],
    "api rest": ["api rest", "rest api", "apis rest", "restful", "rest apis", "api restful"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "terraform": ["terraform"],
    "jenkins": ["jenkins"],
    "ci/cd": ["ci/cd", "cicd", "ci cd", "integracion continua", "continuous integration"],
    "linux": ["linux", "ubuntu", "debian"],
    "bash": ["bash", "shell scripting"],
    "git": ["git", "github", "gitlab", "bitbucket"],
    "scrum": ["scrum", "agile", "agil", "agiles", "kanban"],
    "jira": ["jira"],
    "machine learning": ["machine learning", "aprendizaje automatico", "deep learning"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "pandas": ["pandas"],
    "spark": ["spark", "pyspark"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "selenium": ["selenium"],
    "cypress": ["cypress"],
    "figma": ["figma"],
    "sap": ["sap", "abap"],
    "salesforce": ["salesforce"],
    "unity": ["unity"],
    "redes": ["redes", "networking", "cisco", "ccna"]
}

ANTES = r"(?<![a-z0-9+#.\-])"
DESPUES = r"(?![a-z0-9+#])"


def compilar(alternativas):
    cuerpo = "|".join(a if "\\" in a else re.escape(a) for a in sorted(alternativas, key=len, reverse=True))
    return re.compile(ANTES + "(?:" + cuerpo + ")" + DESPUES)


PATRONES_TECNOLOGIA = {nombre: compilar(alias) for nombre, alias in TECNOLOGIAS.items()}

MODALIDADES = [
    ("hibrido", compilar(["hibrido", "hibrida", "hybrid", "semipresencial", "semi presencial", "semi-presencial"])),
    ("remoto", compilar(["remoto", "remota", "remote", "home office", "teletrabajo", "desde casa",
                         "work from home", "trabajo a distancia", "wfh"])),
    ("presencial", compilar(["presencial", "on-site", "onsite", "on site", "en sitio", "in-office", "en oficina"]))
]

NIVELES = [
    ("semi-senior", compilar(["semi senior", "semi-senior", "semisenior", "ssr", "mid level", "mid-level",
                              "mid senior", "mid-senior", "intermedio", "middle"])),
    ("senior", compilar(["senior", "sr", "lead", "lider", "principal", "staff", "arquitecto", "architect", "expert"])),
    ("practicante", compilar(["practicante", "practicantes", "practicas", "practicas profesionales", "becario",
                              "becaria", "intern", "internship", "trainee", "residencia profesional", "residente",
                              "residentes", "pasante", "estadia", "estadias"])),
    ("junior", compilar(["junior", "jr", "entry level", "entry-level", "recien egresado", "recien egresados",
                         "sin experiencia", "graduate"]))
]

AREAS = [
    ("fullstack", compilar(["full stack", "full-stack", "fullstack"])),
    ("movil", compilar(["movil", "moviles", "mobile", "android", "ios", "flutter", "react native"])),
    ("datos", compilar(["data", "datos", "bi", "business intelligence", "machine learning", "ml", "ia", "ai",
                        "analytics", "cientifico", "scientist", "bases de datos", "dba"])),
    ("devops", compilar(["devops", "sre", "cloud", "nube", "infraestructura", "infrastructure", "sysadmin",
                         "site reliability", "platform", "plataforma"])),
    ("qa", compilar(["qa", "tester", "testing", "pruebas", "quality assurance", "calidad", "sdet"])),
    ("seguridad", compilar(["seguridad", "security", "ciberseguridad", "cybersecurity", "pentester", "pentesting"])),
    ("soporte", compilar(["soporte", "support", "help desk", "helpdesk", "mesa de ayuda", "redes", "network"])),
    ("backend", compilar(["backend", "back-end", "back end", "api", "apis", "servicios web", "web services",
                          "microservicios", "microservices", "server-side"])),
    ("frontend", compilar(["frontend", "front-end", "front end", "maquetador", "maquetadora", "interfaces", "ui"]))
]

TECNOLOGIAS_FRONT = {"react", "angular", "vue", "html", "css", "sass", "next.js", "svelte"}
TECNOLOGIAS_BACK = {"django", "flask", "fastapi", "spring", "laravel", "node.js", "nestjs", ".net", "php", "java", "rails", "go"}
PALABRAS_DESARROLLO = compilar(["desarrollador", "desarrolladora", "developer", "programador", "programadora",
                                "software", "engineer", "ingeniero", "ingeniera", "programmer", "entwickler"])
EXPERIENCIA = re.compile(r"(\d{1,2})\s*\+?\s*(?:a|-|–)?\s*\d{0,2}\s*\+?\s*(?:anos|ano|years|year|yrs)")
VALORES_MODALIDAD = {"remoto", "hibrido", "presencial"}
VALORES_NIVEL = {"practicante", "junior", "semi-senior", "senior"}


def primera(reglas, texto):
    for nombre, patron in reglas:
        if patron.search(texto):
            return nombre
    return ""


def tecnologias(texto):
    limpio = normalizar(texto)
    return [nombre for nombre, patron in PATRONES_TECNOLOGIA.items() if patron.search(limpio)]


def modalidad(titulo, descripcion, origen=""):
    origen = normalizar(origen).strip()
    if origen in VALORES_MODALIDAD:
        return origen
    return primera(MODALIDADES, normalizar(origen + " " + titulo)) or primera(MODALIDADES, normalizar(descripcion)) or "no especificada"


def nivel(titulo, descripcion, origen=""):
    en_titulo = primera(NIVELES, normalizar(titulo))
    if en_titulo:
        return en_titulo
    origen = normalizar(origen).strip()
    if origen in VALORES_NIVEL:
        return origen
    cuerpo = normalizar(descripcion)
    for nombre in ("practicante", "junior", "semi-senior"):
        if dict(NIVELES)[nombre].search(cuerpo):
            return nombre
    anos = [int(n) for n in EXPERIENCIA.findall(cuerpo) if int(n) < 20]
    if anos:
        minimo = min(anos)
        return "junior" if minimo <= 1 else "semi-senior" if minimo <= 4 else "senior"
    if dict(NIVELES)["senior"].search(cuerpo[:400]):
        return "senior"
    return "no especificado"


def area(titulo, lista_tecnologias):
    limpio = normalizar(titulo)
    encontrada = primera(AREAS, limpio)
    if encontrada:
        return encontrada
    conjunto = set(lista_tecnologias)
    front, back = conjunto & TECNOLOGIAS_FRONT, conjunto & TECNOLOGIAS_BACK
    if PALABRAS_DESARROLLO.search(limpio) or front or back:
        if front and back:
            return "fullstack"
        if back:
            return "backend"
        if len(front) >= 2:
            return "frontend"
        return "desarrollo general"
    return "otra"
