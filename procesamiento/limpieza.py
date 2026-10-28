import html
import re
import unicodedata

from bs4 import BeautifulSoup

STOP_ES = set("""
a al algo ante antes asi cada como con contra cual cuando de del desde donde durante e el ella ellas ellos en entre
era eres es esa ese eso esta estamos estar estas este esto estos fue ha han hasta hay la las le les lo los mas me mi
mis muy ni no nos nuestra nuestras nuestro nuestros o otra otro otros para pero por porque que quien se sea ser si
sin sobre somos son su sus tambien te tiene tienen todo todos tu tus un una unas uno unos y ya
""".split())

STOP_EN = set("""
a about all also an and any are as at be been but by can etc for from has have if in into is it its may more must
not of on or our should so such than that the their them then these they this those to us was we were what when
which who will with would you your
""".split())

STOPWORDS = STOP_ES | STOP_EN
SOLO_ES = STOP_ES - STOP_EN
SOLO_EN = STOP_EN - STOP_ES

BLOQUES = ["p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"]
TOKEN = re.compile(r"[a-z0-9]+(?:[+#]+|(?:\.[a-z0-9]+)+)?")


ETIQUETA = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")


def html_a_texto(contenido, pasada=1):
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


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def raiz(token):
    if not token.isalpha():
        return token
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    if len(token) > 4 and token[-1] in "aeo":
        token = token[:-1]
    return token


def palabras(texto):
    limpio = normalizar(texto).replace(".net", " dotnet ")
    return [t.strip(".") for t in TOKEN.findall(limpio)]


def tokenizar(texto):
    return [raiz(t) for t in palabras(texto) if t not in STOPWORDS and (len(t) > 1)]


def idioma(texto):
    muestra = palabras(texto[:3000])
    es = sum(1 for t in muestra if t in SOLO_ES)
    en = sum(1 for t in muestra if t in SOLO_EN)
    if es == en == 0:
        return "desconocido"
    return "es" if es >= en else "en"
