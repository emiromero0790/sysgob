const estado = { q: "", modo: "hibrido", filtros: { modalidad: "", nivel: "", area: "", fuente: "", tecnologias: [] } };
let corpus = null;

const NOMBRES = {
  modalidad: { remoto: "Remoto", hibrido: "Híbrido", presencial: "Presencial", "no especificada": "Sin especificar" },
  nivel: { practicante: "Prácticas", junior: "Junior", "semi-senior": "Semi senior", senior: "Senior", "no especificado": "Sin especificar" },
  area: { backend: "Backend", frontend: "Frontend", fullstack: "Full stack", movil: "Móvil", datos: "Datos", devops: "DevOps y nube", qa: "Pruebas y QA", seguridad: "Seguridad", soporte: "Soporte y redes", "desarrollo general": "Desarrollo general", otra: "Otra" },
  idioma: { es: "Español", en: "Inglés", desconocido: "Sin detectar" },
  modo: { hibrido: "híbrido", semantico: "por significado", lexico: "por palabras exactas" }
};

const ICONOS = {
  remoto: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11 12 4l9 7"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>',
  hibrido: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12 7 8l5 4"/><path d="M4 11v8h6v-8"/><path d="M14 19V5h7v14"/><path d="M17 9h1M17 13h1"/></svg>',
  presencial: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V4h14v16"/><path d="M3 20h18"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M11 20v-4h2v4"/></svg>'
};

const $ = (selector) => document.querySelector(selector);

function limpio(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function nombre(grupo, valor) {
  return (NOMBRES[grupo] && NOMBRES[grupo][valor]) || valor;
}

function iniciales(texto) {
  const partes = (texto || "?").replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).filter(Boolean);
  return ((partes[0] || "?")[0] + (partes[1] ? partes[1][0] : "")).toUpperCase();
}

function tono(texto) {
  let suma = 0;
  for (const letra of texto || "") suma = (suma * 31 + letra.charCodeAt(0)) % 360;
  return suma;
}

function fecha(iso) {
  if (!iso) return "";
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}

async function pedir(ruta) {
  const respuesta = await fetch(ruta);
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || "No se pudo completar la solicitud.");
  return datos;
}

function etiquetas(oferta) {
  const piezas = [];
  if (oferta.modalidad !== "no especificada") {
    piezas.push(`<li class="clave">${ICONOS[oferta.modalidad] || ""}${limpio(nombre("modalidad", oferta.modalidad))}</li>`);
  }
  if (oferta.nivel !== "no especificado") {
    piezas.push(`<li class="nivel">${limpio(nombre("nivel", oferta.nivel))}</li>`);
  }
  oferta.tecnologias.slice(0, 7).forEach((t) => piezas.push(`<li>${limpio(t)}</li>`));
  if (oferta.tecnologias.length > 7) piezas.push(`<li>+${oferta.tecnologias.length - 7}</li>`);
  return `<ul class="etiquetas">${piezas.join("")}</ul>`;
}

function medidor(oferta) {
  const pie = `<span class="origen">${limpio(oferta.fuente)}${oferta.fecha_publicacion ? ", " + fecha(oferta.fecha_publicacion) : ""}</span>`;
  if (oferta.relevancia === null) return `<div class="medidor">${pie}</div>`;
  return `<div class="medidor">
    <div><div class="porcentaje">${Math.round(oferta.relevancia)}<small>%</small></div><div class="medidor-rotulo">relevancia</div></div>
    <div class="senal"><span>Significado <b>${Math.round(oferta.semantico)}</b></span><div class="barra sem"><i style="width:${oferta.semantico}%"></i></div></div>
    <div class="senal"><span>Palabras <b>${Math.round(oferta.lexico)}</b></span><div class="barra lex"><i style="width:${oferta.lexico}%"></i></div></div>
    ${pie}
  </div>`;
}

function tarjeta(oferta) {
  const lugar = [oferta.empresa ? `<b>${limpio(oferta.empresa)}</b>` : "", limpio(oferta.ubicacion)].filter(Boolean).join(", ");
  return `<article class="oferta">
    <div class="sello" style="--tono:${tono(oferta.empresa || oferta.titulo)}" aria-hidden="true">${limpio(iniciales(oferta.empresa || oferta.titulo))}</div>
    <div>
      <h3><button type="button" class="titulo" data-id="${limpio(oferta.id)}">${limpio(oferta.titulo)}</button></h3>
      <p class="empresa">${lugar || "Empresa no indicada"}</p>
      <p class="resumen">${limpio(oferta.resumen)}</p>
      ${etiquetas(oferta)}
    </div>
    ${medidor(oferta)}
  </article>`;
}

function parametros() {
  const p = new URLSearchParams({ q: estado.q, modo: estado.modo });
  ["modalidad", "nivel", "area", "fuente"].forEach((c) => estado.filtros[c] && p.set(c, estado.filtros[c]));
  if (estado.filtros.tecnologias.length) p.set("tecnologias", estado.filtros.tecnologias.join(","));
  return p.toString();
}

function hayFiltros() {
  const f = estado.filtros;
  return Boolean(f.modalidad || f.nivel || f.area || f.fuente || f.tecnologias.length);
}

async function buscar() {
  $("#estado").textContent = "Buscando…";
  try {
    const datos = await pedir("/api/buscar?" + parametros());
    const mostrados = datos.resultados.length;
    if (!mostrados) {
      $("#estado").textContent = "";
      $("#resultados").innerHTML = `<div class="vacio"><b>Ninguna oferta coincide</b>${hayFiltros() ? "Quita algún filtro o describe el puesto con otras palabras." : "Describe el puesto con otras palabras o cambia a ordenar por significado."}</div>`;
    } else {
      $("#estado").innerHTML = datos.consulta
        ? `<strong>${datos.total}</strong> ofertas para “${limpio(datos.consulta)}”, orden ${nombre("modo", datos.modo)}. Se muestran las ${mostrados} más relevantes.`
        : `<strong>${datos.total}</strong> ofertas en el corpus. Se muestran las ${mostrados} más recientes.`;
      $("#resultados").innerHTML = datos.resultados.map(tarjeta).join("");
    }
  } catch (error) {
    $("#estado").textContent = error.message;
    $("#resultados").innerHTML = "";
  }
  $("#limpiar").hidden = !hayFiltros();
}

function grupoFiltro(titulo, campo, conteos, maximo) {
  const entradas = Object.entries(conteos || {}).filter(([valor]) => !valor.startsWith("no especific") && valor !== "sin dato").slice(0, maximo);
  if (!entradas.length) return "";
  const botones = entradas.map(([valor, cantidad]) => {
    const activo = campo === "tecnologias" ? estado.filtros.tecnologias.includes(valor) : estado.filtros[campo] === valor;
    return `<button type="button" class="opcion" data-campo="${campo}" data-valor="${limpio(valor)}" aria-pressed="${activo}">${limpio(nombre(campo, valor))} <small>${cantidad}</small></button>`;
  }).join("");
  return `<h3>${titulo}</h3><div class="opciones">${botones}</div>`;
}

function pintarFiltros() {
  const e = corpus && corpus.estadisticas;
  if (!e) {
    $("#grupos-filtro").innerHTML = '<p class="nota">Ejecuta “python main.py analizar” para ver los filtros.</p>';
    return;
  }
  $("#grupos-filtro").innerHTML =
    grupoFiltro("Modalidad", "modalidad", e.por_modalidad, 4) +
    grupoFiltro("Nivel de experiencia", "nivel", e.por_nivel, 5) +
    grupoFiltro("Área", "area", e.por_area, 11) +
    grupoFiltro("Tecnología", "tecnologias", e.tecnologias, 20) +
    grupoFiltro("Fuente", "fuente", e.por_fuente, 10);
}

function barras(conteos, grupo, maximo) {
  const entradas = Object.entries(conteos || {}).slice(0, maximo);
  const tope = Math.max(1, ...entradas.map(([, n]) => n));
  return entradas.map(([valor, n]) =>
    `<div class="fila-barra"><span>${limpio(nombre(grupo, valor))}</span><div class="barra"><i style="width:${(n / tope) * 100}%"></i></div><b>${n}</b></div>`
  ).join("");
}

function panelEvaluacion(ev) {
  if (!ev || !ev.promedio || !ev.promedio.lexico) {
    return `<section class="panel ancho"><h2>Evaluación comparativa</h2><p>Todavía no hay resultados. Ejecuta “python main.py evaluar” y recarga esta página.</p></section>`;
  }
  const metricas = [["precision", `Precisión@${ev.corte}`], ["recall", `Recall@${ev.corte}`], ["map", "MAP"], ["ndcg", `nDCG@${ev.corte}`]];
  const modos = [["lexico", "Palabras", "lex"], ["semantico", "Significado", "sem"], ["hibrido", "Híbrido", "hib"]];
  const bloques = metricas.map(([clave, titulo]) => `<div class="metrica"><h3>${titulo}</h3>${modos.map(([modo, rotulo, clase]) =>
    `<div class="fila-barra"><span>${rotulo}</span><div class="barra ${clase}"><i style="width:${ev.promedio[modo][clave] * 100}%"></i></div><b>${ev.promedio[modo][clave].toFixed(2)}</b></div>`).join("")}</div>`).join("");
  const filas = ev.detalle.map((f) => {
    const mejor = Math.max(f.lexico.ndcg, f.semantico.ndcg, f.hibrido.ndcg);
    const celda = (v) => `<td class="${v === mejor && mejor > 0 ? "mejor" : ""}">${v.toFixed(2)}</td>`;
    return `<tr><td>${limpio(f.consulta)}</td><td>${f.relevantes}</td>${celda(f.lexico.ndcg)}${celda(f.semantico.ndcg)}${celda(f.hibrido.ndcg)}</tr>`;
  }).join("");
  return `<section class="panel ancho">
    <h2>Evaluación comparativa</h2>
    <p>Promedio de ${ev.consultas_evaluadas} consultas de prueba sobre ${ev.documentos} ofertas. Entre más larga la barra, mejor ordena esa estrategia.</p>
    <div class="leyenda"><span><i style="background:var(--lexico)"></i>Palabras exactas (BM25)</span><span><i style="background:var(--semantico)"></i>Significado (embeddings)</span><span><i style="background:var(--marino)"></i>Híbrido</span></div>
    <div class="metricas">${bloques}</div>
    <div class="desplazable"><table>
      <thead><tr><th>Consulta de prueba</th><th>Relevantes</th><th>nDCG palabras</th><th>nDCG significado</th><th>nDCG híbrido</th></tr></thead>
      <tbody>${filas}</tbody>
    </table></div>
    <p class="nota">Los juicios de relevancia son automáticos: una oferta cuenta como relevante si sus campos extraídos (área, nivel, modalidad, tecnologías) cumplen los criterios definidos para la consulta en evaluacion/consultas.json.</p>
  </section>`;
}

function pintarCorpus() {
  const e = corpus && corpus.estadisticas;
  if (!e) {
    $("#corpus").innerHTML = '<div class="vacio"><b>Falta el análisis del corpus</b>Ejecuta “python main.py analizar” y recarga la página.</div>';
    return;
  }
  const i = corpus.indices;
  const lex = i.lexico || {};
  const p = e.proceso;
  const proceso = p ? `<section class="panel ancho"><h2>Del acopio al corpus final</h2><p>Cada oferta cruda pasa por limpieza de HTML y por dos rondas de eliminación de duplicados antes de indexarse.</p>
    <ol class="pasos">
      <li><b>${p.crudas}</b>ofertas crudas acopiadas</li>
      <li><b>${p.sin_texto_suficiente}</b>descartadas por falta de texto</li>
      <li><b>${p.duplicados_exactos}</b>duplicados exactos eliminados</li>
      <li><b>${p.casi_duplicados}</b>casi duplicados eliminados</li>
      <li><b>${p.finales}</b>ofertas en el corpus final</li>
    </ol></section>` : "";
  $("#corpus").innerHTML = `
    <div class="cifras">
      <div class="cifra"><b>${e.total}</b><span>ofertas indexadas</span></div>
      <div class="cifra"><b>${i.dimensiones}</b><span>dimensiones por embedding</span></div>
      <div class="cifra"><b>${lex.terminos ?? e.vocabulario}</b><span>términos en el índice invertido</span></div>
      <div class="cifra"><b>${e.empresas}</b><span>empresas distintas</span></div>
    </div>
    <div class="tablero">
      ${proceso}
      <section class="panel"><h2>Ofertas por fuente</h2><p>Portales y API de donde se acopió cada vacante.</p>${barras(e.por_fuente, "fuente", 10)}</section>
      <section class="panel"><h2>Modalidad de trabajo</h2><p>Detectada del campo original o del texto de la oferta.</p>${barras(e.por_modalidad, "modalidad", 5)}</section>
      <section class="panel ancho"><h2>Tecnologías más solicitadas</h2><p>Número de ofertas que mencionan cada tecnología del diccionario controlado. ${e.sin_tecnologias} ofertas no mencionan ninguna.</p><div class="columnas-2">${barras(e.tecnologias, "tecnologias", 24)}</div></section>
      <section class="panel"><h2>Nivel de experiencia</h2><p>Según título, campo original o años solicitados.</p>${barras(e.por_nivel, "nivel", 6)}</section>
      <section class="panel"><h2>Área del puesto</h2><p>Clasificación por palabras del título y tecnologías.</p>${barras(e.por_area, "area", 12)}</section>
      <section class="panel"><h2>Índice léxico</h2><p>Índice invertido guardado en data/indices/lexico.json.gz.</p>
        <dl class="ficha"><dt>Modelo</dt><dd>${limpio(lex.modelo || "BM25")}</dd><dt>Documentos</dt><dd>${lex.documentos ?? e.total}</dd><dt>Términos</dt><dd>${lex.terminos ?? e.vocabulario}</dd><dt>Postings</dt><dd>${lex.postings ?? ""}</dd><dt>Longitud media</dt><dd>${lex.longitud_promedio ?? e.longitud_media} términos</dd></dl></section>
      <section class="panel"><h2>Índice semántico</h2><p>Vectores guardados en data/indices/vectores.npy.</p>
        <dl class="ficha"><dt>Modelo</dt><dd>${limpio(i.modelo)}</dd><dt>Dimensiones</dt><dd>${i.dimensiones}</dd><dt>Búsqueda</dt><dd>${limpio(i.motor_vectorial)}</dd><dt>Peso en híbrido</dt><dd>${Math.round(corpus.peso_semantico * 100)}% significado, ${Math.round((1 - corpus.peso_semantico) * 100)}% palabras</dd><dt>Idiomas</dt><dd>${Object.entries(e.por_idioma).map(([k, v]) => `${limpio(nombre("idioma", k))} ${v}`).join(", ")}</dd></dl></section>
      ${panelEvaluacion(corpus.evaluacion)}
    </div>`;
}

function columna(clase, titulo, subtitulo, lista, campo) {
  const items = lista.map((r, n) => `<li>
      <span class="puesto">${n + 1}</span>
      <div><button type="button" class="titulo" data-id="${limpio(r.id)}">${limpio(r.titulo)}</button>
        <p>${limpio([r.empresa, nombre("modalidad", r.modalidad)].filter(Boolean).join(", "))}</p>
        ${r.exclusivo ? '<span class="exclusiva">Solo en este ranking</span>' : ""}</div>
      <span class="valor">${Math.round(r[campo])}%</span>
    </li>`).join("");
  return `<div class="columna ${clase}"><header><h2>${titulo}</h2><p>${subtitulo}</p></header><ol>${items || '<li><span></span><div>Sin resultados con estas palabras.</div><span></span></li>'}</ol></div>`;
}

async function comparar(consulta) {
  $("#estado-comparar").textContent = "Comparando…";
  try {
    const d = await pedir("/api/comparar?q=" + encodeURIComponent(consulta));
    $("#estado-comparar").innerHTML = `Los dos rankings coinciden en <strong>${d.coincidencias}</strong> de sus primeras ${Math.max(d.lexico.length, d.semantico.length)} ofertas para “${limpio(d.consulta)}”.`;
    $("#duelo").innerHTML =
      columna("lex", "Palabras exactas", "BM25 sobre el índice invertido", d.lexico, "lexico") +
      columna("sem", "Significado", "Similitud coseno entre embeddings", d.semantico, "semantico");
  } catch (error) {
    $("#estado-comparar").textContent = error.message;
    $("#duelo").innerHTML = "";
  }
}

async function abrirDetalle(id) {
  try {
    const o = await pedir("/api/oferta/" + encodeURIComponent(id));
    const enlace = /^https?:\/\//.test(o.url) && !o.url.includes(".invalid")
      ? `<a class="enlace-original" href="${limpio(o.url)}" target="_blank" rel="noopener noreferrer">Ver la oferta original en ${limpio(o.fuente)}</a>`
      : "";
    $("#detalle-contenido").innerHTML = `
      <div class="detalle-cabeza">
        <div><h2 id="detalle-titulo">${limpio(o.titulo)}</h2><p>${limpio([o.empresa, o.ubicacion, fecha(o.fecha_publicacion)].filter(Boolean).join(", "))}</p></div>
        <button type="button" class="cerrar" id="cerrar-detalle">Cerrar</button>
      </div>
      <div class="detalle-cuerpo">${etiquetas(o)}<div class="descripcion">${limpio(o.descripcion)}</div>${enlace}</div>`;
    $("#detalle").showModal();
  } catch (error) {
    $("#estado").textContent = error.message;
  }
}

function mostrarVista(vista) {
  document.querySelectorAll(".vista").forEach((s) => (s.hidden = s.id !== "vista-" + vista));
  document.querySelectorAll(".pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.vista === vista));
  if (vista === "comparar" && !$("#duelo").innerHTML) {
    const consulta = estado.q || "programador de servicios web y APIs";
    $("#consulta-comparar").value = consulta;
    comparar(consulta);
  }
}

document.addEventListener("click", (evento) => {
  const b = evento.target.closest("button");
  if (!b) {
    if (evento.target === $("#detalle")) $("#detalle").close();
    return;
  }
  if (b.dataset.vista) return mostrarVista(b.dataset.vista);
  if (b.dataset.modo) {
    estado.modo = b.dataset.modo;
    document.querySelectorAll(".modos button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
    return buscar();
  }
  if (b.dataset.ejemplo) {
    $("#consulta").value = estado.q = b.dataset.ejemplo;
    return buscar();
  }
  if (b.dataset.campo) {
    const { campo, valor } = b.dataset;
    if (campo === "tecnologias") {
      const lista = estado.filtros.tecnologias;
      estado.filtros.tecnologias = lista.includes(valor) ? lista.filter((t) => t !== valor) : [...lista, valor];
    } else {
      estado.filtros[campo] = estado.filtros[campo] === valor ? "" : valor;
    }
    pintarFiltros();
    return buscar();
  }
  if (b.id === "limpiar") {
    estado.filtros = { modalidad: "", nivel: "", area: "", fuente: "", tecnologias: [] };
    pintarFiltros();
    return buscar();
  }
  if (b.id === "cerrar-detalle") return $("#detalle").close();
  if (b.dataset.id) return abrirDetalle(b.dataset.id);
});

$("#formulario").addEventListener("submit", (evento) => {
  evento.preventDefault();
  estado.q = $("#consulta").value.trim();
  buscar();
});

$("#formulario-comparar").addEventListener("submit", (evento) => {
  evento.preventDefault();
  const consulta = $("#consulta-comparar").value.trim();
  if (consulta) comparar(consulta);
});

(async function iniciar() {
  try {
    corpus = await pedir("/api/corpus");
  } catch (error) {
    corpus = null;
  }
  pintarFiltros();
  pintarCorpus();
  buscar();
})();
