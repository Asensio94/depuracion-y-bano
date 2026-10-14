"""The published page: one self-contained HTML file (data embedded), Spanish text, shared sibling style.

Written for someone who has never heard of the directive: plain sentences first, the legal terms
only in the method section.
"""
from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config as c
from .logo import LOGO_SVG, favicon_link
from .places import nice_name

ACCENT, ACCENT_DARK = "#2b59a6", "#8eb1f0"
COMMON_CSS = (Path(__file__).parent / "common.css").read_text(encoding="utf-8")
SLUG = "depuracion-y-bano"
SIBLINGS = [
    ("observatorio-alegaciones", "Observatorio de alegaciones"), ("vigia-incendios", "Vigía de incendios"),
    ("centinela-natura", "Centinela Natura"), ("vigilancia-humedales", "Vigilancia de humedales"),
    ("sub-nocte", "Sub Nocte"), ("riesgo-tendidos-aves", "Riesgo de tendidos para aves"),
    ("grafo-promotores", "Grafo de promotores"), ("cartera-cotizadas", "Cartera de las cotizadas"),
    ("cuaderno-campo", "Cuaderno de campo"), ("caudal-ecologico", "Caudal ecológico"),
    ("estado-iba", "Estado de las IBA"), (SLUG, "Depuración y baño"),
]
MONTHS = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
TOP_ROWS = 25

# The three things the directive asks, in order; each agglomeration counts once, by its most basic failure.
GROUP = {"collection": "collection", "untreated": "collection", "no_plant": "collection",
         "secondary": "secondary", "secondary_performance": "secondary",
         "stringent": "stringent", "stringent_performance": "stringent"}
STEP = {"collection": "Recoger", "secondary": "Depurar", "stringent": "Depurar más"}
CHECK = {"bod": "DBO₅", "cod": "DQO", "n": "nitrógeno", "p": "fósforo"}
# Faecal bacteria above which a bathing water is "insuficiente" (90th percentile, CFU per 100 ml, Directive 2006/7).
POOR_LIMITS = {"inland": (900, 330), "sea": (500, 185)}


def _and(words: list[str]) -> str:
    return " y ".join([", ".join(words[:-1]), words[-1]]) if len(words) > 1 else "".join(words)


def plain_gap(g: str, a: dict) -> str:
    """What a gap means for this agglomeration, in one sentence with its own figures."""
    pct = lambda v: fmt(float(v or 0), 1)
    failed = a.get("failed", [])
    if g == "collection":
        return (f"El {pct(100 - float(a['collected'] or 0) - float(a['individual'] or 0))} % de sus aguas fecales "
                f"no llega al alcantarillado ni a una fosa")
    if g == "untreated":
        return f"Vierte el {pct(a['untreated'])} % de sus aguas fecales sin ningún tratamiento"
    if g == "no_plant":
        return "Recoge sus aguas fecales pero no las lleva a ninguna depuradora"
    if g == "secondary":
        return "Su depuradora no tiene tratamiento biológico: el agua sale con buena parte de la materia orgánica"
    if g == "secondary_performance":
        what = [CHECK[k] for k in failed if k in ("bod", "cod")]
        return ("Su depuradora vierte agua con más materia orgánica de la permitida"
                + (f" ({_and(what)} por encima del límite)" if what else ""))
    if g == "stringent":
        return "Vierte en una zona sensible sin quitar nitrógeno ni fósforo, que alimentan plagas de algas"
    what = [CHECK[k] for k in failed if k in ("n", "p")]
    return f"Vierte en una zona sensible más {_and(what) or 'nitrógeno o fósforo'} de lo permitido"


def gap_sentences(a: dict) -> list[tuple[str, str]]:
    """(group, sentence) per gap; what is not collected is usually what goes out untreated, said once."""
    gaps = list(a["gaps"])
    if {"collection", "untreated"} <= set(gaps) and float(a["untreated"] or 0) == round(
            100 - float(a["collected"] or 0) - float(a["individual"] or 0), 1):
        gaps.remove("untreated")
        return [("collection", f"El {fmt(float(a['untreated']), 1)} % de sus aguas fecales no llega al alcantarillado "
                               f"y se vierte sin tratar")] + [(GROUP[g], plain_gap(g, a)) for g in gaps if g != "collection"]
    return [(GROUP[g], plain_gap(g, a)) for g in gaps]


def faecal_text(z: dict) -> str:
    """Why a bathing water is poor: always faecal bacteria, with the limits for its kind of water."""
    if z["quality"] != "insuficiente":
        return ""
    ec, ie = POOR_LIMITS["inland" if z["type"] in ("riverBathingWater", "lakeBathingWater") else "sea"]
    return (f"Contaminación fecal: en sus análisis hay con demasiada frecuencia más de {fmt(ec)} <i>E. coli</i> "
            f"o más de {fmt(ie)} enterococos por 100 ml")
QUALITY = {"excelente": "Excelente", "buena": "Buena", "suficiente": "Suficiente",
           "insuficiente": "Insuficiente", "sin_clasificar": "Sin clasificar"}
ZONE_TYPE = {"coastalBathingWater": "mar", "transitionalBathingWater": "estuario o ría",
             "riverBathingWater": "río", "lakeBathingWater": "lago o embalse"}
METHOD = {"river": "río abajo", "mouth": "por la desembocadura", "water_body": "en la misma costa o embalse"}
EEA_UWWTD = "https://www.eea.europa.eu/en/datahub/datahubitem-view/6244937d-1c2c-47f5-bdf1-33ca01ff1715"
EEA_BATHING = "https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/{uuid}"
HYDROSHEDS = "https://www.hydrosheds.org/products/hydrorivers"
DIRECTIVE = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:31991L0271"
BATHING_DIRECTIVE = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32006L0007"
RECAST_URL = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32024L3019"
JUDGMENT = "https://curia.europa.eu/juris/liste.jsf?num=C-205/17"
NOMENCLATOR_URL = "https://www.ine.es/nomen2/index.do"
# INE Nomenclátor 2025: people in scattered housing (units ending in 99) and in population nuclei under 2,000.
NOMENCLATOR = {"year": 2025, "scattered": 1_700_591, "small": 6_359_824}

CSS = f""":root{{--accent:{ACCENT};--accent-dark:{ACCENT_DARK};
  --g-collection:#b42318;--g-secondary:#d9600f;--g-stringent:#b8860b;--g-ok:#9a948d;
  --q-insuficiente:#b42318;--q-suficiente:#d99a00;--q-buena:#5b9bd5;--q-excelente:#2b59a6;--q-sin_clasificar:#9a948d}}
main{{max-width:1100px;margin:0 auto;padding:0 16px}}
.figures div{{max-width:270px}}
.prose{{max-width:760px}}
.prose p{{margin:0 0 12px}}
h2.block{{margin:44px 0 8px;font-family:var(--font-title);font-size:1.7rem}}
p.block{{color:var(--muted);margin:0 0 10px;max-width:760px}}
.steps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:14px 0}}
.steps .card{{border-top:5px solid var(--c);display:grid;gap:6px;align-content:start}}
.steps h3{{margin:0;font-family:var(--font-title);font-size:1.35rem}}
.steps h3 small{{color:var(--muted);font-size:.9rem;margin-right:6px}}
.steps p{{margin:0;font-size:.95rem}}
.steps .fail{{font-family:var(--font-data);font-size:1.6rem;color:var(--c);line-height:1.1;margin-top:4px}}
.steps .fail+p{{color:var(--muted);font-size:.88rem}}
.words{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin:14px 0}}
.words dt{{font-weight:700}}.words dd{{margin:2px 0 0}}
.search{{margin:14px 0 4px;max-width:560px}}
.search input{{width:100%;font:inherit;font-size:1.05rem;padding:10px 14px;border:1px solid var(--line);
  border-radius:8px;background:var(--paper);color:var(--ink)}}
#results{{list-style:none;margin:6px 0 0;padding:0;max-width:760px}}
#results li{{margin:0}}
#results button{{all:unset;box-sizing:border-box;display:block;width:100%;cursor:pointer;padding:8px 10px;
  border-bottom:1px solid var(--line)}}
#results button:hover,#results button:focus-visible{{background:color-mix(in srgb,var(--accent) 10%,transparent)}}
#results .sub{{display:block;color:var(--muted);font-size:.86rem}}
#map,#map-bath{{height:min(620px,75vh);border:1px solid var(--line);border-radius:8px;margin:10px 0 6px;background:var(--paper)}}
.leaflet-container{{font:inherit;font-size:.9rem}}
.leaflet-popup-content{{margin:12px 14px;line-height:1.4}}
.leaflet-popup-content h4{{margin:0 0 2px;font-size:1rem}}
.leaflet-popup-content .sub{{color:#6b625c;font-size:.82rem}}
.leaflet-popup-content ul{{margin:4px 0;padding-left:18px}}
.tools{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0 6px}}
.tools button{{font:inherit;font-size:.9rem;padding:6px 12px;border:1px solid var(--line);border-radius:999px;
  background:var(--paper);color:var(--ink);cursor:pointer}}
.tools button[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:var(--paper)}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:.88rem;margin:4px 0}}
.legend.lead{{display:block;margin-top:10px}}
.legend b{{color:var(--ink);font-weight:600}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle;flex:none}}
.sq{{display:inline-block;width:9px;height:9px;margin-right:6px;vertical-align:middle;transform:rotate(45deg)}}
.wrap{{overflow-x:auto}}
table.list{{width:100%;border-collapse:collapse;font-size:.92rem}}
.list th{{text-align:left;font-weight:600;color:var(--muted);font-size:.8rem;text-transform:uppercase;
  letter-spacing:.03em;padding:8px 10px;border-bottom:2px solid var(--line)}}
.list td{{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
.list td.num,.list th.num{{text-align:right;font-family:var(--font-data);white-space:nowrap}}
.list .sub{{display:block;color:var(--muted);font-size:.82rem}}
.list tr:target{{background:color-mix(in srgb,var(--accent) 12%,transparent)}}
.list a.go{{color:inherit;text-decoration:none;border-bottom:1px dotted var(--muted)}}
.why{{display:flex;align-items:baseline;gap:0}}
.hist{{white-space:nowrap;display:block;margin-bottom:2px}}
.hist i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:2px;vertical-align:middle}}
tr[hidden],.collapsed tr[data-extra]{{display:none}}
.more{{font:inherit;margin:10px 0;padding:6px 14px;border:1px solid var(--accent);border-radius:999px;
  background:none;color:var(--accent);cursor:pointer}}
@media (max-width:640px){{
  .list thead{{display:none}}
  .list tr{{display:block;padding:10px 0;border-bottom:1px solid var(--line)}}
  .list td{{display:block;border:0;padding:3px 0}}
  .list td.num{{display:inline-block;text-align:left;margin-right:16px}}
  .list td[data-label]::before{{content:attr(data-label) ": ";color:var(--muted);font:.8rem var(--font-text)}}
  .list td.num .sub{{display:inline;margin-left:4px}}
}}
"""

SCRIPT = r"""
const DATA = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = n => n.toLocaleString('es-ES');
const esc = s => String(s).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[ch]);
const plain = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const map = L.map('map', {preferCanvas: true}).setView([40.2, -3.6], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18, attribution: '© OpenStreetMap'}).addTo(map);
const layers = {flagged: L.layerGroup().addTo(map), ok: L.layerGroup(), zonesBad: L.layerGroup().addTo(map), zonesGood: L.layerGroup()};
const lines = L.layerGroup().addTo(map), svg = L.svg({padding: 1}), LINK = '#173a75';
const aggBy = {}, zoneBy = {};
for (const z of DATA.zones) zoneBy[z[0]] = z;
for (const a of DATA.aggs) aggBy[a[0]] = a;

// Agglomerations: circles sized by load, coloured by the step they fail.
for (const a of DATA.aggs) {
  const [code, name, muni, lon, lat, pe, group, why, zs] = a;
  const m = L.circleMarker([lat, lon], {radius: Math.max(3, Math.min(22, Math.sqrt(pe) / 40)),
    color: '#fff', weight: 1, fillColor: css(group ? '--g-' + group : '--g-ok'), fillOpacity: group ? .85 : .55});
  m.bindPopup(() => `<h4>${esc(name)}</h4><div class="sub">${muni && muni !== name ? esc(muni) + ' · ' : ''}${fmt(pe)} h-e</div>
    ${why.length ? '<b>No cumple:</b><ul>' + why.map(w => '<li>' + esc(w) + '</li>').join('') + '</ul>'
                 : '<div>Cumple lo que pide la ley, según el informe.</div>'}
    <div class="sub">${zs.length ? `Sus vertidos llegan a ${zs.length} zona${zs.length > 1 ? 's' : ''} de baño (líneas azules).`
                                  : 'No hay zonas de baño cerca de sus vertidos.'}</div>
    ${group ? `<div><a href="#${code}">Ver en la lista</a></div>` : ''}`);
  a.targets = () => zs.map(z => zoneBy[z]).filter(Boolean).map(z => [z[4], z[3]]);
  a.layer = group ? 'flagged' : 'ok';
  m.on('click', () => draw([lat, lon], a.targets()));
  layers[a.layer].addLayer(m); a.marker = m;
}

function zonePopup(z) {
  const [id, name, muni, lon, lat, q, type, hist, ups] = z;
  return `<h4>${esc(name)}</h4><div class="sub">Zona de baño · ${type} · ${esc(muni)}</div>
    <div><b>${DATA.quality[q]}</b> en ${DATA.season}${hist ? '. ' + hist : ''}</div>
    ${z[10] ? `<div>${z[10]}.</div>` : ''}
    ${ups.length ? '<b>Vierten cerca:</b><ul>' + ups.map(([c, how, km]) => {
      const a = aggBy[c]; return a ? `<li>${esc(a[1])} <span class="sub">${fmt(a[5])} h-e · ${how}, a ${km.toLocaleString('es-ES')} km${a[6] ? ' · <b>no depura como debe</b>' : ''}</span></li>` : '';
    }).join('') + '</ul>' : '<div class="sub">Ningún pueblo o ciudad de más de 2.000 h-e vierte cerca.</div>'}
    ${z[11] ? `<div class="sub"><a href="${z[11]}">Perfil oficial de la zona (PDF, Sanidad)</a></div>` : ''}`;
}

// Bathing waters: diamonds, the worst ones bigger and on top.
const SIZE = {insuficiente: 15, suficiente: 12, buena: 8, excelente: 7, sin_clasificar: 7};
const RANK = {insuficiente: 400, suficiente: 300, buena: 100, excelente: 0, sin_clasificar: 0};
for (const z of DATA.zones) {
  const [id, name, muni, lon, lat, q, type, hist, ups] = z;
  const m = L.marker([lat, lon], {zIndexOffset: RANK[q], keyboard: false, icon: L.divIcon({className: '',
    html: `<span class="sq" style="background:${css('--q-' + q)};border:1px solid #fff;width:${SIZE[q]}px;height:${SIZE[q]}px;opacity:${RANK[q] ? 1 : .75}"></span>`,
    iconSize: [SIZE[q], SIZE[q]]})});
  m.bindPopup(() => zonePopup(z));
  z.targets = () => ups.map(([c]) => aggBy[c]).filter(Boolean).map(a => [a[4], a[3]]);
  z.layer = RANK[q] >= 300 ? 'zonesBad' : 'zonesGood';
  m.on('click', () => draw([lat, lon], z.targets()));
  layers[z.layer].addLayer(m); z.marker = m;
}
function draw(from, tos, into = lines, renderer = svg) {
  into.clearLayers();
  for (const to of tos) {
    L.polyline([from, to], {renderer, color: LINK, weight: 2.5, dashArray: '5 4', interactive: false}).addTo(into);
    L.circleMarker(to, {renderer, radius: 6, color: LINK, weight: 2.5, fill: false, interactive: false}).addTo(into);
  }
}
map.on('popupclose', () => lines.clearLayers());

// Second map: only the bathing waters rated poor or sufficient, the poor ones bigger the more seasons they failed.
const bath = L.map('map-bath', {preferCanvas: true}).setView([40.2, -3.6], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18, attribution: '© OpenStreetMap'}).addTo(bath);
const bathLines = L.layerGroup().addTo(bath), bathSvg = L.svg({padding: 1}), bathBy = {};
for (const z of [...DATA.zones].sort((x, y) => x[9] - y[9])) {
  const [id, name, muni, lon, lat, q, , , , poorSeasons] = z;
  if (q !== 'insuficiente' && q !== 'suficiente') continue;
  const m = L.circleMarker([lat, lon], {radius: q === 'insuficiente' ? 5 + 2 * poorSeasons : 5,
    color: '#fff', weight: 1, fillColor: css('--q-' + q), fillOpacity: .9}).addTo(bath);
  m.bindPopup(() => zonePopup(z));
  m.on('click', () => draw([lat, lon], z.targets(), bathLines, bathSvg));
  bathBy[id] = {marker: m, at: [lat, lon], targets: z.targets};
}
bath.on('popupclose', () => bathLines.clearLayers());
function focusBath(b) {
  if (!b) return;
  document.getElementById('map-bath').scrollIntoView({behavior: 'smooth', block: 'center'});
  setTimeout(() => { bath.fitBounds(L.latLngBounds([b.at, ...b.targets()]).pad(0.3), {maxZoom: 12}); b.marker.fire('click'); }, 300);
}

function show(key, on) {
  on ? layers[key].addTo(map) : map.removeLayer(layers[key]);
  const b = document.querySelector(`[data-layer="${key}"]`);
  if (b) b.setAttribute('aria-pressed', on);
}
function focus(item) {
  if (!item) return;
  if (!map.hasLayer(layers[item.layer])) show(item.layer, true);
  document.getElementById('map').scrollIntoView({behavior: 'smooth', block: 'center'});
  setTimeout(() => {
    map.fitBounds(L.latLngBounds([[item[4], item[3]], ...item.targets()]).pad(0.3), {maxZoom: 12});
    item.marker.fire('click');
  }, 300);
}
document.querySelectorAll('[data-layer]').forEach(b => b.addEventListener('click', () =>
  show(b.dataset.layer, b.getAttribute('aria-pressed') !== 'true')));
document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => {
  const [lat, lon, z] = b.dataset.view.split(',').map(Number); (b.dataset.map === 'bath' ? bath : map).setView([lat, lon], z);
}));
document.addEventListener('click', e => {
  const a = e.target.closest('[data-agg],[data-zone],[data-bath]');
  if (!a) return;
  e.preventDefault();
  if (a.dataset.bath) focusBath(bathBy[a.dataset.bath]);
  else focus(a.dataset.agg ? aggBy[a.dataset.agg] : zoneBy[a.dataset.zone]);
});

// The list of agglomerations: first rows only, filters by step.
const table = document.getElementById('agg-table'), more = document.getElementById('more');
more.addEventListener('click', () => { table.classList.remove('collapsed'); more.hidden = true; });
document.querySelectorAll('[data-group]').forEach(b => b.addEventListener('click', () => {
  b.parentElement.querySelectorAll('button').forEach(o => o.setAttribute('aria-pressed', o === b));
  table.classList.toggle('collapsed', !b.dataset.group && !more.hidden);
  table.querySelectorAll('tbody tr').forEach(tr => tr.hidden = b.dataset.group && tr.dataset.group !== b.dataset.group);
}));

// Search by town or bathing water.
const input = document.getElementById('q'), out = document.getElementById('results');
const index = [...DATA.aggs.map(a => ({key: plain(a[1] + ' ' + a[2]), item: a, kind: 'agg'})),
               ...DATA.zones.map(z => ({key: plain(z[1] + ' ' + z[2]), item: z, kind: 'zone'}))];
input.addEventListener('input', () => {
  const q = plain(input.value.trim());
  if (q.length < 3) { out.innerHTML = ''; return; }
  const hits = index.filter(h => h.key.includes(q));
  hits.sort((x, y) => (x.kind === 'agg' ? 0 : 1) - (y.kind === 'agg' ? 0 : 1) || !!y.item[6] - !!x.item[6]);
  out.innerHTML = hits.length ? hits.slice(0, 12).map(({item, kind}) => {
    const sub = kind === 'agg'
      ? (item[7].length ? '<b>No cumple:</b> ' + item[7].map(esc).join('; ').toLowerCase() : 'Cumple lo que pide la ley, según el informe')
        + ` · ${fmt(item[5])} h-e`
      : `Zona de baño (${item[6]}) · ${DATA.quality[item[5]]} en ${DATA.season}`;
    return `<li><button type="button" data-${kind}="${item[0]}"><b>${esc(item[1])}</b> <span class="sub">${esc(item[2])}${item[2] ? ' · ' : ''}${sub}</span></button></li>`;
  }).join('') + (hits.length > 12 ? `<li class="sub">… y ${hits.length - 12} más: afina la búsqueda.</li>` : '')
  : '<li class="sub">No aparece. Puede que sea un pueblo de menos de 2.000 h-e: el informe no los incluye.</li>';
});
"""


def fmt(x: float | None, digits: int = 0) -> str:
    """Spanish numbers: thousands with a point, decimals with a comma."""
    if x is None:
        return "—"
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def long_date(iso: str) -> str:
    y, m, d = (int(p) for p in iso[:10].split("-"))
    return f"{d} de {MONTHS[m - 1]} de {y}"


def hist_text(history: dict) -> str:
    """How often a bathing water was rated poor, in words."""
    n, k = len(history), sum(q == "insuficiente" for q in history.values())
    if not k:
        return ""
    if n == 1:
        return "Es su primera temporada clasificada"
    return f"Insuficiente en {'las' if k == n else f'{k} de las'} {n} últimas temporadas"


def _why_html(a: dict) -> str:
    return "".join(f'<div class="why"><span class="dot" style="background:var(--g-{g})"></span>{text}</div>'
                   for g, text in gap_sentences(a))


def _hist_html(history: dict) -> str:
    return '<span class="hist">' + "".join(
        f'<i style="background:var(--q-{q})" title="{s}: {QUALITY[q]}"></i>' for s, q in history.items()) + "</span>"


def _agg_row(a: dict, zones: dict, i: int) -> str:
    linked = [zones[z["id"]] for z in a["zones"] if z["id"] in zones]
    bad = sum(z["quality"] == "insuficiente" for z in linked)
    down = (f'{len(linked)} zona{"s" if len(linked) > 1 else ""}'
            + (f'<span class="sub">{bad} insuficiente{"s" if bad > 1 else ""}</span>' if bad else "")) if linked else "—"
    plan = a["plan"]["date"][:4] if a["plan"] and a["plan"]["date"] else "—"
    muni = escape(a["municipality"]) if a["municipality"] and a["municipality"] != a["name"] else ""
    return (f'<tr id="{a["code"]}" data-group="{GROUP[a["main_gap"]]}"{" data-extra" if i >= TOP_ROWS else ""}>'
            f'<td><a class="go" href="#map" data-agg="{a["code"]}"><b>{escape(nice_name(a["name"]))}</b></a>'
            f'<span class="sub">{muni}</span></td>'
            f'<td class="num" data-label="h-e">{fmt(a["pe"])}</td><td>{_why_html(a)}</td>'
            f'<td class="num" data-label="Obras para">{plan}</td><td class="num" data-label="Baño">{down}</td></tr>')


def _zone_row(z: dict, aggs: dict) -> str:
    ups = []
    for u in z["upstream"]:
        a = aggs[u["code"]]
        bad = " · <b>no depura como debe</b>" if a["gaps"] else ""
        ups.append(f'<a href="#{a["code"]}" class="go">{escape(nice_name(a["name"]))}</a> '
                   f'<span class="sub">{fmt(a["pe"])} h-e · {METHOD[u["method"]]}, a {fmt(u["km"], 1)} km{bad}</span>')
    upstream = "".join(f"<div>{u}</div>" for u in ups) or '<span class="sub">Ningún pueblo o ciudad de más de 2.000 h-e</span>'
    profile = (f'<span class="sub"><a href="{escape(z["profile"])}">Perfil oficial (PDF)</a></span>'
               if z.get("profile") else "")
    where = " · ".join(x for x in (escape(z["municipality"] or ""), ZONE_TYPE.get(z["type"], "")) if x)
    return (f'<tr id="{z["id"]}"><td><a class="go" href="#map-bath" data-bath="{z["id"]}"><b>{escape(nice_name(z["name"]))}</b></a>'
            f'<span class="sub">{where}</span>'
            f'{profile}</td>'
            f'<td>{_hist_html(z["history"])}<span class="sub">{hist_text(z["history"])}</span>'
            f'<span class="sub">{faecal_text(z)}</span></td><td>{upstream}</td></tr>')


def _c205(aggs: dict) -> str:
    """The agglomerations of the 2018 fine: those still pending in 2022 should show a gap, the rest none."""
    pending = [n for k, n in c.C205_PENDING_2022.items() if k in aggs and aggs[k]["gaps"]]
    resolved = [n for k, n in c.C205_RESOLVED.items() if k in aggs and aggs[k]["gaps"]]
    return (f'Sentencia <a href="{JUDGMENT}">C-205/17</a>: de las {len(c.C205_PENDING_2022)} aglomeraciones por las que '
            f'España seguía pagando multa en 2022 (Barbate, Matalascañas, Alhaurín el Grande y Güímar), '
            f'{len(pending)} aparecen aquí sin cumplir; de las {len(c.C205_RESOLVED)} que ya se daban por resueltas, '
            f'{len(resolved) or "ninguna"}{" (" + ", ".join(resolved) + ")" if resolved else ""}. '
            f'Isla Cristina y Coín ya no figuran como aglomeraciones propias en el informe.')


def _map_data(data: dict) -> str:
    rel = data["release"]
    aggs = [[a["code"], nice_name(a["name"]), a["municipality"], round(a["lon"], 5), round(a["lat"], 5), a["pe"],
             GROUP[a["main_gap"]] if a["gaps"] else "", [text for _, text in gap_sentences(a)],
             [z["id"] for z in a["zones"]]] for a in data["aggs"] if a["lon"] is not None]
    zones = [[z["id"], nice_name(z["name"]), z["municipality"], round(z["lon"], 5), round(z["lat"], 5), z["quality"],
              ZONE_TYPE.get(z["type"], ""), hist_text(z["history"]),
              [[u["code"], METHOD[u["method"]], u["km"]] for u in z["upstream"]],
              sum(q == "insuficiente" for q in z["history"].values()), faecal_text(z), z.get("profile")]
             for z in data["zones"] if z["lon"] is not None]
    blob = json.dumps({"aggs": aggs, "zones": zones, "quality": QUALITY, "season": rel["season"]},
                      ensure_ascii=False, separators=(",", ":"))
    return blob.replace("</", "<\\/")


def render(data: dict) -> Path:
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    rep, rel, f = data["report"], data["release"], data["figures"]
    aggs = {a["code"]: a for a in data["aggs"]}
    zones = {z["id"]: z for z in data["zones"]}
    flagged = [a for a in data["aggs"] if a["gaps"]]
    poor = sorted((z for z in data["zones"] if z["quality"] == "insuficiente"),
                  key=lambda z: (-sum(q == "insuficiente" for q in z["history"].values()), z["name"]))
    groups = {g: sum(GROUP[a["main_gap"]] == g for a in flagged) for g in STEP}
    gaps = f["gaps"]
    ok_pct = 100 * (f["zones"] - f["poor"] - f["quality"]["sin_clasificar"]) / f["zones"]
    one_in = round(f["total_pe"] / f["flagged_pe"])
    seasons = len(poor[0]["history"]) if poor else 4
    siblings = "\n".join(
        f'    <li{" aria-current=\"page\"" if slug == SLUG else ""}>'
        f'<a href="https://asensio94.github.io/{slug}/">{name}</a></li>' for slug, name in SIBLINGS)

    def step(n: int, g: str, text: str, detail: str) -> str:
        return (f'<div class="card" style="--c:var(--g-{g})"><h3><small>{n}</small>{STEP[g]}</h3><p>{text}</p>'
                f'<div class="fail">{fmt(groups[g])}</div><p>{detail}</p></div>')

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Depuración y baño</title>
<meta name="description" content="Qué pueblos y ciudades de España no depuran sus aguas residuales como exige la ley europea, y qué zonas de baño quedan río abajo.">
{favicon_link(ACCENT, ACCENT_DARK)}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
{COMMON_CSS}
{CSS}
</style>
</head>
<body>
<header class="site-header">
  <h1>{LOGO_SVG}Depuración <span>y baño</span></h1>
  <p class="lede">¿A dónde va lo que tiras por el váter? Qué pueblos y ciudades no depuran sus aguas residuales
  como exige la ley europea, y qué zonas de baño quedan río abajo.</p>
  <div class="figures">
    <div><b>{fmt(f["flagged"])}</b><span>pueblos y ciudades no depuran como exige la ley, de {fmt(f["assessed"])}</span></div>
    <div><b>1 de cada {one_in}</b><span>partes de las aguas residuales de España salen de ellos</span></div>
    <div><b>{fmt(f["poor"])}</b><span>zonas de baño suspenden en {rel["season"]}, de {fmt(f["zones"])}</span></div>
  </div>
</header>
<main>
  <h2 class="block">En pocas palabras</h2>
  <div class="prose">
    <p>Las aguas residuales urbanas deben depurarse antes de verterse a un río, un embalse o el mar. La
    <a href="{DIRECTIVE}">Directiva 91/271/CEE</a> del Consejo fija qué tratamiento debe tener cada aglomeración según su
    tamaño y el medio al que vierte, y los valores que debe cumplir el agua depurada (en el tratamiento secundario, por
    ejemplo, 25 mg/l de DBO<sub>5</sub> y 125 mg/l de DQO). Los plazos vencieron entre 1998 y 2005. España ya ha sido
    condenada por incumplirla: en 2018 el Tribunal de Justicia de la UE le impuso una multa de 12 millones de euros más
    10,95 millones por cada semestre de retraso (<a href="{JUDGMENT}">asunto C-205/17</a>).</p>
    <p>Esta página toma lo que el propio Gobierno declaró a Europa en su último informe, con datos a
    {long_date(rep["situation"])}, y comprueba regla a regla quién no cumple. Después sigue el agua de cada depuradora
    hasta las zonas de baño que hay río abajo. Es un <b>indicio, no un veredicto</b>: la Comisión Europea tiene en
    cuenta plazos, excepciones y datos que el informe no trae.</p>
  </div>

  <h2 class="block">Lo que pide la ley, en tres pasos</h2>
  <p class="block">Debajo de cada paso, cuántos pueblos y ciudades fallan en él. Cada uno cuenta una sola vez, por su
  fallo más básico: en total, {fmt(f["flagged"])}.</p>
  <div class="steps">
    {step(1, "collection", "Llevar las aguas de casas, comercios e industrias por el alcantarillado hasta una depuradora, sin que se pierdan por el camino.",
          "no recogen todas sus aguas o vierten parte sin depurar.")}
    {step(2, "secondary", f"Depurarlas con un tratamiento biológico que quita casi toda la suciedad orgánica. Obligatorio desde {fmt(c.SECONDARY_FRESH_PE)} h-e ({fmt(c.SECONDARY_COASTAL_PE)} si vierten al mar).",
          f"fallan aquí: {fmt(gaps['secondary'])} no tienen ese tratamiento y {fmt(gaps['secondary_performance'])} lo tienen pero no pasan los análisis.")}
    {step(3, "stringent", f"Donde el agua es sensible (embalses, rías, deltas), quitar además el nitrógeno y el fósforo, que alimentan plagas de algas. Desde {fmt(c.STRINGENT_PE)} h-e.",
          f"fallan aquí: {fmt(gaps['stringent'])} no lo hacen y {fmt(gaps['stringent_performance'])} no quitan lo bastante.")}
  </div>
  <p class="block">Dentro de las aglomeraciones del informe, {fmt(f["untreated_pe"])} h-e se vierten sin ningún
  tratamiento y {fmt(f["individual_pe"])} h-e van a fosas sépticas u otros sistemas individuales.</p>
  <p class="block">Fuera del recuento quedan las casas aisladas y los pueblos pequeños: el informe europeo solo incluye
  aglomeraciones de 2.000 h-e o más. Según el <a href="{NOMENCLATOR_URL}">Nomenclátor del INE</a> de
  {NOMENCLATOR["year"]}, {fmt(NOMENCLATOR["scattered"] / 1e6, 1)} millones de personas viven en diseminado y
  {fmt(NOMENCLATOR["small"] / 1e6, 1)} millones en núcleos de menos de 2.000 habitantes. No hay datos abiertos de
  ámbito nacional sobre cómo depuran sus aguas.</p>
  <dl class="words">
    <div class="card"><dt>Pueblo o ciudad («aglomeración»)</dt><dd>Para la ley, la zona que comparte alcantarillado y
    depuradora. Puede ser un municipio, parte de uno o varios juntos. Solo se cuentan las de más de 2.000 h-e.</dd></div>
    <div class="card"><dt>h-e (habitante-equivalente)</dt><dd>La suciedad que echa al agua una persona en un día. Suma
    vecinos, turistas e industria: por eso España declara {fmt(f["total_pe"] / 1e6)} millones de h-e, más que habitantes.</dd></div>
  </dl>

  <h2 class="block" id="buscar">Busca tu pueblo o tu playa</h2>
  <div class="search"><input id="q" type="search" placeholder="Escribe un municipio o una zona de baño…"
    autocomplete="off" aria-label="Buscar municipio o zona de baño" aria-controls="results"></div>
  <ul id="results" aria-live="polite"></ul>

  <h2 class="block" id="mapa">El mapa</h2>
  <div class="legend lead"><b>Círculos: pueblos y ciudades</b> (más grandes cuanto más aguas residuales). El color dice en qué paso fallan:</div>
  <div class="legend">
    {"".join(f'<span><span class="dot" style="background:var(--g-{g})"></span>{n}. {STEP[g]} ({fmt(groups[g])})</span>' for n, g in enumerate(STEP, 1))}
    <span><span class="dot" style="background:var(--g-ok)"></span>Cumplen (ocultos al principio)</span>
  </div>
  <div class="legend lead"><b>Rombos: zonas de baño</b>, según su nota de {rel["season"]}:</div>
  <div class="legend">
    {"".join(f'<span><span class="sq" style="background:var(--q-{q})"></span>{QUALITY[q]} ({fmt(f["quality"][q])})</span>' for q in QUALITY)}
  </div>
  <p class="legend">Pulsa un círculo para ver a qué zonas de baño llegan sus vertidos, o un rombo para ver quién vierte cerca.</p>
  <div class="tools" role="group" aria-label="Qué se ve en el mapa">
    <button type="button" data-layer="ok" aria-pressed="false">Mostrar los que cumplen</button>
    <button type="button" data-layer="zonesGood" aria-pressed="false">Mostrar zonas de baño buenas y excelentes</button>
    <button type="button" data-view="40.2,-3.6,6">Península y Baleares</button>
    <button type="button" data-view="28.4,-15.9,8">Canarias</button>
  </div>
  <div id="map" role="region" aria-label="Mapa de pueblos y ciudades y de zonas de baño"></div>

  <h2 class="block" id="aglomeraciones">Los {fmt(f["flagged"])} que no cumplen</h2>
  <p class="block">De más a menos aguas residuales. «Obras para» es el año en que el Gobierno prevé terminar las obras
  pendientes, cuando lo ha declarado. «Baño» cuenta las zonas de baño a las que llegan sus vertidos.</p>
  <div class="tools" role="group" aria-label="Filtrar por paso">
    <button type="button" data-group="" aria-pressed="true">Todos ({fmt(len(flagged))})</button>
{chr(10).join(f'    <button type="button" data-group="{g}" aria-pressed="false">{n}. {STEP[g]} ({fmt(groups[g])})</button>' for n, g in enumerate(STEP, 1))}
  </div>
  <div class="wrap"><table class="list collapsed" id="agg-table">
    <thead><tr><th>Dónde</th><th class="num">h-e</th><th>Qué falla</th><th class="num">Obras<br>para</th><th class="num">Baño</th></tr></thead>
    <tbody>
{chr(10).join(_agg_row(a, zones, i) for i, a in enumerate(flagged))}
    </tbody>
  </table></div>
  <button type="button" class="more" id="more">Ver los {fmt(max(0, len(flagged) - TOP_ROWS))} restantes</button>

  <h2 class="block" id="zonas">Las {fmt(f["poor"])} zonas de baño que suspenden</h2>
  <div class="prose">
    <p>Cada verano se analiza el agua de cada zona de baño en busca de dos bacterias que viven en los intestinos y
    llegan al agua con las heces: <i>E. coli</i> y enterococos. Su presencia indica que hay materia fecal en el agua,
    y con ella pueden llegar virus y bacterias que causan gastroenteritis, otitis o infecciones de piel. Con los
    análisis de las cuatro últimas temporadas, cada zona recibe una nota según la
    <a href="{BATHING_DIRECTIVE}">Directiva 2006/7/CE</a>: excelente, buena, suficiente o insuficiente.</p>
    <p><b>Insuficiente</b> quiere decir que la contaminación fecal pasa del límite con demasiada frecuencia: en el mar y
    en las rías, más de {fmt(POOR_LIMITS["sea"][0])} <i>E. coli</i> o {fmt(POOR_LIMITS["sea"][1])} enterococos por 100 ml
    (unidades formadoras de colonias); en ríos y embalses, más de {fmt(POOR_LIMITS["inland"][0])} o
    {fmt(POOR_LIMITS["inland"][1])}. Técnicamente, es el percentil 90 de los análisis. Entonces hay que avisar a los
    bañistas, prohibir o desaconsejar el baño y buscar el origen. Si suspende cinco años seguidos, la prohibición pasa a
    ser permanente.</p>
    <p>En {fmt(f["poor_with_upstream"])} de las {fmt(f["poor"])} vierte cerca algún pueblo o ciudad, río arriba o en la
    misma costa, y en {fmt(f["poor_with_flagged_upstream"])} ese pueblo no depura como debe. En las otras
    {fmt(f["poor"] - f["poor_with_upstream"])} no vierte cerca ninguno de más de 2.000 h-e: la causa estará en pueblos
    pequeños, la ganadería o la lluvia que arrastra suciedad.</p>
  </div>
  <div class="legend lead"><b>Mapa de las zonas de baño con peor nota</b> en {rel["season"]}:</div>
  <div class="legend">
    <span><span class="dot" style="background:var(--q-insuficiente)"></span>Insuficiente ({fmt(f["quality"]["insuficiente"])}), más grande cuantas más temporadas lleva suspendiendo</span>
    <span><span class="dot" style="background:var(--q-suficiente)"></span>Suficiente ({fmt(f["quality"]["suficiente"])}), aprobado justo</span>
  </div>
  <p class="legend">Pulsa una zona para ver su historial y quién vierte cerca (líneas azules).</p>
  <div class="tools" role="group" aria-label="Ir a">
    <button type="button" data-map="bath" data-view="40.2,-3.6,6">Península y Baleares</button>
    <button type="button" data-map="bath" data-view="28.4,-15.9,8">Canarias</button>
  </div>
  <div id="map-bath" role="region" aria-label="Mapa de zonas de baño insuficientes y suficientes"></div>
  <p class="block">Primero las que llevan más temporadas suspendiendo. Cuadros: nota de cada una de las {seasons} últimas temporadas.</p>
  <div class="wrap"><table class="list">
    <thead><tr><th>Zona de baño</th><th>Historial</th><th>Quién vierte cerca</th></tr></thead>
    <tbody>
{chr(10).join(_zone_row(z, aggs) for z in poor)}
    </tbody>
  </table></div>

  <section class="method">
    <h2>Cómo se calcula</h2>
    <ol>
      <li><b>Lo que España declara.</b> Cada dos años el Gobierno envía a la Agencia Europea de Medio Ambiente (AEMA)
      el estado de cada aglomeración urbana: cuántas aguas residuales genera (en h-e), qué parte llega al alcantarillado,
      qué parte va a fosas o sistemas individuales, qué parte se vierte sin tratar, a qué depuradoras llega, qué
      tratamiento tienen, si sus análisis cumplen y dónde vierten. El último es el informe de {rep["year"]}, con datos a
      {long_date(rep["situation"])}, entregado el {long_date(rep["version"])}.</li>
      <li><b>Las reglas de la ley.</b> A cada aglomeración se le aplican los artículos 3, 4 y 5 de la
      <a href="{DIRECTIVE}">Directiva 91/271/CEE</a>. <i>Recoger</i>: al menos el {fmt(c.MIN_COLLECTED_PCT)} % de las
      aguas debe ir al alcantarillado o a un sistema individual adecuado, y no más del {fmt(c.MAX_UNTREATED_PCT)} % puede
      verterse sin tratar. <i>Depurar</i> (tratamiento secundario, biológico): obligatorio desde
      {fmt(c.SECONDARY_FRESH_PE)} h-e si vierte a ríos, lagos o estuarios, y desde {fmt(c.SECONDARY_COASTAL_PE)} h-e si
      vierte al mar. <i>Depurar más</i> (tratamiento más riguroso, que elimina nitrógeno o fósforo): obligatorio desde
      {fmt(c.STRINGENT_PE)} h-e si vierte en una zona declarada sensible. Si la depuradora tiene el tratamiento pero sus
      análisis no cumplen, también cuenta como fallo. Los límites del agua depurada son 25 mg/l de DBO<sub>5</sub>
      y 125 mg/l de DQO (materia orgánica) y, en zonas sensibles, 1 a 2 mg/l de fósforo y 10 a 15 mg/l de nitrógeno
      según el tamaño.</li>
      <li><b>Lo que viene.</b> La <a href="{RECAST_URL}">nueva directiva de 2024</a> (2024/3019) exigirá a las
      depuradoras de más de {fmt(c.RECAST_LARGE_PE)} h-e quitar nitrógeno y fósforo en 2039 y un cuarto tratamiento contra
      microcontaminantes (fármacos, cosméticos) en 2045. Hoy no es un fallo y no cuenta en las cifras, pero ya se ve quién
      tendrá que hacer obras: {fmt(f["recast"]["recast_np"])} aglomeraciones para lo primero y
      {fmt(f["recast"]["recast_quaternary"])} para lo segundo.</li>
      <li><b>Las zonas de baño.</b> Cada año la AEMA publica la nota de todas las zonas de baño de Europa. Aquí se usa la
      de {rel["season"]}, publicada el {long_date(rel["published"])}, con el historial de las {seasons} últimas temporadas.</li>
      <li><b>El camino del agua.</b> Cada punto de vertido de una depuradora se une a las zonas de baño de tres maneras.
      <i>Río abajo</i>: el vertido y la zona están a menos de {fmt(c.RIVER_SNAP_KM)} km de un tramo de la red de ríos
      HydroRIVERS, y siguiendo el río desde el vertido se llega a la zona en menos de {fmt(c.RIVER_DOWNSTREAM_KM)} km.
      <i>Por la desembocadura</i>: el río llega al mar en menos de {fmt(c.RIVER_DOWNSTREAM_KM)} km y la zona está a
      menos de {fmt(c.SAME_BODY_KM)} km de la desembocadura. <i>En la misma costa o embalse</i>: el vertido y la zona
      están en la misma masa de agua y a menos de {fmt(c.SAME_BODY_KM)} km.</li>
    </ol>
    <table class="params">
      <tr><th>Parámetro</th><th class="num">Valor</th></tr>
      <tr><td>Aguas recogidas como mínimo (alcantarillado + sistemas individuales)</td><td class="num">{fmt(c.MIN_COLLECTED_PCT)} %</td></tr>
      <tr><td>Aguas vertidas sin tratar como máximo</td><td class="num">{fmt(c.MAX_UNTREATED_PCT)} %</td></tr>
      <tr><td>Depurar: si vierte a ríos, lagos o estuarios</td><td class="num">{fmt(c.SECONDARY_FRESH_PE)} h-e</td></tr>
      <tr><td>Depurar: si vierte al mar</td><td class="num">{fmt(c.SECONDARY_COASTAL_PE)} h-e</td></tr>
      <tr><td>Depurar más: zonas sensibles</td><td class="num">{fmt(c.STRINGENT_PE)} h-e</td></tr>
      <tr><td>Directiva de 2024: grandes depuradoras</td><td class="num">{fmt(c.RECAST_LARGE_PE)} h-e</td></tr>
      <tr><td>Distancia máxima de un punto a la red de ríos</td><td class="num">{fmt(c.RIVER_SNAP_KM)} km</td></tr>
      <tr><td>Recorrido máximo río abajo</td><td class="num">{fmt(c.RIVER_DOWNSTREAM_KM)} km</td></tr>
      <tr><td>Distancia máxima en costa, estuario o embalse</td><td class="num">{fmt(c.SAME_BODY_KM)} km</td></tr>
    </table>
    <h3>Contraste</h3>
    <ul>
      <li>Las {fmt(f["zones"])} zonas de baño y su reparto por notas coinciden con la publicación de la AEMA de {rel["season"]}:
      el {fmt(ok_pct, 1)} % llega al menos a «suficiente».</li>
      <li id="c205">{_c205(aggs)}</li>
    </ul>
    <h3>Límites</h3>
    <ul>
      <li>Es un indicio, no un veredicto. La Comisión evalúa el cumplimiento con plazos, excepciones y aclaraciones
      que no están en el informe, y su evaluación no se publica como datos abiertos.</li>
      <li>El informe solo incluye aglomeraciones de 2.000 h-e o más. Los pueblos pequeños, que también deben depurar
      sus aguas, no aparecen.</li>
      <li>El informe llega con dos años de retraso: una depuradora terminada después de {long_date(rep["situation"])} sigue
      apareciendo con su fallo hasta el informe siguiente.</li>
      <li>Para el cuarto tratamiento se usa como aproximación la ozonización declarada: el informe aún no tiene un campo propio.</li>
      <li>HydroRIVERS es una red de ríos mundial con unos 500 m de detalle. Algunos puntos caen en el tramo vecino y
      los arroyos pequeños no están: un enlace puede faltar o sobrar. En la costa la distancia es en línea recta, sin corrientes.</li>
      <li>No se incluyen los vertidos industriales ni los alivios de tormenta. El Censo Nacional de Vertidos del
      Ministerio, que los tiene, solo se puede descargar resolviendo un captcha, y aquí no se automatiza.</li>
    </ul>
  </section>
</main>
<footer class="site-footer">
  <p class="principle">Datos públicos, reglas a la vista y cada cifra enlazada a su fuente. Indicios, no veredictos.</p>
  <p>Aguas residuales: <a href="{EEA_UWWTD}">Waterbase UWWTD</a>, informe de España de {rep["year"]} a la AEMA. Zonas de baño:
  <a href="{EEA_BATHING.format(uuid=rel["uuid"])}">estado de las aguas de baño {rel["season"]}</a>, AEMA. Red de ríos:
  <a href="{HYDROSHEDS}">HydroRIVERS</a> (Lehner y Grill, 2013, <i>Hydrological Processes</i> 27(15): 2171–2186).
  Municipios: IGN, vía es-atlas. Mapa: © colaboradores de OpenStreetMap. Código en <a href="{c.REPO}">GitHub</a> (MIT);
  datos propios CC BY 4.0. Página generada el {now:%d/%m/%Y a las %H:%M} (hora peninsular).</p>
  <nav aria-label="Proyectos hermanos"><ul class="siblings">
{siblings}
  </ul></nav>
</footer>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>{SCRIPT.replace("__DATA__", _map_data(data))}</script>
</body>
</html>
"""
    out = c.DOCS_DIR / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
