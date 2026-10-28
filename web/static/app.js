const $ = (selector, raiz = document) => raiz.querySelector(selector);
const $$ = (selector, raiz = document) => [...raiz.querySelectorAll(selector)];

const estado = {
  q: "",
  modo: "hibrido",
  filtros: { modalidad: "", nivel: "", area: "", idioma: "", fuente: "", tecnologias: [] },
  vista: "buscar",
  corpus: null,
  texto: null,
  datos: null,
  ultimo: null,
  muestra: 0,
  fuenteFrec: "frecuencias",
  ngrama: "2",
  tema: localStorage.getItem("sysjobs-tema") || "claro",
  peticion: 0,
};

const NOMBRES = {
  modalidad: { remoto: "Remoto", hibrido: "Híbrido", presencial: "Presencial", "no especificada": "Sin especificar" },
  nivel: { practicante: "Prácticas", junior: "Junior", "semi-senior": "Semi senior", senior: "Senior", "no especificado": "Sin especificar" },
  area: {
    backend: "Backend", frontend: "Frontend", fullstack: "Full stack", movil: "Móvil", datos: "Datos",
    devops: "DevOps y nube", qa: "Pruebas y QA", seguridad: "Seguridad", soporte: "Soporte y redes",
    "desarrollo general": "Desarrollo general", otra: "Otra",
  },
  idioma: { es: "Español", en: "Inglés", de: "Alemán", fr: "Francés", desconocido: "Sin detectar" },
  modo: { hibrido: "híbrido", semantico: "por significado", lexico: "por palabras exactas", recientes: "por fecha" },
};

const ICONOS = {
  remoto: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11 12 4l9 7"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/></svg>',
  hibrido: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12 7 8l5 4"/><path d="M4 11v8h6v-8"/><path d="M14 19V5h7v14"/><path d="M17 9h1M17 13h1"/></svg>',
  presencial: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 20V4h14v16"/><path d="M3 20h18"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M11 20v-4h2v4"/></svg>',
  altavoz: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 10v4h4l5 4V6l-5 4H4Z"/><path d="M16 9.5a4 4 0 0 1 0 5M18.5 7a7 7 0 0 1 0 10"/></svg>',
  flecha: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
};

const TITULOS = { buscar: "Buscar", comparar: "Comparar rankings", texto: "Laboratorio de texto", datos: "Datos y exportación", corpus: "Corpus e índices" };

function limpio(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function numero(n) {
  const valor = Number(n);
  return Number.isFinite(valor) ? valor.toLocaleString("es-MX") : "—";
}

function nombre(grupo, valor) {
  return (NOMBRES[grupo] && NOMBRES[grupo][valor]) || valor || "Sin dato";
}

function fecha(iso) {
  if (!iso) return "";
  const [a, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  if (!a || !m || !d) return iso;
  return new Date(a, m - 1, d).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
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

function resaltar(texto, consulta) {
  const seguro = limpio(texto);
  const terminos = String(consulta || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .split(/[^a-z0-9+#.]+/).filter((t) => t.length > 2).slice(0, 7);
  if (!terminos.length) return seguro;
  const patron = terminos.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  try { return seguro.replace(new RegExp(`(${patron})`, "gi"), "<mark>$1</mark>"); } catch { return seguro; }
}

async function pedir(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, opciones);
  let datos = {};
  try { datos = await respuesta.json(); } catch { datos = {}; }
  if (!respuesta.ok) throw new Error(datos.error || `No se pudo completar la solicitud (${respuesta.status}).`);
  return datos;
}

function toast(mensaje, tipo = "") {
  const caja = document.createElement("div");
  caja.className = `toast ${tipo}`.trim();
  caja.textContent = mensaje;
  $("#toasts").appendChild(caja);
  setTimeout(() => { caja.style.opacity = "0"; caja.style.transform = "translateY(6px)"; }, 4200);
  setTimeout(() => caja.remove(), 4700);
}

/* ------------------------------------------------------------------ */
/* Voz: reconocimiento y síntesis                                     */
/* ------------------------------------------------------------------ */
const Voz = {
  reconocimiento: null,
  activo: false,
  soportado: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
  sintesis: "speechSynthesis" in window,
  utterance: null,

  iniciar() {
    const boton = $("#micro");
    if (this.activo) { this.detener(); return; }
    if (!this.soportado) {
      toast("Tu navegador no permite dictado por voz. Prueba con Chrome o Edge.", "error");
      return;
    }
    const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;
    const reconocimiento = new Reconocimiento();
    reconocimiento.lang = "es-MX";
    reconocimiento.interimResults = true;
    reconocimiento.continuous = false;
    reconocimiento.maxAlternatives = 1;
    reconocimiento.onstart = () => {
      this.activo = true;
      boton.classList.add("escuchando");
      boton.setAttribute("aria-pressed", "true");
      $("#voz-estado").textContent = "Escuchando… habla ahora y pulsa de nuevo para detener.";
    };
    reconocimiento.onresult = (evento) => {
      const texto = [...evento.results].map((r) => r[0].transcript).join(" ").trim();
      $("#consulta").value = texto;
      estado.q = texto;
      const final = evento.results[evento.results.length - 1].isFinal;
      if (final && texto) {
        $("#voz-estado").textContent = `Entendí: “${texto}”. Buscando…`;
        setTimeout(() => buscar(), 350);
      }
    };
    reconocimiento.onerror = (evento) => {
      const mensajes = {
        "not-allowed": "El navegador bloqueó el micrófono. Revisa los permisos del sitio.",
        "no-speech": "No se escuchó nada. Intenta de nuevo.",
        "audio-capture": "No se encontró un micrófono disponible.",
        network: "El servicio de dictado necesita conexión a internet.",
      };
      toast(mensajes[evento.error] || "No se pudo usar el micrófono.", "error");
    };
    reconocimiento.onend = () => {
      this.activo = false;
      boton.classList.remove("escuchando");
      boton.setAttribute("aria-pressed", "false");
      setTimeout(() => {
        if (!this.activo && $("#voz-estado")) $("#voz-estado").textContent = "";
      }, 1800);
    };
    try {
      reconocimiento.start();
      this.reconocimiento = reconocimiento;
    } catch {
      toast("El dictado ya estaba activo. Espera un momento e inténtalo otra vez.", "error");
    }
  },

  detener() {
    if (this.reconocimiento) this.reconocimiento.stop();
    this.activo = false;
    $("#micro")?.classList.remove("escuchando");
    $("#micro")?.setAttribute("aria-pressed", "false");
    if ($("#voz-estado")) $("#voz-estado").textContent = "Dictado detenido.";
  },

  hablar(texto, boton = null) {
    if (!this.sintesis) {
      toast("Tu navegador no permite síntesis de voz.", "error");
      return;
    }
    const limpioTexto = String(texto || "").replace(/\s+/g, " ").trim();
    if (!limpioTexto) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(limpioTexto.slice(0, 2200));
    utterance.lang = "es-MX";
    utterance.rate = 1.02;
    utterance.pitch = 1;
    const voces = window.speechSynthesis.getVoices();
    const voz = voces.find((v) => /es[-_]MX/i.test(v.lang)) || voces.find((v) => /^es/i.test(v.lang));
    if (voz) utterance.voice = voz;
    if (boton) { boton.dataset.hablando = "1"; boton.setAttribute("aria-pressed", "true"); }
    utterance.onend = utterance.onerror = () => {
      if (boton) { boton.dataset.hablando = ""; boton.setAttribute("aria-pressed", "false"); }
      if ($("#voz-estado")) $("#voz-estado").textContent = "";
    };
    this.utterance = utterance;
    if ($("#voz-estado")) $("#voz-estado").textContent = "Leyendo en voz alta…";
    window.speechSynthesis.speak(utterance);
  },
};

if (Voz.sintesis) window.speechSynthesis.onvoiceschanged = () => {};

/* ------------------------------------------------------------------ */
/* Tarjetas y resultados                                              */
/* ------------------------------------------------------------------ */
function anillo(valor) {
  const v = Math.max(0, Math.min(100, Number(valor) || 0));
  const circunferencia = 2 * Math.PI * 26;
  return `<div class="anillo" title="Relevancia ${Math.round(v)}%">
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <circle class="pista" cx="32" cy="32" r="26"/>
      <circle class="valor" cx="32" cy="32" r="26" stroke="url(#gradAnillo)" stroke-dasharray="${circunferencia.toFixed(1)}" stroke-dashoffset="${(circunferencia * (1 - v / 100)).toFixed(1)}"/>
    </svg>
    <b>${Math.round(v)}<small>%</small></b>
  </div>`;
}

function etiquetasOferta(oferta) {
  const piezas = [];
  if (oferta.modalidad && oferta.modalidad !== "no especificada") {
    piezas.push(`<li class="clave">${ICONOS[oferta.modalidad] || ""}${limpio(nombre("modalidad", oferta.modalidad))}</li>`);
  }
  if (oferta.nivel && oferta.nivel !== "no especificado") {
    piezas.push(`<li class="nivel">${limpio(nombre("nivel", oferta.nivel))}</li>`);
  }
  (oferta.tecnologias || []).slice(0, 7).forEach((t) => piezas.push(`<li>${limpio(t)}</li>`));
  if ((oferta.tecnologias || []).length > 7) piezas.push(`<li>+${oferta.tecnologias.length - 7}</li>`);
  return `<ul class="etiquetas">${piezas.join("")}</ul>`;
}

function medidor(oferta) {
  const origen = `<span class="origen">${limpio(oferta.fuente)}${oferta.fecha_publicacion ? " · " + fecha(oferta.fecha_publicacion) : ""}</span>`;
  if (oferta.relevancia === null || oferta.relevancia === undefined) {
    return `<div class="oferta-lado"><span class="badge-fuente">reciente</span>${origen}
      <div class="acciones-tarjeta"><button type="button" class="boton-icono" data-leer-id="${limpio(oferta.id)}" aria-label="Escuchar oferta">${ICONOS.altavoz}</button></div></div>`;
  }
  return `<div class="oferta-lado">
    ${anillo(oferta.relevancia)}
    <div class="senales">
      <div class="senal"><span>Significado <b>${Math.round(oferta.semantico)}</b></span><div class="barra sem"><i style="width:${oferta.semantico}%"></i></div></div>
      <div class="senal"><span>Palabras <b>${Math.round(oferta.lexico)}</b></span><div class="barra lex"><i style="width:${oferta.lexico}%"></i></div></div>
    </div>
    <div class="acciones-tarjeta">
      <button type="button" class="boton-icono" data-leer-id="${limpio(oferta.id)}" aria-label="Escuchar oferta">${ICONOS.altavoz}</button>
      <button type="button" class="boton-icono" data-id="${limpio(oferta.id)}" aria-label="Ver detalle">${ICONOS.flecha}</button>
    </div>
    ${origen}
  </div>`;
}

function tarjeta(oferta) {
  const lugar = [oferta.empresa ? `<b>${limpio(oferta.empresa)}</b>` : "", limpio(oferta.ubicacion)].filter(Boolean).join(", ");
  return `<article class="oferta">
    <div class="sello" style="--tono:${tono(oferta.empresa || oferta.titulo)}" aria-hidden="true">${limpio(iniciales(oferta.empresa || oferta.titulo))}</div>
    <div class="oferta-cuerpo">
      <div class="oferta-top">
        <h3><button type="button" class="titulo" data-id="${limpio(oferta.id)}">${limpio(oferta.titulo)}</button></h3>
        <span class="badge-fuente">${limpio(oferta.fuente)}</span>
      </div>
      <p class="empresa">${lugar || "Empresa no indicada"}</p>
      <p class="resumen">${resaltar(oferta.resumen, estado.q)}</p>
      ${etiquetasOferta(oferta)}
    </div>
    ${medidor(oferta)}
  </article>`;
}

function parametros() {
  const p = new URLSearchParams({ q: estado.q, modo: estado.modo, k: "24" });
  ["modalidad", "nivel", "area", "idioma", "fuente"].forEach((c) => estado.filtros[c] && p.set(c, estado.filtros[c]));
  if (estado.filtros.tecnologias.length) p.set("tecnologias", estado.filtros.tecnologias.join(","));
  return p.toString();
}

function hayFiltros() {
  const f = estado.filtros;
  return Boolean(f.modalidad || f.nivel || f.area || f.idioma || f.fuente || f.tecnologias.length);
}

function pintarChips() {
  const etiquetas = [];
  ["modalidad", "nivel", "area", "idioma", "fuente"].forEach((campo) => {
    if (estado.filtros[campo]) {
      etiquetas.push(`<span class="chip-activo">${limpio(nombre(campo, estado.filtros[campo]))}<button type="button" data-quitar="${campo}" aria-label="Quitar filtro">×</button></span>`);
    }
  });
  estado.filtros.tecnologias.forEach((tecnologia) => {
    etiquetas.push(`<span class="chip-activo">${limpio(tecnologia)}<button type="button" data-quitar="tecnologias" data-valor="${limpio(tecnologia)}" aria-label="Quitar tecnología">×</button></span>`);
  });
  $("#chips-activos").innerHTML = etiquetas.join("");
  $("#limpiar").hidden = !hayFiltros();
}

async function buscar() {
  const actual = ++estado.peticion;
  $("#estado").textContent = "Buscando coincidencias…";
  $("#resultados").innerHTML = Array.from({ length: 4 }, () => '<div class="skeleton"></div>').join("");
  try {
    const datos = await pedir("/api/buscar?" + parametros());
    if (actual !== estado.peticion) return;
    estado.ultimo = datos;
    const mostrados = datos.resultados.length;
    if (!mostrados) {
      $("#estado").textContent = "";
      $("#resultados").innerHTML = `<div class="vacio"><b>Ninguna oferta coincide</b><span>${hayFiltros() ? "Quita algún filtro o describe el puesto con otras palabras." : "Describe el puesto con otras palabras o cambia a ordenar por significado."}</span></div>`;
    } else {
      $("#estado").innerHTML = datos.consulta
        ? `<strong>${numero(datos.total)}</strong> ofertas para “${limpio(datos.consulta)}” · orden ${nombre("modo", datos.modo)} · mostrando ${mostrados}`
        : `<strong>${numero(datos.total)}</strong> ofertas en el corpus · mostrando las ${mostrados} más recientes`;
      $("#resultados").innerHTML = datos.resultados.map(tarjeta).join("");
    }
  } catch (error) {
    if (actual !== estado.peticion) return;
    $("#estado").textContent = error.message;
    $("#resultados").innerHTML = `<div class="vacio"><b>No se pudo buscar</b><span>${limpio(error.message)}</span></div>`;
    toast(error.message, "error");
  }
  pintarChips();
}

function grupoFiltro(titulo, campo, conteos, maximo, abierto = false) {
  const entradas = Object.entries(conteos || {})
    .filter(([valor]) => valor && !valor.startsWith("no especific") && valor !== "sin dato")
    .slice(0, maximo);
  if (!entradas.length) return "";
  const botones = entradas.map(([valor, cantidad]) => {
    const activo = campo === "tecnologias" ? estado.filtros.tecnologias.includes(valor) : estado.filtros[campo] === valor;
    return `<button type="button" class="opcion" data-campo="${campo}" data-valor="${limpio(valor)}" aria-pressed="${activo}">${limpio(nombre(campo, valor))} <small>${numero(cantidad)}</small></button>`;
  }).join("");
  return `<details class="grupo" ${abierto ? "open" : ""}><summary>${titulo}</summary><div class="opciones">${botones}</div></details>`;
}

function pintarFiltros() {
  const e = estado.corpus && estado.corpus.estadisticas;
  if (!e) {
    $("#grupos-filtro").innerHTML = '<p class="nota">Ejecuta <code>python main.py analizar</code> para ver los filtros.</p>';
  } else {
    $("#grupos-filtro").innerHTML =
      grupoFiltro("Modalidad", "modalidad", e.por_modalidad, 4, true) +
      grupoFiltro("Nivel", "nivel", e.por_nivel, 5, true) +
      grupoFiltro("Área", "area", e.por_area, 11) +
      grupoFiltro("Tecnología", "tecnologias", e.tecnologias, 22) +
      grupoFiltro("Idioma", "idioma", e.por_idioma, 5) +
      grupoFiltro("Fuente", "fuente", e.por_fuente, 10);
  }
  pintarChips();
}

/* ------------------------------------------------------------------ */
/* Laboratorio de texto                                               */
/* ------------------------------------------------------------------ */
function barras(conteos, maximo, grupo) {
  const entradas = Object.entries(conteos || {}).slice(0, maximo);
  const tope = Math.max(1, ...entradas.map(([, n]) => n));
  return `<div class="grafico">${entradas.map(([valor, n]) =>
    `<div class="fila-grafico"><span class="nombre" title="${limpio(nombre(grupo, valor))}">${limpio(nombre(grupo, valor))}</span><div class="barra"><i style="width:${(n / tope) * 100}%"></i></div><b>${numero(n)}</b></div>`
  ).join("")}</div>`;
}

function barrasTerminos(datos, maximo = 18) {
  const entradas = (datos || []).slice(0, maximo);
  const tope = Math.max(1, ...entradas.map(([, n]) => n));
  return `<div class="grafico">${entradas.map(([termino, total, df]) =>
    `<div class="fila-grafico"><span class="nombre" title="${limpio(termino)} · ${numero(total)} apariciones · ${numero(df)} ofertas">${limpio(termino)}</span><div class="barra"><i style="width:${(total / tope) * 100}%"></i></div><b>${numero(total)}</b></div>`
  ).join("")}</div>`;
}

function nube(datos) {
  const entradas = (datos || []).slice(0, 55);
  if (!entradas.length) return '<p class="nota">Sin datos de frecuencia.</p>';
  const tope = Math.max(1, ...entradas.map(([, n]) => n));
  return `<div class="nube">${entradas.map(([termino, n]) => {
    const escala = 0.72 + (n / tope) * 1.55;
    return `<span style="font-size:${escala.toFixed(2)}rem" title="${numero(n)} apariciones">${limpio(termino)}</span>`;
  }).join("")}</div>`;
}

function renderFrecuencias() {
  const d = estado.texto;
  if (!d) return;
  const mapa = {
    frecuencias: d.frecuencias,
    derivadas: d.derivadas,
    palabras_vacias: (d.palabras_vacias || []).map(([t, n]) => [t, n, n]),
  };
  const datos = mapa[estado.fuenteFrec] || [];
  $("#grafico-frecuencias").innerHTML = datos.length
    ? barrasTerminos(datos, 20)
    : '<p class="nota">Sin datos para esta representación.</p>';
  $$("#texto-contenido [data-fuente-frec]").forEach((b) => b.classList.toggle("activa", b.dataset.fuenteFrec === estado.fuenteFrec));
}

function renderNgramas() {
  const d = estado.texto;
  if (!d) return;
  const filas = (d.ngramas && d.ngramas[estado.ngrama]) || [];
  $("#tabla-ngramas").innerHTML = filas.length ? `<div class="tabla-envoltura"><table>
    <thead><tr><th>${estado.ngrama === "2" ? "Bigrama" : "Trigrama"}</th><th>Apariciones</th><th>Ofertas</th></tr></thead>
    <tbody>${filas.slice(0, 16).map(([gram, total, df]) => `<tr><td>${limpio(gram)}</td><td>${numero(total)}</td><td>${numero(df)}</td></tr>`).join("")}</tbody>
  </table></div>` : '<p class="nota">Sin n-gramas.</p>';
  $$("#texto-contenido [data-ngrama]").forEach((b) => b.classList.toggle("activa", b.dataset.ngrama === estado.ngrama));
}

function pintarTexto() {
  const d = estado.texto;
  const contenedor = $("#texto-contenido");
  if (!d || !d.resumen) {
    contenedor.innerHTML = `<div class="vacio"><b>Falta el análisis de texto</b><span>Ejecuta <code>python main.py analizar</code> y recarga la página.</span></div>`;
    return;
  }
  const r = d.resumen;
  const muestras = d.muestras || [];
  const muestra = muestras[Math.min(estado.muestra, Math.max(0, muestras.length - 1))] || null;
  const muestraTabs = muestras.length > 1
    ? `<div class="tabs">${muestras.map((m, i) => `<button type="button" data-muestra="${i}" class="${i === estado.muestra ? "activa" : ""}">${limpio(m.idioma ? nombre("idioma", m.idioma) : "Muestra " + (i + 1))}</button>`).join("")}</div>`
    : "";
  const chips = muestra ? muestra.detalle.map((item) => {
    const cambio = item.lema !== item.palabra;
    return `<span class="${item.vacia ? "vacia" : ""}" title="lema: ${limpio(item.lema)} · raíz: ${limpio(item.derivada)}">${limpio(item.palabra)}${cambio ? ` <b>→ ${limpio(item.lema)}</b>` : ""}</span>`;
  }).join("") : "";
  const tablaLemas = (d.lematizacion || []).map(([palabra, lema, derivada]) =>
    `<tr><td>${limpio(palabra)}</td><td>${limpio(lema)}</td><td><span class="pildora">${limpio(derivada)}</span></td></tr>`
  ).join("");

  contenedor.innerHTML = `
    <div class="kpis">
      <div class="kpi acento"><b>${numero(r.tokens)}</b><span>tokens útiles</span></div>
      <div class="kpi"><b>${numero(r.tipos)}</b><span>lemas distintos</span></div>
      <div class="kpi"><b>${numero(r.hapax)}</b><span>hapax (aparecen 1 vez)</span></div>
      <div class="kpi"><b>${r.reduccion_tokens}%</b><span>menos ruido</span></div>
      <div class="kpi"><b>${numero(r.ngramas_distintos?.["2"] || 0)}</b><span>bigramas distintos</span></div>
    </div>

    <section class="panel ancho">
      <div class="panel-cabeza"><div><h2>Pipeline de preprocesamiento</h2><p>El mismo recorrido se aplica a las ofertas y a tu consulta.</p></div></div>
      <div class="pipeline">${(d.pipeline || []).map((p, i) => `<div class="paso"><span class="num">${i + 1}</span><h3>${limpio(p.nombre)}</h3><p>${limpio(p.descripcion)}</p><small>${limpio(p.detalle)}</small></div>`).join("")}</div>
    </section>

    <div class="rejilla-2" style="margin-top:1.1rem">
      <section class="panel ancho" style="grid-column:1/-1">
        <div class="panel-cabeza"><div><h2>Antes y después</h2><p>Una oferta real recorre limpieza, normalización, tokenización, palabras vacías, lematización y derivación.</p></div>${muestraTabs}</div>
        ${muestra ? `
          <div class="comparador">
            <div><h3>Texto original</h3><pre>${limpio(muestra.original)}</pre></div>
            <div><h3>Normalizado y limpio</h3><pre>${limpio(muestra.normalizado)}</pre></div>
          </div>
          <div class="chips-tokens">${chips}</div>
          <p class="nota">${numero(muestra.estadisticas.tokens_brutos)} tokens → ${numero(muestra.estadisticas.tokens_utiles)} útiles; ${numero(muestra.estadisticas.palabras_vacias)} palabras vacías; ${numero(muestra.estadisticas.tipos)} tipos.</p>
          <div class="chips-tokens">${(muestra.ngramas || []).map((g) => `<span>${limpio(g)}</span>`).join("")}</div>
        ` : '<p class="nota">Sin muestras disponibles.</p>'}
      </section>
    </div>

    <div class="rejilla-2" style="margin-top:1.1rem">
      <section class="panel">
        <div class="panel-cabeza"><div><h2>Palabras más frecuentes</h2><p>Frecuencia total; el tooltip muestra en cuántas ofertas aparece.</p></div></div>
        <div class="tabs">
          <button type="button" data-fuente-frec="frecuencias" class="${estado.fuenteFrec === "frecuencias" ? "activa" : ""}">Lemas</button>
          <button type="button" data-fuente-frec="derivadas" class="${estado.fuenteFrec === "derivadas" ? "activa" : ""}">Raíces</button>
          <button type="button" data-fuente-frec="palabras_vacias" class="${estado.fuenteFrec === "palabras_vacias" ? "activa" : ""}">Vacías</button>
        </div>
        <div id="grafico-frecuencias"></div>
      </section>
      <section class="panel">
        <div class="panel-cabeza"><div><h2>Nube de lemas</h2><p>Tamaño proporcional a la frecuencia en todo el corpus.</p></div></div>
        ${nube(d.nube)}
      </section>
    </div>

    <section class="panel ancho" style="margin-top:1.1rem">
      <div class="panel-cabeza"><div><h2>N-gramas</h2><p>Secuencias consecutivas de palabras que revelan expresiones frecuentes.</p></div>
        <div class="tabs">
          <button type="button" data-ngrama="2" class="${estado.ngrama === "2" ? "activa" : ""}">Bigramas</button>
          <button type="button" data-ngrama="3" class="${estado.ngrama === "3" ? "activa" : ""}">Trigramas</button>
        </div>
      </div>
      <div id="tabla-ngramas"></div>
    </section>

    <section class="panel ancho" style="margin-top:1.1rem">
      <div class="panel-cabeza"><div><h2>Lematización y derivación</h2><p>Ejemplos reales de palabras que cambiaron al reducirse a su lema y a su raíz.</p></div></div>
      <div class="tabla-envoltura"><table>
        <thead><tr><th>Palabra</th><th>Lema</th><th>Raíz derivada</th></tr></thead>
        <tbody>${tablaLemas || '<tr><td colspan="3">Sin ejemplos.</td></tr>'}</tbody>
      </table></div>
      <p class="nota">Reglas basadas en diccionario y sufijos para español e inglés, sin dependencias externas. La estrategia activa de indexación es <b>${limpio(r.estrategia)}</b> y el vocabulario de palabras vacías tiene ${numero(r.stopwords)} entradas.</p>
    </section>`;
  renderFrecuencias();
  renderNgramas();
}

/* ------------------------------------------------------------------ */
/* Datos y exportación                                                */
/* ------------------------------------------------------------------ */
function archivoDe(datos, idFormato, archivo) {
  const grupo = idFormato === "mongodb" ? "no_relacional" : "procesado";
  return (datos.archivos || []).find((a) => a.grupo === grupo && a.nombre.endsWith(archivo));
}

function pintarDatos() {
  const d = estado.datos;
  const contenedor = $("#datos-contenido");
  if (!d) {
    contenedor.innerHTML = '<div class="vacio"><b>Sin información de archivos</b><span>Recarga la página o ejecuta <code>python main.py procesar</code>.</span></div>';
    return;
  }
  const formatos = (d.formatos || []).map((f) => {
    const archivo = archivoDe(d, f.id, f.archivo);
    return `<article class="formato">
      <div class="icono-formato">${f.nombre.slice(0, 4).toUpperCase()}</div>
      <h3>${limpio(f.nombre)}</h3>
      <p>${limpio(f.descripcion)}</p>
      <span class="meta">${archivo ? `${archivo.tamano} · ${archivo.nombre}` : "Por generar"}</span>
      ${archivo ? `<a href="${archivo.descarga}">Descargar ↓</a>` : ""}
    </article>`;
  }).join("");

  const archivos = (d.archivos || []).map((a) => `<div class="archivo">
    <span class="nombre" title="${limpio(a.nombre)}">${limpio(a.nombre)}</span>
    <span class="grupo">${limpio(a.grupo)}</span>
    <span class="tamano">${limpio(a.tamano)}</span>
    <a href="${a.descarga}">Descargar</a>
  </div>`).join("");

  const esquema = (d.esquema_relacional || []).map((t) => `<div class="tabla-esquema">
    <header><b>${limpio(t.tabla)}</b><span>${numero(t.filas)} filas</span></header>
    <ul>${t.columnas.map((c) => `<li><b>${limpio(c.nombre)}</b><span>${limpio(c.tipo.toLowerCase())}${c.rol ? ` <i class="rol">${limpio(c.rol)}</i>` : ""}</span></li>`).join("")}</ul>
  </div>`).join("");

  const comandos = (d.comandos || []).map((c, i) => `<div class="codigo">
    <div class="codigo-cabeza"><span>${limpio(c.titulo)} · ${limpio(c.lenguaje)}</span><button type="button" data-copiar="codigo-${i}">Copiar</button></div>
    <code id="codigo-${i}">${limpio(c.codigo)}</code>
  </div>`).join("");

  contenedor.innerHTML = `
    <div class="kpis">
      <div class="kpi acento"><b>${numero(d.conteos?.ofertas)}</b><span>ofertas exportadas</span></div>
      <div class="kpi"><b>${numero(d.conteos?.empresas)}</b><span>empresas</span></div>
      <div class="kpi"><b>${numero(d.conteos?.tecnologias)}</b><span>tecnologías</span></div>
      <div class="kpi"><b>${numero(d.archivos?.length)}</b><span>archivos generados</span></div>
      <div class="kpi"><b>${limpio(d.total_legible || "—")}</b><span>tamaño total</span></div>
    </div>

    <section class="panel ancho">
      <div class="panel-cabeza"><div><h2>Formatos disponibles</h2><p>La misma información en cinco representaciones. Todas se regeneran desde el corpus procesado.</p></div>
        <button type="button" class="boton-fantasma" id="regenerar-2">Regenerar</button></div>
      <div class="formatos">${formatos}</div>
    </section>

    <div class="rejilla-2" style="margin-top:1.1rem">
      <section class="panel">
        <div class="panel-cabeza"><div><h2>Archivos generados</h2><p>Descarga directa desde el servidor local.</p></div></div>
        <div class="archivos">${archivos}</div>
      </section>
      <section class="panel">
        <div class="panel-cabeza"><div><h2>Documento de ejemplo</h2><p>Así se ve una oferta en el modelo no relacional.</p></div></div>
        <div class="codigo documento"><code>${limpio(JSON.stringify(d.documento_ejemplo || {}, null, 2))}</code></div>
      </section>
    </div>

    <section class="panel ancho" style="margin-top:1.1rem">
      <div class="panel-cabeza"><div><h2>Esquema relacional</h2><p>Modelo normalizado en SQLite: catálogos, tabla de ofertas y relación N:M con tecnologías.</p></div></div>
      <div class="esquema">${esquema || '<p class="nota">Sin base de datos. Ejecuta <code>python main.py procesar</code>.</p>'}</div>
    </section>

    <section class="panel ancho" style="margin-top:1.1rem">
      <div class="panel-cabeza"><div><h2>Consultas y carga</h2><p>Comandos listos para usar sobre los archivos generados.</p></div></div>
      <div class="rejilla-2">${comandos}</div>
    </section>`;
}

async function cargarDatos(forzar = false) {
  if (estado.datos && !forzar) { pintarDatos(); return; }
  try {
    estado.datos = await pedir("/api/datos");
    pintarDatos();
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ------------------------------------------------------------------ */
/* Corpus, índices y evaluación                                       */
/* ------------------------------------------------------------------ */
function panelEvaluacion(ev) {
  if (!ev || !ev.promedio || !ev.promedio.lexico) {
    return `<section class="panel ancho"><h2>Evaluación comparativa</h2><p>Todavía no hay resultados. Ejecuta <code>python main.py evaluar</code> y recarga.</p></section>`;
  }
  const metricas = [["precision", `Precisión@${ev.corte}`], ["recall", `Recall@${ev.corte}`], ["map", "MAP"], ["ndcg", `nDCG@${ev.corte}`]];
  const modos = [["lexico", "Palabras", "lex"], ["semantico", "Significado", "sem"], ["hibrido", "Híbrido", "hib"]];
  const bloques = metricas.map(([clave, titulo]) => `<div class="metrica"><h3>${titulo}</h3>${modos.map(([modo, rotulo, clase]) =>
    `<div class="fila-grafico"><span class="nombre">${rotulo}</span><div class="barra ${clase}"><i style="width:${ev.promedio[modo][clave] * 100}%"></i></div><b>${ev.promedio[modo][clave].toFixed(2)}</b></div>`).join("")}</div>`).join("");
  const filas = (ev.detalle || []).map((f) => {
    const mejor = Math.max(f.lexico.ndcg, f.semantico.ndcg, f.hibrido.ndcg);
    const celda = (v) => `<td class="${v === mejor && mejor > 0 ? "mejor" : ""}">${v.toFixed(2)}</td>`;
    return `<tr><td>${limpio(f.consulta)}</td><td>${f.relevantes}</td>${celda(f.lexico.ndcg)}${celda(f.semantico.ndcg)}${celda(f.hibrido.ndcg)}</tr>`;
  }).join("");
  return `<section class="panel ancho">
    <div class="panel-cabeza"><div><h2>Evaluación comparativa</h2><p>Promedio de ${ev.consultas_evaluadas} consultas sobre ${numero(ev.documentos)} ofertas. Más barra = mejor ordena esa estrategia.</p></div></div>
    <div class="leyenda"><span><i style="background:var(--lexico)"></i>Palabras exactas (BM25)</span><span><i style="background:var(--semantico)"></i>Significado (embeddings)</span><span><i style="background:var(--acento)"></i>Híbrido</span></div>
    <div class="metricas">${bloques}</div>
    <div class="tabla-envoltura"><table>
      <thead><tr><th>Consulta de prueba</th><th>Relevantes</th><th>nDCG palabras</th><th>nDCG significado</th><th>nDCG híbrido</th></tr></thead>
      <tbody>${filas}</tbody>
    </table></div>
    <p class="nota">Juicios automáticos: una oferta es relevante si sus campos extraídos (área, nivel, modalidad, tecnologías) cumplen los criterios definidos en <code>evaluacion/consultas.json</code>.</p>
  </section>`;
}

function pintarCorpus() {
  const c = estado.corpus;
  const e = c && c.estadisticas;
  const contenedor = $("#corpus");
  if (!e) {
    contenedor.innerHTML = `<div class="vacio"><b>Falta el análisis del corpus</b><span>Ejecuta <code>python main.py construir</code> y recarga la página.</span></div>`;
    return;
  }
  const i = c.indices || {};
  const lex = i.lexico || {};
  const p = e.proceso;
  const v = c.vectorizacion || {};
  const proceso = p ? `<section class="panel ancho"><div class="panel-cabeza"><div><h2>Del acopio al corpus final</h2><p>Cada oferta cruda pasa por limpieza de HTML y dos rondas de eliminación de duplicados antes de indexarse.</p></div></div>
    <ol class="pasos">
      <li><b>${numero(p.crudas)}</b>ofertas crudas</li>
      <li><b>${numero(p.sin_texto_suficiente)}</b>sin texto suficiente</li>
      <li><b>${numero(p.duplicados_exactos)}</b>duplicados exactos</li>
      <li><b>${numero(p.casi_duplicados)}</b>casi duplicados</li>
      <li><b>${numero(p.finales)}</b>ofertas finales</li>
    </ol></section>` : "";
  const vector = v.matriz ? `<section class="panel ancho">
    <div class="panel-cabeza"><div><h2>Vectorización</h2><p>Cómo se convierte una oferta en una fila de números. La matriz TF-IDF es dispersa; los embeddings son densos.</p></div>
      <a class="boton-fantasma" href="/descargas/indices/${encodeURIComponent("estructura.json")}">Ver estructura.json</a></div>
    <div class="rejilla-2">
      <div>
        <dl class="ficha">
          <dt>Matriz TF-IDF</dt><dd>${numero(v.matriz.documentos)} × ${numero(v.matriz.dimensiones)}</dd>
          <dt>Valores no cero</dt><dd>${numero(v.matriz.valores_no_cero)} de ${numero(v.matriz.celdas_totales)}</dd>
          <dt>Densidad</dt><dd>${v.matriz.densidad_pct}%</dd>
          <dt>TF-IDF medio</dt><dd>${v.matriz.tfidf_medio}</dd>
          <dt>Vocabulario</dt><dd>${numero(v.vocabulario?.terminos)} términos</dd>
          <dt>Embeddings</dt><dd>${numero(v.embeddings?.dimensiones)} dimensiones · ${limpio(v.embeddings?.motor_vectorial || "")}</dd>
        </dl>
      </div>
      <div>
        <h3 style="font-size:.82rem;margin-bottom:.45rem">Vector de ejemplo: ${limpio(v.vector_ejemplo?.titulo || "")}</h3>
        <div class="chips-tokens">${(v.vector_ejemplo?.componentes || []).map(([t, w]) => `<span title="peso TF-IDF">${limpio(t)} <b>${w}</b></span>`).join("")}</div>
        <p class="nota">Solo se muestran los componentes con mayor peso. El resto de las ${numero(v.vector_ejemplo?.dimensiones)} dimensiones vale cero: eso es la dispersión.</p>
      </div>
    </div>
    <div class="chips-tokens" style="margin-top:.8rem">${(v.esquema || []).map((x) => `<span title="${limpio(x.uso)}"><b>${limpio(x.nombre)}</b> · ${limpio(x.estructura)}</span>`).join("")}</div>
  </section>` : "";
  contenedor.innerHTML = `
    <div class="cifras">
      <div class="cifra"><b>${numero(e.total)}</b><span>ofertas indexadas</span></div>
      <div class="cifra"><b>${numero(i.dimensiones)}</b><span>dimensiones por embedding</span></div>
      <div class="cifra"><b>${numero(lex.terminos ?? e.vocabulario)}</b><span>términos del índice invertido</span></div>
      <div class="cifra"><b>${numero(e.empresas)}</b><span>empresas distintas</span></div>
    </div>
    ${proceso}
    <div class="rejilla-2" style="margin-top:1.1rem">
      <section class="panel"><h2>Ofertas por fuente</h2><p>Portales y API de donde se acopió cada vacante.</p>${barras(e.por_fuente, 10, "fuente")}</section>
      <section class="panel"><h2>Modalidad de trabajo</h2><p>Detectada del campo original o del texto de la oferta.</p>${barras(e.por_modalidad, 5, "modalidad")}</section>
      <section class="panel ancho"><h2>Tecnologías más solicitadas</h2><p>Ofertas que mencionan cada tecnología del diccionario controlado. ${numero(e.sin_tecnologias)} no mencionan ninguna.</p><div class="columnas-2">${barras(e.tecnologias, 24, "tecnologias")}</div></section>
      <section class="panel"><h2>Nivel de experiencia</h2><p>Según título, campo original o años solicitados.</p>${barras(e.por_nivel, 6, "nivel")}</section>
      <section class="panel"><h2>Área del puesto</h2><p>Clasificación por palabras del título y tecnologías.</p>${barras(e.por_area, 12, "area")}</section>
      <section class="panel"><h2>Idioma detectado</h2><p>Conteo de palabras vacías por idioma.</p>${barras(e.por_idioma, 5, "idioma")}</section>
      <section class="panel"><h2>Índice léxico</h2><p>Índice invertido guardado en <code>lexico.json.gz</code>.</p>
        <dl class="ficha"><dt>Modelo</dt><dd>${limpio(lex.modelo || "BM25")}</dd><dt>Documentos</dt><dd>${numero(lex.documentos ?? e.total)}</dd><dt>Términos</dt><dd>${numero(lex.terminos ?? e.vocabulario)}</dd><dt>Postings</dt><dd>${numero(lex.postings)}</dd><dt>Longitud media</dt><dd>${lex.longitud_promedio ?? e.longitud_media} términos</dd></dl></section>
      <section class="panel"><h2>Índice semántico</h2><p>Vectores guardados en <code>vectores.npy</code>.</p>
        <dl class="ficha"><dt>Modelo</dt><dd>${limpio(i.modelo)}</dd><dt>Dimensiones</dt><dd>${numero(i.dimensiones)}</dd><dt>Búsqueda</dt><dd>${limpio(i.motor_vectorial)}</dd><dt>Peso híbrido</dt><dd>${Math.round(c.peso_semantico * 100)}% significado · ${Math.round((1 - c.peso_semantico) * 100)}% palabras</dd><dt>Idiomas</dt><dd>${Object.entries(e.por_idioma || {}).map(([k, val]) => `${limpio(nombre("idioma", k))} ${numero(val)}`).join(" · ")}</dd></dl></section>
    </div>
    ${vector}
    <div style="margin-top:1.1rem">${panelEvaluacion(c.evaluacion)}</div>
    <div class="encabezado-acciones" style="margin-top:1rem"><button type="button" class="boton-primario" data-vista="texto">Abrir laboratorio de texto ${ICONOS.flecha}</button></div>`;
}

/* ------------------------------------------------------------------ */
/* Comparar                                                           */
/* ------------------------------------------------------------------ */
function columna(clase, titulo, subtitulo, lista, campo) {
  const items = (lista || []).map((r, n) => `<li>
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
  $("#duelo").innerHTML = '<div class="skeleton" style="height:280px"></div><div class="skeleton" style="height:280px"></div>';
  try {
    const d = await pedir("/api/comparar?q=" + encodeURIComponent(consulta));
    $("#estado-comparar").innerHTML = `Los dos rankings coinciden en <strong>${d.coincidencias}</strong> de sus primeras ${Math.max(d.lexico.length, d.semantico.length)} ofertas para “${limpio(d.consulta)}”.`;
    $("#duelo").innerHTML =
      columna("lex", "Palabras exactas", "BM25 sobre el índice invertido", d.lexico, "lexico") +
      columna("sem", "Significado", "Similitud coseno entre embeddings", d.semantico, "semantico");
  } catch (error) {
    $("#estado-comparar").textContent = error.message;
    $("#duelo").innerHTML = "";
    toast(error.message, "error");
  }
}

/* ------------------------------------------------------------------ */
/* Detalle y voz por oferta                                           */
/* ------------------------------------------------------------------ */
let detalleActual = null;

async function abrirDetalle(id) {
  try {
    const o = await pedir("/api/oferta/" + encodeURIComponent(id));
    detalleActual = o;
    const enlace = /^https?:\/\//.test(o.url) && !o.url.includes(".invalid")
      ? `<a class="enlace-original" href="${limpio(o.url)}" target="_blank" rel="noopener noreferrer">Ver la oferta original en ${limpio(o.fuente)} ${ICONOS.flecha}</a>`
      : "";
    $("#detalle-contenido").innerHTML = `
      <div class="detalle-cabeza">
        <div><h2 id="detalle-titulo">${limpio(o.titulo)}</h2><p>${limpio([o.empresa, o.ubicacion, fecha(o.fecha_publicacion)].filter(Boolean).join(" · "))}</p></div>
        <button type="button" class="boton-icono" id="cerrar-detalle" aria-label="Cerrar detalle">✕</button>
      </div>
      <div class="detalle-cuerpo">
        ${etiquetasOferta(o)}
        <div class="detalle-acciones" style="margin-top:1rem">
          <button type="button" class="boton-fantasma" data-leer-detalle>${ICONOS.altavoz} Escuchar oferta</button>
          <button type="button" class="boton-fantasma" data-copiar-detalle>Copiar texto</button>
        </div>
        <div class="descripcion">${limpio(o.descripcion)}</div>
        ${enlace}
      </div>`;
    $("#detalle").showModal();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function hablarOferta(id) {
  try {
    const o = await pedir("/api/oferta/" + encodeURIComponent(id));
    const texto = `${o.titulo}. ${o.empresa || ""}. ${nombre("modalidad", o.modalidad)}. ${o.descripcion || ""}`;
    Voz.hablar(texto);
  } catch (error) {
    toast(error.message, "error");
  }
}

/* ------------------------------------------------------------------ */
/* Navegación y eventos                                               */
/* ------------------------------------------------------------------ */
function aplicarTema(tema) {
  estado.tema = tema;
  document.documentElement.dataset.tema = tema;
  document.body.dataset.tema = tema;
  localStorage.setItem("sysjobs-tema", tema);
}

function mostrarVista(vista) {
  if (!TITULOS[vista]) vista = "buscar";
  estado.vista = vista;
  $$(".vista").forEach((s) => (s.hidden = s.id !== "vista-" + vista));
  $$(".pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.vista === vista));
  $("#barra-titulo").textContent = TITULOS[vista];
  cerrarFiltros();
  if (vista === "comparar" && !$("#duelo").innerHTML.trim()) {
    const consulta = estado.q || "programador de servicios web y APIs";
    $("#consulta-comparar").value = consulta;
    comparar(consulta);
  }
  if (vista === "texto") pintarTexto();
  if (vista === "datos") cargarDatos();
  if (vista === "corpus") pintarCorpus();
  history.replaceState(null, "", vista === "buscar" ? location.pathname : "#" + vista);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function leerResumen() {
  if (!estado.ultimo) return;
  const titulos = (estado.ultimo.resultados || []).slice(0, 4).map((r) => `${r.titulo}, ${r.empresa || "empresa no indicada"}`);
  Voz.hablar(`${$("#estado").textContent}. ${titulos.join(". ")}`);
}

function leerTexto() {
  const r = estado.texto && estado.texto.resumen;
  if (!r) return;
  Voz.hablar(`El corpus tiene ${r.documentos} ofertas y ${r.tokens} tokens útiles. Se conservaron ${r.tipos} lemas y se eliminó el ${r.reduccion_tokens} por ciento del ruido. Hay ${r.ngramas_distintos?.["2"] || 0} bigramas distintos.`);
}

function leerCorpus() {
  const c = estado.corpus;
  if (!c || !c.estadisticas) return;
  const e = c.estadisticas;
  const tecnologia = Object.entries(e.tecnologias || {})[0];
  Voz.hablar(`El corpus tiene ${e.total} ofertas de ${e.empresas} empresas. La tecnología más solicitada es ${tecnologia ? tecnologia[0] : "no disponible"}. El índice semántico usa ${c.indices?.dimensiones || "varias"} dimensiones.`);
}

function alternarFiltros() {
  const panel = $("#panel-filtros");
  const abierto = panel.classList.toggle("abierto");
  $("#mostrar-filtros").textContent = abierto ? "Ocultar filtros" : "Filtros";
  $("#velo-filtros").classList.toggle("visible", abierto);
  document.body.classList.toggle("filtros-abiertos", abierto);
  if (abierto) $("#cerrar-filtros").focus();
}

function cerrarFiltros() {
  $("#panel-filtros").classList.remove("abierto");
  $("#velo-filtros").classList.remove("visible");
  document.body.classList.remove("filtros-abiertos");
  const botonFiltros = $("#mostrar-filtros");
  if (botonFiltros) botonFiltros.textContent = "Filtros";
}

document.addEventListener("click", (evento) => {
  const boton = evento.target.closest("button, a");
  if (!boton) {
    if (evento.target === $("#detalle")) $("#detalle").close();
    return;
  }
  if (boton.dataset.vista) return mostrarVista(boton.dataset.vista);
  if (boton.dataset.modo) {
    estado.modo = boton.dataset.modo;
    $$(".modos button").forEach((b) => b.setAttribute("aria-checked", String(b === boton)));
    return buscar();
  }
  if (boton.dataset.ejemplo) {
    $("#consulta").value = estado.q = boton.dataset.ejemplo;
    return buscar();
  }
  if (boton.dataset.campo) {
    const { campo, valor } = boton.dataset;
    if (campo === "tecnologias") {
      const lista = estado.filtros.tecnologias;
      estado.filtros.tecnologias = lista.includes(valor) ? lista.filter((t) => t !== valor) : [...lista, valor];
    } else {
      estado.filtros[campo] = estado.filtros[campo] === valor ? "" : valor;
    }
    pintarFiltros();
    return buscar();
  }
  if (boton.dataset.quitar) {
    const campo = boton.dataset.quitar;
    if (campo === "tecnologias") {
      estado.filtros.tecnologias = estado.filtros.tecnologias.filter((t) => t !== boton.dataset.valor);
    } else {
      estado.filtros[campo] = "";
    }
    pintarFiltros();
    return buscar();
  }
  if (boton.id === "limpiar") {
    estado.filtros = { modalidad: "", nivel: "", area: "", idioma: "", fuente: "", tecnologias: [] };
    pintarFiltros();
    return buscar();
  }
  if (boton.id === "cerrar-detalle") return $("#detalle").close();
  if (boton.id === "mostrar-filtros") return alternarFiltros();
  if (boton.id === "cerrar-filtros" || boton.id === "velo-filtros") return cerrarFiltros();
  if (boton.id === "micro") return Voz.iniciar();
  if (boton.id === "escuchar-resumen") return leerResumen();
  if (boton.id === "escuchar-texto") return leerTexto();
  if (boton.id === "escuchar-corpus") return leerCorpus();
  if (boton.id === "boton-voz") {
    mostrarVista("buscar");
    $("#consulta").focus();
    toast("Pulsa el micrófono para dictar y usa los altavoces para escuchar ofertas y resúmenes.");
    return;
  }
  if (boton.classList.contains("alternar-tema")) return aplicarTema(estado.tema === "claro" ? "oscuro" : "claro");
  if (boton.id === "regenerar" || boton.id === "regenerar-2") return regenerar();
  if (boton.dataset.muestra !== undefined) {
    estado.muestra = Number(boton.dataset.muestra);
    return pintarTexto();
  }
  if (boton.dataset.fuenteFrec) {
    estado.fuenteFrec = boton.dataset.fuenteFrec;
    return renderFrecuencias();
  }
  if (boton.dataset.ngrama) {
    estado.ngrama = boton.dataset.ngrama;
    return renderNgramas();
  }
  if (boton.dataset.copiar) {
    const codigo = document.getElementById(boton.dataset.copiar);
    if (!codigo) return;
    navigator.clipboard?.writeText(codigo.textContent).then(() => toast("Código copiado.", "exito")).catch(() => toast("No se pudo copiar.", "error"));
    return;
  }
  if (boton.dataset.copiarDetalle) {
    if (detalleActual) navigator.clipboard?.writeText(`${detalleActual.titulo}\n${detalleActual.empresa}\n${detalleActual.descripcion}`)
      .then(() => toast("Oferta copiada.", "exito")).catch(() => toast("No se pudo copiar.", "error"));
    return;
  }
  if (boton.dataset.leerDetalle) {
    if (detalleActual) Voz.hablar(`${detalleActual.titulo}. ${detalleActual.empresa || ""}. ${detalleActual.descripcion || ""}`, boton);
    return;
  }
  if (boton.dataset.leerId) return hablarOferta(boton.dataset.leerId);
  if (boton.dataset.id) return abrirDetalle(boton.dataset.id);
});

document.addEventListener("keydown", (evento) => {
  const escribiendo = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "");
  if (evento.key === "Escape") {
    if ($("#detalle")?.open) $("#detalle").close();
    if (Voz.activo) Voz.detener();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    cerrarFiltros();
  }
  if (evento.key === "/" && !escribiendo) {
    evento.preventDefault();
    mostrarVista("buscar");
    $("#consulta").focus();
  }
  if (!escribiendo && /^[1-5]$/.test(evento.key)) {
    mostrarVista(["buscar", "comparar", "texto", "datos", "corpus"][Number(evento.key) - 1]);
  }
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

async function regenerar() {
  const botones = ["#regenerar", "#regenerar-2"].map((s) => $(s)).filter(Boolean);
  botones.forEach((b) => { b.disabled = true; b.dataset.texto = b.textContent; b.textContent = "Regenerando…"; });
  try {
    const res = await pedir("/api/exportar", { method: "POST" });
    estado.datos = res.datos;
    pintarDatos();
    toast(res.mensaje, "exito");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    botones.forEach((b) => { b.disabled = false; b.textContent = b.dataset.texto || "Regenerar"; });
  }
}

/* ------------------------------------------------------------------ */
/* Arranque                                                           */
/* ------------------------------------------------------------------ */
function pintarHero() {
  const c = estado.corpus;
  const e = c && c.estadisticas;
  const i = c && c.indices;
  const r = estado.texto && estado.texto.resumen;
  const cifras = {
    ofertas: e ? e.total : null,
    lemas: r ? r.tipos : (e ? e.vocabulario : null),
    dimensiones: i ? i.dimensiones : null,
  };
  Object.entries(cifras).forEach(([clave, valor]) => {
    const nodo = document.querySelector(`[data-cifra="${clave}"]`);
    if (nodo) nodo.textContent = valor ? numero(valor) : "—";
  });
}

(async function iniciar() {
  aplicarTema(estado.tema);
  const [corpus, datos] = await Promise.allSettled([
    pedir("/api/corpus"),
    pedir("/api/datos"),
  ]);
  if (corpus.status === "fulfilled") {
    estado.corpus = corpus.value;
    estado.texto = corpus.value.texto || null;
    $("#riel-estado").textContent = "corpus listo";
  } else {
    $("#riel-estado").textContent = "sin conexión";
    toast(corpus.reason.message, "error");
  }
  if (datos.status === "fulfilled") estado.datos = datos.value;
  pintarHero();
  pintarFiltros();
  pintarCorpus();
  pintarTexto();
  if (estado.datos) pintarDatos();
  else cargarDatos();
  const vista = (location.hash || "").replace("#", "");
  if (TITULOS[vista]) mostrarVista(vista);
  else buscar();
})();
