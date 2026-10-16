"""The French page (docs/fr/index.html): same style and layout as the Spanish one, in French.

Built on the official verdict of the State services (portail de l'assainissement collectif), with the
rule of the directive applied to France's report to the EEA as a second reading. Written for someone
who has never heard of the directive: plain sentences first, the legal terms in the method section.
French typography: narrow no-break space as thousands separator and before « % », « ; », « ? », « ! »;
no-break space before « : » and inside guillemets.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config as c
from .i18n import NNBSP, d, n, t
from .logo import LOGO_SVG, favicon_link
from .places import nice_name
from .web import ACCENT, ACCENT_DARK, COMMON_CSS, CSS, POOR_LIMITS, SIBLINGS, SLUG

NBSP = " "
MONTHS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
TOP_ROWS = 25

# What fails in the official verdict, from the most basic; each agglomeration counts once, by the first.
STEP = {"collection": "Collecter", "equipment": "Équiper", "performance": "Bien épurer"}
CHECK = {"bod": "DBO₅", "cod": "DCO", "n": "azote", "p": "phosphore"}
QUALITY = {"excelente": "Excellente", "buena": "Bonne", "suficiente": "Suffisante",
           "insuficiente": "Insuffisante", "sin_clasificar": "Non classée"}
ZONE_TYPE = {"coastalBathingWater": "mer", "transitionalBathingWater": "estuaire ou lagune",
             "riverBathingWater": "rivière", "lakeBathingWater": "lac ou plan d'eau"}
METHOD = {"river": "en aval sur la rivière", "mouth": "par l'embouchure", "water_body": "même côte ou même lac"}
VIEWS = [("Métropole et Corse", "46.6,2.4,6"), ("Guadeloupe", "16.2,-61.5,9"), ("Martinique", "14.65,-61.0,10"),
         ("Guyane", "4.4,-53.0,7"), ("La Réunion", "-21.1,55.5,10"), ("Mayotte", "-12.8,45.15,11")]

ERU_PORTAL = c.ERU_DOWNLOAD_PAGE
EEA_UWWTD = "https://www.eea.europa.eu/en/datahub/datahubitem-view/6244937d-1c2c-47f5-bdf1-33ca01ff1715"
EEA_BATHING = "https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/{uuid}"
HYDROSHEDS = "https://www.hydrosheds.org/products/hydrorivers"
DIRECTIVE = "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:31991L0271"
BATHING_DIRECTIVE = "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32006L0007"
RECAST_URL = "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024L3019"
ARRETE_2015 = "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000031052756"
INFRINGEMENT = ("https://www.data.gouv.fr/datasets/stations-de-traitement-des-eaux-usees-concernees-par-le-"
                "contentieux-eru-2017-2125-en-bourgogne-fran-1")

CSS_FR = """:root{--g-equipment:#d9600f;--g-performance:#b8860b;--g-other:#7a6f66}
.agree{border-collapse:collapse;font-size:.95rem;margin:10px 0}
.agree th,.agree td{border:1px solid var(--line);padding:6px 12px}
.agree td{text-align:right;font-family:var(--font-data)}
.agree th{font-weight:600;text-align:left}
.list td[data-label]::before{content:attr(data-label) " : "}
"""

SCRIPT = r"""
const DATA = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = n => n.toLocaleString('fr-FR');
const esc = s => String(s).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[ch]);
const plain = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const map = L.map('map', {preferCanvas: true}).setView([46.6, 2.4], 6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18, attribution: '© OpenStreetMap'}).addTo(map);
const layers = {flagged: L.layerGroup().addTo(map), ok: L.layerGroup(), zonesBad: L.layerGroup().addTo(map), zonesGood: L.layerGroup()};
const lines = L.layerGroup().addTo(map), svg = L.svg({padding: 1}), LINK = '#173a75';
const aggBy = {}, zoneBy = {};
for (const z of DATA.zones) zoneBy[z[0]] = z;
for (const a of DATA.aggs) aggBy[a[0]] = a;

// Agglomerations: circles sized by load, coloured by the first thing that fails.
for (const a of DATA.aggs) {
  const [code, name, muni, lon, lat, pe, group, why, zs] = a;
  const m = L.circleMarker([lat, lon], {radius: Math.max(3, Math.min(22, Math.sqrt(pe) / 40)),
    color: '#fff', weight: 1, fillColor: css(group ? '--g-' + group : '--g-ok'), fillOpacity: group ? .85 : .55});
  m.bindPopup(() => `<h4>${esc(name)}</h4><div class="sub">${muni && muni !== name ? esc(muni) + ' · ' : ''}${fmt(pe)} EH</div>
    ${why.length ? '<b>Non conforme :</b><ul>' + why.map(w => '<li>' + esc(w) + '</li>').join('') + '</ul>'
                 : '<div>Conforme selon les services de l’État.</div>'}
    <div class="sub">${zs.length ? `Ses rejets arrivent à ${zs.length} baignade${zs.length > 1 ? 's' : ''} (lignes bleues).`
                                  : 'Aucune baignade près de ses rejets.'}</div>
    ${group ? `<div><a href="#${code}">Voir dans la liste</a></div>` : ''}`);
  a.targets = () => zs.map(z => zoneBy[z]).filter(Boolean).map(z => [z[4], z[3]]);
  a.layer = group ? 'flagged' : 'ok';
  m.on('click', () => draw([lat, lon], a.targets()));
  layers[a.layer].addLayer(m); a.marker = m;
}

function zonePopup(z) {
  const [id, name, muni, lon, lat, q, type, hist, ups] = z;
  return `<h4>${esc(name)}</h4><div class="sub">Baignade · ${type} · ${esc(muni)}</div>
    <div><b>${DATA.quality[q]}</b> en ${DATA.season}${hist ? '. ' + hist : ''}</div>
    ${z[10] ? `<div>${z[10]}.</div>` : ''}
    ${z[12] ? `<div>${z[12]}.</div>` : ''}
    ${ups.length ? '<b>Rejettent à proximité :</b><ul>' + ups.map(([c, how, km]) => {
      const a = aggBy[c]; return a ? `<li>${esc(a[1])} <span class="sub">${fmt(a[5])} EH · ${how}, à ${km.toLocaleString('fr-FR')} km${a[6] ? ' · <b>non conforme</b>' : ''}</span></li>` : '';
    }).join('') + '</ul>' : '<div class="sub">Aucune agglomération de 2 000 EH ou plus ne rejette à proximité.</div>'}
    ${z[11] ? `<div class="sub"><a href="${z[11]}">Profil officiel de la baignade (ministère de la Santé)</a></div>` : ''}`;
}

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

const bath = L.map('map-bath', {preferCanvas: true}).setView([46.6, 2.4], 6);
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

const table = document.getElementById('agg-table'), more = document.getElementById('more');
more.addEventListener('click', () => { table.classList.remove('collapsed'); more.hidden = true; });
document.querySelectorAll('[data-group]').forEach(b => b.addEventListener('click', () => {
  b.parentElement.querySelectorAll('button').forEach(o => o.setAttribute('aria-pressed', o === b));
  table.classList.toggle('collapsed', !b.dataset.group && !more.hidden);
  table.querySelectorAll('tbody tr').forEach(tr => tr.hidden = b.dataset.group && tr.dataset.group !== b.dataset.group);
}));

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
      ? (item[7].length ? '<b>Non conforme :</b> ' + item[7].map(esc).join(' ; ') : 'Conforme selon les services de l’État')
        + ` · ${fmt(item[5])} EH`
      : `Baignade (${item[6]}) · ${DATA.quality[item[5]]} en ${DATA.season}`;
    return `<li><button type="button" data-${kind}="${item[0]}"><b>${esc(item[1])}</b> <span class="sub">${esc(item[2])}${item[2] ? ' · ' : ''}${sub}</span></button></li>`;
  }).join('') + (hits.length > 12 ? `<li class="sub">… et ${hits.length - 12} de plus : précisez la recherche.</li>` : '')
  : '<li class="sub">Introuvable. C’est peut-être une commune de moins de 2 000 EH : elles ne sont pas évaluées ici.</li>';
});
"""


def typo(html: str) -> str:
    """French spacing in the prose: no-break space before « : » and inside guillemets, narrow one before ; ? !"""
    html = re.sub(r" :(?=[\s<])", NBSP + ":", html)
    html = re.sub(r" ([;?!])(?=[\s<])", NNBSP + r"\1", html)
    return html.replace("« ", "«" + NBSP).replace(" »", NBSP + "»")


def pct(x: float) -> str:
    return f"{x:.0f}{NNBSP}%"


def long_date(iso: str) -> str:
    y, m, dd = (int(p) for p in iso[:10].split("-"))
    return f"{'1er' if dd == 1 else dd} {MONTHS[m - 1]} {y}"


def group_of(a: dict) -> str:
    if a["verdict"] != "no":
        return ""
    return next((g for g in STEP if g in a["fails"]), "other")


def _missing(p: dict) -> list[str]:
    """Treatment the directive requires and the plant lacks."""
    req_bio, req_n, req_p = p["required"]
    has_bio, has_n, has_p, _ = p["existing"]
    out = []
    if req_bio == "Traitement secondaire" and has_bio != "Traitement secondaire":
        out.append("traitement secondaire")
    if req_n and not (has_n == req_n or has_n == "Dénitrification plus poussée"):
        out.append(req_n.lower())
    if req_p and not (has_p == req_p or has_p == "Déphosphatation plus poussée"):
        out.append(req_p.lower())
    return out


def why(a: dict) -> list[str]:
    """What fails, in plain sentences with the plant and the official cause."""
    out = []
    multi = len(a["plants"]) > 1
    if "collection" in a["fails"]:
        out.append("La collecte n'est pas conforme : trop d'eaux usées partent dans le milieu avant d'arriver "
                   "à la station, par temps sec ou par temps de pluie")
    if "equipment" in a["fails"]:
        for p in a["plants"]:
            if p["equipment"] == "no":
                miss = _missing(p)
                out.append(f"La station{' ' + p['name'] if multi else ''} n'a pas l'équipement exigé"
                           + (f" ({', '.join(miss)})" if miss else ""))
    if "performance" in a["fails"]:
        for p in a["plants"]:
            if p["performance"] == "no":
                checks = [CHECK[k] for k in p["failed"]]
                s = f"La station{' ' + p['name'] if multi else ''} n'épure pas comme il faut"
                if checks:
                    s += f" (rejets au-dessus des limites en {', '.join(checks)})"
                if p["cause"]:
                    s += f" ; motif retenu : {p['cause'][0].lower() + p['cause'][1:]}"
                out.append(s)
    if a["verdict"] == "no" and not out:
        out.append("Non conforme selon les services de l'État, sans détail par critère")
    return out


def hist_text(history: dict) -> str:
    k, m = sum(q == "insuficiente" for q in history.values()), len(history)
    if not k:
        return ""
    if m == 1:
        return "C'est sa première saison classée"
    return f"Insuffisante {'lors des' if k == m else f'{k} fois sur les'} {m} dernières saisons"


def events_text(z: dict, season: int) -> str:
    e = z.get("events", {})
    parts = []
    if "health_ban" in e:
        h = e["health_ban"]
        parts.append(f"Baignade interdite pour raison sanitaire {h['count']} fois en {season}"
                     + (f" ({n(h['days'], 'fr')} jour{'s' if h['days'] > 1 else ''})" if h["days"] else ""))
    if "cyanobacteria" in e:
        parts.append(f"cyanobactéries {e['cyanobacteria']['count']} fois")
    if "short_term_pollution" in e:
        parts.append(f"pollution à court terme {e['short_term_pollution']['count']} fois")
    s = " ; ".join(parts)
    return s[:1].upper() + s[1:]


def faecal_text(z: dict) -> str:
    if z["quality"] != "insuficiente":
        return ""
    ec, ie = POOR_LIMITS["inland" if z["type"] in ("riverBathingWater", "lakeBathingWater") else "sea"]
    return (f"Contamination fécale : ses analyses dépassent trop souvent {n(ec, 'fr')} <i>E. coli</i> "
            f"ou {n(ie, 'fr')} entérocoques pour 100{NNBSP}ml")


def _hist_html(history: dict) -> str:
    return '<span class="hist">' + "".join(
        f'<i style="background:var(--q-{q})" title="{s} : {QUALITY[q]}"></i>' for s, q in history.items()) + "</span>"


def _eea_cell(a: dict) -> str:
    e = a["eea"]
    if e is None:
        return '<span class="sub">absente du rapport</span>'
    if not e["gaps"]:
        return '<span class="sub">aucune carence</span>'
    return escape(t("fr", f"gap_{e['main_gap']}"))


def _agg_row(a: dict, zones: dict, i: int) -> str:
    linked = [zones[z["id"]] for z in a["zones"] if z["id"] in zones]
    bad = sum(z["quality"] == "insuficiente" for z in linked)
    down = (f'{len(linked)} baignade{"s" if len(linked) > 1 else ""}'
            + (f'<span class="sub">{bad} insuffisante{"s" if bad > 1 else ""}</span>' if bad else "")) if linked else "—"
    sub = " · ".join(x for x in (escape(a["commune"] or "") if a["commune"] != a["name"] else "",
                                 f"dép. {a['dept']}" if a["dept"] else "") if x)
    group = group_of(a)
    reasons = "".join(f'<div class="why"><span class="dot" style="background:var(--g-{group})"></span>{escape(w)}</div>'
                      for w in why(a))
    fixed = {"eea_fixed": "taille corrigée (rapport à l'AEE)", "eea": "taille du rapport à l'AEE",
             "capacity": "capacité des stations"}.get(a["pe_source"], "")
    fixed = f'<span class="sub">{fixed}</span>' if fixed else ""
    return (f'<tr id="{a["code"]}" data-group="{group}"{" data-extra" if i >= TOP_ROWS else ""}>'
            f'<td><a class="go" href="#map" data-agg="{a["code"]}"><b>{escape(a["name"])}</b></a>'
            f'<span class="sub">{sub}</span></td>'
            f'<td class="num" data-label="EH">{n(a["pe"], "fr")}{fixed}</td><td>{reasons}</td>'
            f'<td data-label="Lecture AEE 2022">{_eea_cell(a)}</td><td class="num" data-label="Baignade">{down}</td></tr>')


def _zone_row(z: dict, aggs: dict, season: int) -> str:
    ups = []
    for u in z["upstream"]:
        a = aggs[u["code"]]
        bad = " · <b>non conforme</b>" if a["verdict"] == "no" else ""
        ups.append(f'<a href="#{a["code"]}" class="go">{escape(a["name"])}</a> '
                   f'<span class="sub">{n(a["pe"], "fr")}{NNBSP}EH · {METHOD[u["method"]]}, à {d(u["km"], "fr")}{NNBSP}km{bad}</span>')
    upstream = "".join(f"<div>{u}</div>" for u in ups) or '<span class="sub">Aucune agglomération de 2 000 EH ou plus</span>'
    profile = (f'<span class="sub"><a href="{escape(z["profile"])}">Profil officiel</a></span>' if z.get("profile") else "")
    where = " · ".join(x for x in (escape(nice_name(z.get("commune") or "", "fr")), ZONE_TYPE.get(z["type"], "")) if x)
    ev = events_text(z, season)
    return (f'<tr id="{z["id"]}"><td><a class="go" href="#map-bath" data-bath="{z["id"]}"><b>{escape(nice_name(z["name"], "fr"))}</b></a>'
            f'<span class="sub">{where}</span>{profile}</td>'
            f'<td>{_hist_html(z["history"])}<span class="sub">{hist_text(z["history"])}</span>'
            f'<span class="sub">{faecal_text(z)}</span>{f"<span class=sub>{escape(ev)}</span>" if ev else ""}</td>'
            f'<td>{upstream}</td></tr>')


def _map_data(data: dict) -> str:
    rel = data["release"]
    aggs = [[a["code"], a["name"], nice_name(a["commune"] or "", "fr"), round(a["lon"], 5), round(a["lat"], 5), a["pe"],
             group_of(a), why(a), [z["id"] for z in a["zones"]]] for a in data["aggs"] if a["lon"] is not None]
    zones = [[z["id"], nice_name(z["name"], "fr"), nice_name(z.get("commune") or "", "fr"), round(z["lon"], 5),
              round(z["lat"], 5), z["quality"], ZONE_TYPE.get(z["type"], ""), hist_text(z["history"]),
              [[u["code"], METHOD[u["method"]], u["km"]] for u in z["upstream"]],
              sum(q == "insuficiente" for q in z["history"].values()), faecal_text(z), z.get("profile"),
              events_text(z, rel["season"])]
             for z in data["zones"] if z["lon"] is not None]
    blob = json.dumps({"aggs": aggs, "zones": zones, "quality": QUALITY, "season": rel["season"]},
                      ensure_ascii=False, separators=(",", ":"))
    return blob.replace("</", "<\\/")


def render(data: dict) -> Path:
    now = datetime.now(ZoneInfo("Europe/Paris"))
    rep, eru, bai, rel, f = data["report"], data["eru"], data["baignade"], data["release"], data["figures"]
    aggs = {a["code"]: a for a in data["aggs"]}
    zones = {z["id"]: z for z in data["zones"]}
    bad = [a for a in data["aggs"] if a["verdict"] == "no"]
    poor = sorted((z for z in data["zones"] if z["quality"] == "insuficiente"),
                  key=lambda z: (-sum(q == "insuficiente" for q in z["history"].values()), z["name"]))
    groups = {g: sum(group_of(a) == g for a in bad) for g in [*STEP, "other"]}
    ag = f["agreement"]
    one_in = round(f["total_pe"] / f["noncompliant_pe"])
    seasons = len(poor[0]["history"]) if poor else 4
    fixed = [aggs[code]["name"] for code in f["pe_fixed"]]
    causes = f["causes"][:6]
    nf = lambda v: n(v, "fr")
    poor_differ = sum("insuficiente" in (zones[i]["quality"], zones[i]["ministry_quality"]) for i in f["class_differ"])
    diff = ("" if not f["class_differ"] else
            f" (les {nf(len(f['class_differ']))} écarts {'ne touchent aucune' if not poor_differ else 'touchent ' + nf(poor_differ)} "
            f"baignade{'s' if poor_differ > 1 else ''} insuffisante{'s' if poor_differ > 1 else ''} ; la page suit l'AEE)")
    siblings = "\n".join(
        f'    <li{" aria-current=\"page\"" if slug == SLUG else ""}>'
        f'<a href="https://asensio94.github.io/{slug}/{"fr/" if slug == SLUG else ""}">{name}</a></li>'
        for slug, name in SIBLINGS)

    def step(k: int, g: str, text: str, detail: str) -> str:
        return (f'<div class="card" style="--c:var(--g-{g})"><h3><small>{k}</small>{STEP[g]}</h3><p>{text}</p>'
                f'<div class="fail">{nf(groups[g])}</div><p>{detail}</p></div>')

    body = f"""<header class="site-header">
  <h1>{LOGO_SVG}Épuration <span>et baignade</span></h1>
  <p class="lede">Où vont les eaux de vos toilettes ? Les villes et villages de France qui n'épurent pas leurs eaux
  usées comme l'exige la loi européenne, et les baignades situées en aval.</p>
  <p class="lang" lang="es"><a href="../">Versión en español: España</a></p>
  <div class="figures">
    <div><b>{nf(f["noncompliant"])}</b><span>agglomérations non conformes en {eru["year"]}, sur {nf(f["assessed"])}</span></div>
    <div><b>1 part sur {one_in}</b><span>des eaux usées de France vient de ces agglomérations</span></div>
    <div><b>{nf(f["poor"])}</b><span>baignades insuffisantes en {rel["season"]}, sur {nf(f["zones"])}</span></div>
  </div>
</header>
<main>
  <h2 class="block">En quelques mots</h2>
  <div class="prose">
    <p>Les eaux usées des villes doivent être épurées avant d'être rejetées dans une rivière, un lac ou la mer. La
    <a href="{DIRECTIVE}">directive 91/271/CEE</a> du Conseil fixe le traitement exigé pour chaque agglomération selon sa
    taille et le milieu où elle rejette, et les valeurs que l'eau épurée doit respecter (pour le traitement secondaire,
    par exemple, 25 mg/l de DBO<sub>5</sub> et 125 mg/l de DCO). Les échéances sont passées depuis 1998–2005. La
    Commission européenne poursuit la France pour la non-conformité de plusieurs agglomérations : avis motivé du
    14 mai 2020 (procédure 2017/2125), puis saisine de la Cour de justice de l'Union européenne le 2 mai 2023
    (<a href="{INFRINGEMENT}">données publiées par l'État</a>).</p>
    <p>Chaque année, les services de l'État (police de l'eau) jugent si chaque agglomération de 2 000 équivalents-habitants
    (EH) ou plus est conforme, et le ministère de la Transition écologique publie ce verdict sur le
    <a href="{ERU_PORTAL}">portail de l'assainissement collectif</a>. Cette page reprend le verdict de {eru["year"]}, le
    plus récent, et suit l'eau de chaque station jusqu'aux baignades situées en aval. En complément, elle applique aux
    données que la France a envoyées à l'Agence européenne pour l'environnement (AEE) les mêmes règles que la page
    espagnole : une deuxième lecture, indépendante.</p>
  </div>

  <h2 class="block">Ce que demande la loi, en trois étapes</h2>
  <p class="block">Sous chaque étape, combien d'agglomérations y échouent. Chacune compte une seule fois, pour son
  premier échec : {nf(f["noncompliant"])} au total{f", dont {nf(groups['other'])} sans détail par critère" if groups["other"] else ""}.</p>
  <div class="steps">
    {step(1, "collection", "Amener les eaux des maisons, commerces et industries par les égouts jusqu'à une station, sans qu'elles se perdent en chemin, ni par temps sec ni quand il pleut.",
          f"ont une collecte non conforme. Pour {nf(f['collection_pending'])} autres, l'évaluation de la collecte est en cours.")}
    {step(2, "equipment", "Avoir une station avec le traitement exigé : biologique (secondaire) dans tous les cas, et l'élimination de l'azote ou du phosphore en zone sensible.",
          f"échouent ici en premier ; {nf(f['fails']['equipment'])} au total n'ont pas l'équipement exigé.")}
    {step(3, "performance", "Que la station fonctionne : ses analyses (l'autosurveillance) doivent respecter les limites, et être faites et transmises correctement.",
          f"échouent ici en premier ; {nf(f['fails']['performance'])} au total n'ont pas des performances conformes.")}
  </div>
  <p class="block">Quand une station échoue, les services de l'État en donnent le motif. Les plus fréquents parmi les
  agglomérations non conformes :</p>
  <ul class="prose">
{chr(10).join(f"    <li>{escape(cause)} : {nf(k)}</li>" for cause, k in causes)}
  </ul>
  <dl class="words">
    <div class="card"><dt>Agglomération d'assainissement</dt><dd>La zone dont les eaux usées vont au même système de
    collecte et à la même station (ou aux mêmes stations). Elle peut couvrir une commune, une partie de commune ou
    plusieurs communes. Seules celles de 2 000 EH ou plus sont évaluées ici.</dd></div>
    <div class="card"><dt>EH (équivalent-habitant)</dt><dd>La pollution qu'une personne rejette dans l'eau en un jour.
    Elle additionne habitants, touristes et industries raccordées : la France compte ainsi {nf(f["total_pe"] / 1e6)} millions
    d'EH dans les agglomérations évaluées.</dd></div>
  </dl>

  <h2 class="block">Deux lectures, et ce qu'elles disent ensemble</h2>
  <div class="prose">
    <p>Le verdict officiel ({eru["year"]}) et la règle de la directive appliquée au rapport de la France à l'AEE
    ({rep["year"]}, avec la même méthode que pour l'Espagne) ne regardent ni la même année ni tout à fait les mêmes
    critères : le verdict officiel compte aussi une autosurveillance incomplète ou mal faite et les déversements par
    temps de pluie, que le rapport européen ne détaille pas. Sur les {nf(ag["compared"])} agglomérations présentes dans
    les deux sources :</p>
  </div>
  <table class="agree">
    <tr><th></th><th>Carence selon la règle (AEE {rep["year"]})</th><th>Aucune carence</th></tr>
    <tr><th>Non conforme (État, {eru["year"]})</th><td>{nf(ag["both"])}</td><td>{nf(ag["official_only"])}</td></tr>
    <tr><th>Conforme (État, {eru["year"]})</th><td>{nf(ag["eea_only"])}</td><td>{nf(ag["neither"])}</td></tr>
  </table>
  <p class="block">Les deux lectures s'accordent pour {nf(ag["both"] + ag["neither"])} agglomérations sur
  {nf(ag["compared"])}. Le verdict officiel est plus sévère : il signale {nf(ag["official_only"])} agglomérations où la
  règle ne voit rien, souvent pour l'autosurveillance ou la collecte. {nf(ag["missing"])} agglomérations du verdict
  {eru["year"]} n'apparaissent pas dans le rapport de {rep["year"]} (nouvelles, redécoupées ou passées au-dessus de
  2 000 EH). La page et les signaux se fondent sur le verdict officiel ; la deuxième lecture figure dans la liste.</p>

  <h2 class="block" id="chercher">Cherchez votre commune ou votre plage</h2>
  <div class="search"><input id="q" type="search" placeholder="Une commune, une agglomération ou une baignade…"
    autocomplete="off" aria-label="Chercher une commune ou une baignade" aria-controls="results"></div>
  <ul id="results" aria-live="polite"></ul>

  <h2 class="block" id="carte">La carte</h2>
  <div class="legend lead"><b>Cercles : agglomérations</b> (plus grands quand elles produisent plus d'eaux usées). La couleur dit ce qui échoue en premier :</div>
  <div class="legend">
    {"".join(f'<span><span class="dot" style="background:var(--g-{g})"></span>{k}. {STEP[g]} ({nf(groups[g])})</span>' for k, g in enumerate(STEP, 1))}
    {f'<span><span class="dot" style="background:var(--g-other)"></span>Sans détail ({nf(groups["other"])})</span>' if groups["other"] else ""}
    <span><span class="dot" style="background:var(--g-ok)"></span>Conformes (masquées au départ)</span>
  </div>
  <div class="legend lead"><b>Losanges : baignades</b>, selon leur classement {rel["season"]} :</div>
  <div class="legend">
    {"".join(f'<span><span class="sq" style="background:var(--q-{q})"></span>{QUALITY[q]} ({nf(f["quality"][q])})</span>' for q in QUALITY)}
  </div>
  <p class="legend">Cliquez sur un cercle pour voir les baignades où arrivent ses rejets, ou sur un losange pour voir qui rejette à proximité.</p>
  <div class="tools" role="group" aria-label="Ce que montre la carte">
    <button type="button" data-layer="ok" aria-pressed="false">Montrer les conformes</button>
    <button type="button" data-layer="zonesGood" aria-pressed="false">Montrer les baignades bonnes et excellentes</button>
{chr(10).join(f'    <button type="button" data-view="{v}">{label}</button>' for label, v in VIEWS)}
  </div>
  <div id="map" role="region" aria-label="Carte des agglomérations et des baignades"></div>

  <h2 class="block" id="agglomerations">Les {nf(f["noncompliant"])} agglomérations non conformes</h2>
  <p class="block">De la plus grande à la plus petite. « Lecture AEE 2022 » : la première carence que la règle de la
  directive trouve dans le rapport de {rep["year"]}. « Baignade » : les baignades où arrivent ses rejets.</p>
  <div class="tools" role="group" aria-label="Filtrer par étape">
    <button type="button" data-group="" aria-pressed="true">Toutes ({nf(len(bad))})</button>
{chr(10).join(f'    <button type="button" data-group="{g}" aria-pressed="false">{k}. {STEP[g]} ({nf(groups[g])})</button>' for k, g in enumerate(STEP, 1))}
  </div>
  <div class="wrap"><table class="list collapsed" id="agg-table">
    <thead><tr><th>Où</th><th class="num">EH</th><th>Ce qui ne va pas</th><th>Lecture<br>AEE 2022</th><th class="num">Baignade</th></tr></thead>
    <tbody>
{chr(10).join(_agg_row(a, zones, i) for i, a in enumerate(bad))}
    </tbody>
  </table></div>
  <button type="button" class="more" id="more">Voir les {nf(max(0, len(bad) - TOP_ROWS))} autres</button>

  <h2 class="block" id="baignades">Les {nf(f["poor"])} baignades insuffisantes</h2>
  <div class="prose">
    <p>Chaque été, l'agence régionale de santé analyse l'eau de chaque baignade à la recherche de deux bactéries qui
    vivent dans l'intestin et arrivent dans l'eau avec les matières fécales : <i>E. coli</i> et les entérocoques. Leur
    présence signale une contamination fécale, qui peut apporter des virus et des bactéries responsables de
    gastro-entérites, d'otites ou d'infections de la peau. Avec les analyses des quatre dernières saisons, chaque
    baignade reçoit un classement selon la <a href="{BATHING_DIRECTIVE}">directive 2006/7/CE</a> : excellente, bonne,
    suffisante ou insuffisante.</p>
    <p><b>Insuffisante</b> veut dire que la contamination fécale dépasse trop souvent la limite : en mer et dans les
    eaux de transition, plus de {nf(POOR_LIMITS["sea"][0])} <i>E. coli</i> ou {nf(POOR_LIMITS["sea"][1])} entérocoques
    pour 100 ml ; en rivière et en lac, plus de {nf(POOR_LIMITS["inland"][0])} ou {nf(POOR_LIMITS["inland"][1])}
    (percentile 90 des analyses). Il faut alors informer les baigneurs, interdire ou déconseiller la baignade et
    chercher l'origine. Après cinq saisons insuffisantes de suite, la baignade est interdite ou
    déconseillée de façon permanente.</p>
    <p>En {rel["season"]}, la baignade a été interdite pour raison sanitaire au moins une fois sur {nf(f["health_ban_sites"])}
    sites ({nf(f["events"]["health_ban"])} interdictions). Les
    cyanobactéries ont fait fermer {nf(f["events"]["cyanobacteria"])} fois des baignades en eau douce.</p>
    <p>Pour {nf(f["poor_with_upstream"])} des {nf(f["poor"])} baignades insuffisantes, une agglomération rejette à
    proximité, en amont ou sur la même côte, et pour {nf(f["poor_with_noncompliant_upstream"])} d'entre elles cette
    agglomération est non conforme. Pour les {nf(f["poor"] - f["poor_with_upstream"])} autres, aucune agglomération de
    2 000 EH ou plus ne rejette à proximité : la cause est à chercher du côté des petites communes, de
    l'assainissement non collectif, de l'élevage ou du ruissellement.</p>
  </div>
  <div class="legend lead"><b>Carte des baignades les moins bien classées</b> en {rel["season"]} :</div>
  <div class="legend">
    <span><span class="dot" style="background:var(--q-insuficiente)"></span>Insuffisante ({nf(f["quality"]["insuficiente"])}), plus grande quand elle l'est depuis plus de saisons</span>
    <span><span class="dot" style="background:var(--q-suficiente)"></span>Suffisante ({nf(f["quality"]["suficiente"])}), tout juste</span>
  </div>
  <p class="legend">Cliquez sur une baignade pour voir son historique et qui rejette à proximité (lignes bleues).</p>
  <div class="tools" role="group" aria-label="Aller à">
{chr(10).join(f'    <button type="button" data-map="bath" data-view="{v}">{label}</button>' for label, v in VIEWS)}
  </div>
  <div id="map-bath" role="region" aria-label="Carte des baignades insuffisantes et suffisantes"></div>
  <p class="block">D'abord celles qui sont insuffisantes depuis le plus de saisons. Carrés : classement de chacune des {seasons} dernières saisons.</p>
  <div class="wrap"><table class="list">
    <thead><tr><th>Baignade</th><th>Historique</th><th>Qui rejette à proximité</th></tr></thead>
    <tbody>
{chr(10).join(_zone_row(z, aggs, rel["season"]) for z in poor)}
    </tbody>
  </table></div>

  <section class="method">
    <h2>Comment c'est calculé</h2>
    <ol>
      <li><b>Le verdict de l'État.</b> Le <a href="{ERU_PORTAL}">portail de l'assainissement collectif</a> du ministère
      de la Transition écologique publie chaque année une ligne par station de traitement des eaux usées : son
      agglomération, sa capacité, la charge reçue, le traitement exigé et celui qui existe, le point de rejet et le milieu
      récepteur, et la conformité réglementaire jugée par les services de police de l'eau. On garde les
      {nf(f["assessed"])} agglomérations de 2 000 EH ou plus (celles que vise la directive) et leurs {nf(f["plants"])}
      stations, pour l'année {eru["year"]} (dernière mise à jour le {long_date(eru["updated"])}). Le fichier est
      téléchargé tel quel ; ni le maître d'ouvrage ni l'exploitant ne sont conservés.</li>
      <li><b>Ce que juge l'État.</b> L'agglomération est conforme si trois critères le sont, selon la directive et
      l'<a href="{ARRETE_2015}">arrêté du 21 juillet 2015</a>. <i>Équipement</i> : la station a le niveau de traitement
      exigé (secondaire ; dénitrification ou déphosphatation en zone sensible). <i>Performance</i> : les analyses de
      l'autosurveillance respectent les limites (DBO<sub>5</sub>, DCO, azote, phosphore) et l'autosurveillance est faite,
      validée et transmise. <i>Collecte</i> : pas de rejet direct par temps sec, et des déversements par temps de pluie
      limités (en volume, en pollution ou en jours de déversement). Une agglomération est non conforme si un critère ne
      l'est pas. La page reprend ce verdict sans le modifier.</li>
      <li><b>La deuxième lecture.</b> Tous les deux ans, la France envoie à l'AEE le même type d'informations
      (<a href="{EEA_UWWTD}">Waterbase UWWTD</a>). Le dernier rapport porte sur {rep["year"]} (situation au
      {long_date(rep["situation"])}). On lui applique les articles 3, 4 et 5 de la directive, comme pour l'Espagne :
      au moins {pct(c.MIN_COLLECTED_PCT)} des eaux collectées ou traitées par un système individuel adéquat, pas plus de
      {pct(c.MAX_UNTREATED_PCT)} rejetés sans traitement, traitement secondaire dès {nf(c.SECONDARY_FRESH_PE)} EH
      ({nf(c.SECONDARY_COASTAL_PE)} EH en mer), traitement plus rigoureux dès {nf(c.STRINGENT_PE)} EH en zone sensible,
      et des analyses conformes. Les codes d'agglomération sont les mêmes dans les deux sources (le code SANDRE précédé
      de « FR »), ce qui permet de les comparer une à une.</li>
      <li><b>Les baignades.</b> Le classement de chaque baignade vient de l'AEE ({rel["season"]}, publié le
      {long_date(rel["published"])}, avec l'historique des {seasons} dernières saisons). Le ministère de la Santé publie
      sur <a href="{c.BAIGNADE_PAGE}">data.gouv.fr</a> le même classement, la commune de chaque site, le lien vers son
      profil et les événements de la saison (interdictions, cyanobactéries, pollutions à court terme). Les deux
      classements coïncident pour {nf(f["eea_zones"] - len(f["class_differ"]))} sites sur {nf(f["eea_zones"])}{diff} ; les {nf(f["zones"] - f["eea_zones"])} sites que l'AEE ne liste pas
      encore viennent du ministère. Des événements, on ne garde que le nombre et la durée par type : les
      commentaires libres ne sont pas repris.</li>
      <li><b>Le chemin de l'eau.</b> Chaque point de rejet d'une station est relié aux baignades de trois façons, comme
      pour l'Espagne. <i>En aval sur la rivière</i> : le rejet et la baignade sont à moins de {nf(c.RIVER_SNAP_KM)} km d'un
      tronçon du réseau HydroRIVERS, et en suivant la rivière depuis le rejet on atteint la baignade en moins de
      {nf(c.RIVER_DOWNSTREAM_KM)} km. <i>Par l'embouchure</i> : la rivière atteint la mer en moins de
      {nf(c.RIVER_DOWNSTREAM_KM)} km et la baignade est à moins de {nf(c.SAME_BODY_KM)} km de l'embouchure. <i>Même côte
      ou même lac</i> : le rejet et la baignade sont dans la même masse d'eau et à moins de {nf(c.SAME_BODY_KM)} km. Les
      rejets dans le sol ou diffus ne sont reliés à aucune baignade.</li>
    </ol>
    <table class="params">
      <tr><th>Paramètre</th><th class="num">Valeur</th></tr>
      <tr><td>Taille minimale des agglomérations évaluées</td><td class="num">2 000 EH</td></tr>
      <tr><td>Deuxième lecture : eaux collectées au minimum</td><td class="num">{pct(c.MIN_COLLECTED_PCT)}</td></tr>
      <tr><td>Deuxième lecture : eaux rejetées sans traitement au maximum</td><td class="num">{pct(c.MAX_UNTREATED_PCT)}</td></tr>
      <tr><td>Traitement secondaire : rivières, lacs, estuaires</td><td class="num">{nf(c.SECONDARY_FRESH_PE)} EH</td></tr>
      <tr><td>Traitement secondaire : mer</td><td class="num">{nf(c.SECONDARY_COASTAL_PE)} EH</td></tr>
      <tr><td>Traitement plus rigoureux : zones sensibles</td><td class="num">{nf(c.STRINGENT_PE)} EH</td></tr>
      <tr><td>Distance maximale d'un point au réseau de rivières</td><td class="num">{nf(c.RIVER_SNAP_KM)} km</td></tr>
      <tr><td>Parcours maximal vers l'aval</td><td class="num">{nf(c.RIVER_DOWNSTREAM_KM)} km</td></tr>
      <tr><td>Distance maximale sur la côte, dans un estuaire ou un lac</td><td class="num">{nf(c.SAME_BODY_KM)} km</td></tr>
    </table>
    <h3>Vérifications</h3>
    <ul>
      <li>Classement des baignades : l'AEE et le ministère de la Santé donnent le même pour
      {nf(f["eea_zones"] - len(f["class_differ"]))} des {nf(f["eea_zones"])} sites que les deux publient en {bai["season"]}{diff}.</li>
      <li>Les deux lectures des agglomérations sont comparées plus haut : elles s'accordent pour
      {pct(100 * (ag["both"] + ag["neither"]) / ag["compared"])} des agglomérations présentes dans les deux sources.</li>
      {f'<li>Taille corrigée : {", ".join(escape(x) for x in fixed)}. Le portail lui attribue une taille plus de vingt fois supérieure à la capacité de ses stations, ce qui est une erreur de saisie ; on retient la taille du rapport à l\'AEE.</li>' if fixed else ""}
      {f'<li>Taille absente du portail pour {nf(sum(f["pe_missing"].values()))} agglomérations : on retient la taille du rapport à l\'AEE ({nf(f["pe_missing"]["eea"])}) ou, à défaut, la capacité de leurs stations ({nf(f["pe_missing"]["capacity"])}).</li>' if f["pe_missing"] else ""}
    </ul>
    <h3>Ce qui reste en dehors, et pourquoi</h3>
    <ul>
      <li>Les agglomérations de moins de 2 000 EH : le portail les publie, mais la directive ne leur fixe pas les mêmes
      obligations, et la comparaison avec l'Espagne se ferait sur des bases différentes.</li>
      <li>L'assainissement non collectif (fosses septiques et autres systèmes individuels) : il n'existe pas de données
      ouvertes nationales sur leur conformité.</li>
      <li>Les rejets industriels qui ne passent pas par une station urbaine, et le détail des déversoirs d'orage : ils
      ne figurent pas dans ces sources (les déversements par temps de pluie comptent seulement à travers le critère de
      collecte).</li>
      <li>Outre-mer : les {nf(f["overseas"])} agglomérations de Guadeloupe, Martinique, Guyane, La Réunion et Mayotte sont
      dans la liste et sur la carte, avec leur verdict, mais HydroRIVERS (version Europe) ne couvre pas ces territoires.
      Leurs rejets ne sont donc reliés aux baignades que lorsqu'ils partagent la même masse d'eau, jamais en suivant une
      rivière.</li>
    </ul>
    <h3>Limites</h3>
    <ul>
      <li>Le verdict officiel est celui des services de l'État, pas celui de la Commission européenne, qui tient compte
      d'autres éléments et d'autres échéances.</li>
      <li>Le verdict porte sur l'année {eru["year"]} : une station mise aux normes depuis reste non conforme ici jusqu'au
      verdict suivant.</li>
      <li>Les noms d'agglomérations et de stations sont ceux du portail, parfois abrégés ou en majuscules ; ils sont
      seulement remis en minuscules.</li>
      <li>HydroRIVERS est un réseau de rivières mondial d'environ 500 m de précision. Certains points tombent sur le
      tronçon voisin et les petits ruisseaux n'y sont pas : un lien peut manquer ou être de trop. Sur la côte, la
      distance est en ligne droite, sans courants.</li>
    </ul>
  </section>
</main>
<footer class="site-footer">
  <p class="principle">Données publiques, règles visibles et chaque chiffre relié à sa source. Des indices, pas des verdicts.</p>
  <p>Assainissement : <a href="{ERU_PORTAL}">portail de l'assainissement collectif</a>, ministère de la Transition
  écologique, conformité {eru["year"]}, et <a href="{EEA_UWWTD}">Waterbase UWWTD</a>, rapport de la France de {rep["year"]}
  à l'AEE. Baignades : <a href="{EEA_BATHING.format(uuid=rel["uuid"])}">état des eaux de baignade {rel["season"]}</a>,
  AEE, et <a href="{c.BAIGNADE_PAGE}">données de la saison balnéaire</a>, ministère de la Santé (licence ouverte).
  Réseau de rivières : <a href="{HYDROSHEDS}">HydroRIVERS</a> (Lehner et Grill, 2013, <i>Hydrological Processes</i>
  27(15) : 2171–2186). Carte : © contributeurs d'OpenStreetMap. Code sur <a href="{c.REPO}">GitHub</a> (MIT) ;
  données dérivées CC BY 4.0. Page générée le {now:%d/%m/%Y à %H:%M} (heure de Paris).</p>
  <nav aria-label="Projets frères" lang="es"><ul class="siblings">
{siblings}
  </ul></nav>
</footer>"""

    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Épuration et baignade</title>
<meta name="description" content="Les villes et villages de France qui n'épurent pas leurs eaux usées comme l'exige la loi européenne, et les baignades situées en aval.">
{favicon_link(ACCENT, ACCENT_DARK)}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
{COMMON_CSS}
{CSS}
{CSS_FR}
</style>
</head>
<body>
{typo(body)}
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>{SCRIPT.replace("__DATA__", _map_data(data))}</script>
</body>
</html>
"""
    out = c.DOCS_DIR / "fr" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
