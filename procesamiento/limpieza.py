import html
import re
import unicodedata

from bs4 import BeautifulSoup

import config
from procesamiento.lematizador import analizar_palabra, derivar, lematizar

STOP_ES = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun cada como con contra cual cuales
cualquier cuando de del desde donde dos durante e el ella ellas ello ellos en entre era eran eres es esa
esas ese eso esos esta estaba estado estamos estan estar estas este esto estos estoy fue fueron ha habia
han hasta hay la las le le les lo los mas me mi mientras mis mucho muy ni no nos nosotras nosotros nuestra
nuestras nuestro nuestros o os otra otras otro otros para pero poco por porque que quien quienes se sea
sean segun ser si sin sobre somos son soy su sus tambien tan te tener tiene tienen todo todos tu tus un
una unas uno unos usted ustedes y ya
""".split())

STOP_EN = set("""
a about above after again against all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each etc few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just me more most my
myself no nor not now of off on once only or other our ours ourselves out over own same she should so
some such than that the their theirs them themselves then there these they this those through to too
under until up very was we were what when where which while who whom why will with would you your yours
yourself yourselves
""".split())

# Arbeitnow publica muchas vacantes en alemán; se filtran sus palabras vacías
# para que no dominen las frecuencias del corpus.
STOP_DE = set("""
aber alle allem allen aller alles als also am an ander andere anderem anderen anderer anderes anderm
andern anders auch auf aus bei beim bin bis bist da damit dann das dass dasselbe dazu dein deine dem den
denn der deren des dessen dich die dies diese diesem diesen dieser dieses dir doch dort du durch ein eine
einem einen einer eines einig einige einigem einigen einiger einiges einmal er es etwas euch euer eure eurem
euren eurer eures für gegen gewesen hab habe haben hat hatte hatten hier hin hinter ich ihm ihn ihnen ihr ihre
ihrem ihren ihrer ihres im in indem ins ist jede jedem jeden jeder jedes jene jenem jenen jener jenes jetzt
kann kannst können könnte machen man manche manchem manchen mancher manches mein meine meinem meinen meiner
meines mich mir mit muss müssen nach nicht nichts noch nun nur ob oder ohne sehr sein seine seinem seinen
seiner seines selbst sich sie sind so solche solchem solchen solcher solches soll sollen sollte sondern sonst
über um und uns unser unsere unserem unseren unseres unter viel vom von vor wann war waren warst was weg weil
weiter welche welchem welchen welcher welches wenn werde werden wie wieder will wir wo wollen worden wurde
würde zu zum zur zwar zwischen
""".split())

STOP_FR = set("""
au aux avec ce ces dans de des du elle en et eux il je la le les leur lui ma mais me même mes moi mon ne
nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous
c est d l à été être plus
""".split())

STOPWORDS = STOP_ES | STOP_EN | STOP_DE | STOP_FR
SOLO_ES = STOP_ES - STOP_EN
SOLO_EN = STOP_EN - STOP_ES

BLOQUES = ["p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"]
TOKEN = re.compile(r"[a-z0-9]+(?:[+#]+|(?:\.[a-z0-9]+)+|(?:\/[a-z0-9]+)+)?")
ETIQUETA = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")

URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
CORREO = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
NUMERO = re.compile(r"\b\d+(?:[.,]\d+)*\b")
NO_PERMITIDO = re.compile(r"[^\w\s+#./-]+", re.UNICODE)
ESPACIOS = re.compile(r"\s+")


def html_a_texto(contenido, pasada=1):
    """Convierte HTML en texto legible conservando viñetas y saltos de bloque."""
    if not contenido:
        return ""
    sopa = BeautifulSoup(contenido, "html.parser")
    for etiqueta in sopa(["script", "style", "noscript", "svg", "form", "button", "nav", "footer"]):
        etiqueta.decompose()
    for salto in sopa.find_all("br"):
        salto.replace_with("\n")
    for vineta in sopa.find_all("li"):
        vineta.insert(0, "\n- ")
    for bloque in sopa.find_all(BLOQUES):
        bloque.append("\n")
    texto = html.unescape(sopa.get_text(""))
    texto = texto.replace("\xa0", " ").replace("\u200b", "")
    if pasada == 1 and ETIQUETA.search(texto):
        return html_a_texto(texto, pasada=2)
    lineas = [re.sub(r"[ \t\r\f\v]+", " ", linea).strip() for linea in texto.split("\n")]
    lineas = [linea for linea in lineas if linea and linea != "-"]
    return "\n".join(lineas)


def limpiar_texto(texto, quitar_numeros=None):
    """Limpieza superficial: URLs, correos, emojis, signos raros y números.

    Conserva mayúsculas y acentos para poder mostrar un "antes / después"
    entendible; la normalización fuerte ocurre en normalizar().
    """
    quitar_numeros = config.QUITAR_NUMEROS if quitar_numeros is None else quitar_numeros
    texto = html.unescape(str(texto or ""))
    texto = URL.sub(" ", texto)
    texto = CORREO.sub(" ", texto)
    texto = texto.replace("_", " ").replace("|", " ")
    texto = NO_PERMITIDO.sub(" ", texto)
    if quitar_numeros:
        texto = NUMERO.sub(" ", texto)
    texto = re.sub(r"(?:(?<=\s)|^)[./+#-](?=\s|$)", " ", texto)
    return ESPACIOS.sub(" ", texto).strip()


def normalizar(texto):
    """Normalización: minúsculas, sin acentos y con espacios colapsados."""
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return ESPACIOS.sub(" ", texto).strip()


def raiz(token):
    """Compatibilidad con versiones anteriores: raíz derivada del token."""
    return derivar(token)


def palabras(texto):
    """Tokens normalizados, sin stopwords y sin números sueltos.

    No aplica lematización: sirve para contar palabras y detectar idioma.
    Los términos técnicos con +, #, . o / se preservan (c++, c#, node.js).
    """
    limpio = normalizar(limpiar_texto(texto)).replace(".net", " dotnet ")
    tokens = []
    for bruto in TOKEN.findall(limpio):
        token = bruto.strip(".")
        if not token or token.isdigit():
            continue
        if len(token) < config.MIN_LONGITUD_TOKEN:
            continue
        tokens.append(token)
    return tokens


def tokenizar(texto, estrategia=None, quitar_vacias=True):
    """Pipeline completo: limpieza, normalización, tokenización y reducción.

    estrategia:
      "lema"     -> lematización
      "derivada" -> derivación / stemming
      "palabra"  -> solo normalización
    """
    estrategia = estrategia or config.ESTRATEGIA_TOKENS
    resultado = []
    for token in palabras(texto):
        if quitar_vacias and token in STOPWORDS:
            continue
        if estrategia == "derivada":
            reducido = derivar(token)
        elif estrategia == "palabra":
            reducido = token
        else:
            reducido = lematizar(token)
        if quitar_vacias and reducido in STOPWORDS:
            continue
        if reducido and len(reducido) >= config.MIN_LONGITUD_TOKEN:
            resultado.append(reducido)
    return resultado


def tokenizar_detalle(texto):
    """Devuelve cada palabra con las representaciones del pipeline.

    Se usa para las estadísticas y la vista de preprocesamiento de la web.
    """
    detalle = []
    for token in palabras(texto):
        analisis = analizar_palabra(token)
        analisis["vacia"] = token in STOPWORDS or analisis["lema"] in STOPWORDS
        detalle.append(analisis)
    return detalle


def quitar_vacias(tokens):
    return [t for t in tokens if t not in STOPWORDS]


def ngramas(tokens, n):
    """N-gramas consecutivos sobre una lista de tokens."""
    if n <= 0 or len(tokens) < n:
        return []
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def idioma(texto):
    muestra = palabras(texto[:3000])
    conteos = {
        "es": sum(1 for t in muestra if t in STOP_ES),
        "en": sum(1 for t in muestra if t in STOP_EN),
        "de": sum(1 for t in muestra if t in STOP_DE),
        "fr": sum(1 for t in muestra if t in STOP_FR),
    }
    maximo = max(conteos.values())
    if maximo == 0:
        return "desconocido"
    return max(conteos, key=conteos.get)
