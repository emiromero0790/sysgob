import random
from datetime import date, timedelta

from acopio.base import Recolector

PUESTOS = [
    ("Desarrollador backend", ["python", "django", "postgresql", "docker", "api rest"], "construir servicios y microservicios que atienden a las aplicaciones de la empresa"),
    ("Programador de servicios web", ["java", "spring boot", "mysql", "api rest"], "programar los servicios web que consumen las aplicaciones internas"),
    ("Ingeniero de APIs", ["node.js", "express", "mongodb", "graphql"], "disenar y mantener las interfaces de programacion que integran nuestros sistemas"),
    ("Desarrollador frontend", ["javascript", "react", "html", "css"], "crear interfaces de usuario accesibles y rapidas"),
    ("Maquetador web", ["html", "css", "sass", "javascript"], "convertir disenos en paginas responsivas"),
    ("Ingeniero de interfaces", ["typescript", "angular", "css"], "desarrollar componentes visuales reutilizables para el portal de clientes"),
    ("Desarrollador full stack", ["javascript", "react", "node.js", "sql"], "participar en todo el ciclo, de la base de datos a la pantalla"),
    ("Programador de aplicaciones moviles", ["kotlin", "android", "firebase"], "desarrollar apps para telefonos y tabletas"),
    ("Desarrollador iOS", ["swift", "ios", "git"], "construir nuestra aplicacion para iPhone"),
    ("Desarrollador Flutter", ["flutter", "dart", "firebase"], "crear aplicaciones multiplataforma"),
    ("Analista de datos", ["sql", "python", "power bi", "pandas"], "generar reportes y tableros para la toma de decisiones"),
    ("Cientifico de datos", ["python", "machine learning", "tensorflow", "sql"], "entrenar modelos predictivos con informacion del negocio"),
    ("Ingeniero de datos", ["python", "spark", "aws", "sql"], "construir flujos de extraccion y carga de informacion"),
    ("Ingeniero DevOps", ["docker", "kubernetes", "aws", "jenkins", "linux"], "automatizar despliegues y cuidar la infraestructura en la nube"),
    ("Administrador de infraestructura cloud", ["azure", "terraform", "linux"], "operar servidores y servicios en la nube"),
    ("Tester de software", ["selenium", "jira", "sql"], "disenar y ejecutar pruebas funcionales y automatizadas"),
    ("Ingeniero de calidad QA", ["cypress", "javascript", "git"], "asegurar la calidad del producto antes de cada liberacion"),
    ("Analista de ciberseguridad", ["linux", "python", "redes"], "monitorear incidentes y revisar vulnerabilidades"),
    ("Soporte tecnico de sistemas", ["windows", "redes", "sql"], "atender a usuarios internos y dar mantenimiento a equipos"),
    ("Desarrollador .NET", ["c#", ".net", "sql server", "azure"], "mantener el sistema administrativo de la compania"),
    ("Programador PHP", ["php", "laravel", "mysql", "javascript"], "desarrollar modulos del sistema de ventas en linea"),
    ("Administrador de bases de datos", ["postgresql", "oracle", "sql", "linux"], "respaldar, optimizar y vigilar las bases de datos")
]

NIVELES = [
    ("Practicante de {}", "Buscamos estudiantes de Ingenieria en Sistemas de ultimos semestres para practicas profesionales o residencia. No se requiere experiencia previa; ofrecemos apoyo economico y horario flexible para la escuela."),
    ("{} Jr", "Vacante para recien egresados o personas con hasta 1 ano de experiencia. Tendras acompanamiento de un mentor."),
    ("{} Semi Senior", "Requerimos de 2 a 4 anos de experiencia comprobable y autonomia para resolver tareas."),
    ("{} Senior", "Requerimos mas de 5 anos de experiencia, liderazgo tecnico y revision de codigo del equipo.")
]

MODALIDADES = [
    ("Trabajo 100% remoto desde cualquier parte de Mexico.", "Remoto, Mexico"),
    ("Esquema hibrido: tres dias en oficina y dos en home office.", "Guadalajara, Jalisco"),
    ("Esquema hibrido con visitas semanales a oficina.", "Ciudad de Mexico"),
    ("Trabajo presencial en nuestras oficinas.", "Morelia, Michoacan"),
    ("Trabajo presencial de lunes a viernes.", "Queretaro, Queretaro")
]

EXTRAS = [
    "Valoramos el trabajo en equipo y la comunicacion clara.",
    "Usamos metodologias agiles con Scrum.",
    "Es deseable ingles intermedio para leer documentacion.",
    "Ofrecemos prestaciones de ley, seguro de gastos medicos y capacitacion constante.",
    "Control de versiones con Git y revisiones de codigo entre pares.",
    "Participaras en la documentacion tecnica de los proyectos."
]


class Demo(Recolector):
    nombre = "demo"

    def recolectar(self):
        azar = random.Random(7)
        hoy = date.today()
        numero = 0
        for puesto, tecnologias, tarea in PUESTOS:
            for plantilla, parrafo_nivel in azar.sample(NIVELES, 3):
                for frase_modalidad, ciudad in azar.sample(MODALIDADES, 2):
                    numero += 1
                    stack = azar.sample(tecnologias, max(2, len(tecnologias) - azar.randint(0, 1)))
                    extras = azar.sample(EXTRAS, 2)
                    descripcion = (
                        f"<p>Tu trabajo sera {tarea}.</p>"
                        f"<p>{parrafo_nivel}</p>"
                        f"<p>Conocimientos solicitados:</p><ul>{''.join(f'<li>{t}</li>' for t in stack)}</ul>"
                        f"<p>{frase_modalidad} {' '.join(extras)}</p>"
                        f"<p>Oferta sintetica generada para probar SysJobs; no corresponde a una vacante real.</p>"
                    )
                    yield self.registro(
                        url=f"https://ejemplo.invalid/demo/{numero}",
                        titulo=plantilla.format(puesto) if "Practicante" not in plantilla else plantilla.format(puesto.lower()),
                        empresa=f"Empresa Demo {azar.randint(1, 25):02d}",
                        descripcion_html=descripcion,
                        ubicacion=ciudad,
                        fecha_publicacion=(hoy - timedelta(days=azar.randint(0, 60))).isoformat()
                    )
