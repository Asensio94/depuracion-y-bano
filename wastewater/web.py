"""The published page: one self-contained HTML file (data embedded), Spanish text, shared sibling style."""
from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config as c
from .compliance import GAPS, RECAST
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

# The three things an agglomeration can lack, as the map groups them.
GROUP = {"collection": "collection", "untreated": "collection", "no_plant": "collection",
         "secondary": "secondary", "secondary_performance": "secondary",
         "stringent": "stringent", "stringent_performance": "stringent"}
GROUP_LABEL = {"collection": "Colector o depuradora", "secondary": "Tratamiento secundario",
               "stringent": "Tratamiento más riguroso"}
QUALITY = {"excelente": "Excelente", "buena": "Buena", "suficiente": "Suficiente",
           "insuficiente": "Insuficiente", "sin_clasificar": "Sin clasificar"}
ZONE_TYPE = {"coastalBathingWater": "costa", "transitionalBathingWater": "transición",
             "riverBathingWater": "río", "lakeBathingWater": "lago o embalse"}
METHOD = {"river": "río abajo", "mouth": "por la desembocadura", "water_body": "misma masa de agua"}
EEA_UWWTD = "https://www.eea.europa.eu/en/datahub/datahubitem-view/6244937d-1c2c-47f5-bdf1-33ca01ff1715"
EEA_BATHING = "https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/{uuid}"
HYDROSHEDS = "https://www.hydrosheds.org/products/hydrorivers"
DIRECTIVE = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:31991L0271"
RECAST_URL = "https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32024L3019"
JUDGMENT = "https://curia.europa.eu/juris/liste.jsf?num=C-205/17"

CSS = f""":root{{--accent:{ACCENT};--accent-dark:{ACCENT_DARK};
  --g-collection:#b42318;--g-secondary:#d9600f;--g-stringent:#b8860b;--g-ok:#9a948d;
  --q-insuficiente:#b42318;--q-suficiente:#d99a00;--q-buena:#5b9bd5;--q-excelente:#2b59a6;--q-sin_clasificar:#9a948d}}
main{{max-width:1100px;margin:0 auto;padding:0 16px}}
.intro{{max-width:760px;margin:28px 0 8px}}
#map{{height:min(620px,75vh);border:1px solid var(--line);border-radius:8px;margin:12px 0 6px;background:var(--paper)}}
.leaflet-container{{font:inherit;font-size:.9rem}}
.leaflet-popup-content{{margin:12px 14px;line-height:1.4}}
.leaflet-popup-content h4{{margin:0 0 4px;font-size:1rem}}
.leaflet-popup-content .sub{{color:#6b625c;font-size:.82rem}}
.tools{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:20px 0 8px}}
.tools button{{font:inherit;font-size:.9rem;padding:6px 12px;border:1px solid var(--line);border-radius:999px;
  background:var(--paper);color:var(--ink);cursor:pointer}}
.tools button[aria-pressed="true"]{{background:var(--accent);border-color:var(--accent);color:var(--paper)}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;color:var(--muted);font-size:.85rem;margin:4px 0 0}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}}
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
.gap{{display:inline-block;font-size:.78rem;padding:1px 7px;border-radius:999px;margin:0 4px 3px 0;
  border:1px solid currentColor;white-space:nowrap}}
.gap.collection{{color:var(--g-collection)}}.gap.secondary{{color:var(--g-secondary)}}
.gap.stringent{{color:var(--g-stringent)}}.gap.recast{{color:var(--muted);border-style:dashed}}
.hist{{white-space:nowrap}}
.hist i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:2px;vertical-align:middle}}
tr[hidden]{{display:none}}
h2.block{{margin:40px 0 4px;font-family:var(--font-title);font-size:1.6rem}}
p.block{{color:var(--muted);margin:0 0 8px;max-width:760px}}
details.more{{margin:8px 0}}
"""


def fmt(x: float | None, digits: int = 0) -> str:
    """Spanish numbers: thousands with a point, decimals with a comma."""
    if x is None:
        return "—"
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def millions(x: float) -> str:
    return f"{fmt(x / 1e6, 2)} millones"


def long_date(iso: str) -> str:
    y, m, d = (int(p) for p in iso[:10].split("-"))
    return f"{d} de {MONTHS[m - 1]} de {y}"


def _gaps_html(a: dict) -> str:
    cur = "".join(f'<span class="gap {GROUP[g]}">{GAPS[g]}</span>' for g in a["gaps"])
    nxt = "".join(f'<span class="gap recast" title="Refundición de 2024">{RECAST[g]}</span>' for g in a["recast"])
    return cur + nxt


def _hist_html(history: dict) -> str:
    return '<span class="hist">' + "".join(
        f'<i style="background:var(--q-{q})" title="{s}: {QUALITY[q]}"></i>' for s, q in history.items()) + "</span>"


def _agg_row(a: dict, zones: dict) -> str:
    linked = [zones[z["id"]] for z in a["zones"] if z["id"] in zones]
    bad = [z for z in linked if z["quality"] in ("insuficiente", "suficiente")]
    down = (f'{len(linked)}' + (f'<span class="sub">{len(bad)} suficiente o peor</span>' if bad else "")) if linked else "—"
    plan = (f'{a["plan"]["date"][:4]}' if a["plan"] and a["plan"]["date"] else "—")
    muni = f'{escape(a["municipality"])} · ' if a["municipality"] else ""
    return (f'<tr id="{a["code"]}" data-group="{GROUP[a["main_gap"]]}">'
            f'<td><a class="go" href="#map" data-agg="{a["code"]}"><b>{escape(nice_name(a["name"]))}</b></a>'
            f'<span class="sub">{muni}{a["code"]}</span></td>'
            f'<td class="num">{fmt(a["pe"])}</td><td>{_gaps_html(a)}</td>'
            f'<td class="num">{plan}</td><td class="num">{down}</td></tr>')


def _zone_row(z: dict, aggs: dict) -> str:
    ups = []
    for u in z["upstream"]:
        a = aggs[u["code"]]
        mark = (f' <span class="gap {GROUP[a["main_gap"]]}">{GAPS[a["main_gap"]]}</span>' if a["gaps"] else "")
        ups.append(f'<a href="#{a["code"]}" class="go">{escape(nice_name(a["name"]))}</a> '
                   f'<span class="sub">{fmt(a["pe"])} h-e · {METHOD[u["method"]]}, {fmt(u["km"], 1)} km{mark}</span>')
    upstream = "".join(f"<div>{u}</div>" for u in ups) or '<span class="sub">Ningún vertido de aglomeración enlazado</span>'
    muni = escape(z["municipality"]) if z["municipality"] else ""
    return (f'<tr id="{z["id"]}"><td><a class="go" href="#map" data-zone="{z["id"]}"><b>{escape(nice_name(z["name"]))}</b></a>'
            f'<span class="sub">{muni} · {ZONE_TYPE.get(z["type"], "")}</span></td>'
            f'<td>{_hist_html(z["history"])}</td><td>{upstream}</td></tr>')


def _c205(aggs: dict) -> str:
    """The agglomerations of the 2018 fine: those still pending in 2022 should show a gap, the rest none."""
    pending = [n for k, n in c.C205_PENDING_2022.items() if k in aggs and aggs[k]["gaps"]]
    resolved = [n for k, n in c.C205_RESOLVED.items() if k in aggs and aggs[k]["gaps"]]
    return (f'Sentencia <a href="{JUDGMENT}">C-205/17</a>: de las {len(c.C205_PENDING_2022)} aglomeraciones por las que '
            f'España seguía pagando multa en 2022 (Barbate, Matalascañas, Alhaurín el Grande y Güímar), '
            f'{len(pending)} aparecen aquí con carencias; de las {len(c.C205_RESOLVED)} que ya se daban por resueltas, '
            f'{len(resolved) or "ninguna"}{" (" + ", ".join(resolved) + ")" if resolved else ""}. '
            f'Isla Cristina y Coín ya no figuran como aglomeraciones propias en el informe.')


def _map_data(data: dict) -> str:
    aggs = [[a["code"], nice_name(a["name"]), a["municipality"], round(a["lon"], 5), round(a["lat"], 5), a["pe"],
             GROUP[a["main_gap"]] if a["gaps"] else "", [GAPS[g] for g in a["gaps"]], [RECAST[g] for g in a["recast"]],
             [z["id"] for z in a["zones"]]] for a in data["aggs"] if a["lon"] is not None]
    zones = [[z["id"], nice_name(z["name"]), z["municipality"], round(z["lon"], 5), round(z["lat"], 5), z["quality"],
              ZONE_TYPE.get(z["type"], ""), list(z["history"].items()),
              [[u["code"], METHOD[u["method"]], u["km"]] for u in z["upstream"]]]
             for z in data["zones"] if z["lon"] is not None]
    blob = json.dumps({"aggs": aggs, "zones": zones}, ensure_ascii=False, separators=(",", ":"))
    return blob.replace("</", "<\\/")


def render(data: dict) -> Path:
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    rep, rel, f = data["report"], data["release"], data["figures"]
    aggs = {a["code"]: a for a in data["aggs"]}
    zones = {z["id"]: z for z in data["zones"]}
    flagged = [a for a in data["aggs"] if a["gaps"]]
    poor = sorted((z for z in data["zones"] if z["quality"] == "insuficiente"),
                  key=lambda z: (-sum(q == "insuficiente" for q in z["history"].values()), z["name"]))
    groups = {g: sum(GROUP[a["main_gap"]] == g for a in flagged) for g in GROUP_LABEL}
    ok_pct = 100 * (f["zones"] - f["poor"] - f["quality"]["sin_clasificar"]) / f["zones"]
    siblings = "\n".join(
        f'    <li{" aria-current=\"page\"" if slug == SLUG else ""}>'
        f'<a href="https://asensio94.github.io/{slug}/">{name}</a></li>' for slug, name in SIBLINGS)

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Depuración y baño</title>
<meta name="description" content="Las aglomeraciones urbanas que no depuran como pide la directiva europea, y las zonas de baño que quedan aguas abajo.">
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
  <p class="lede">¿A dónde va lo que tiras? Las ciudades y pueblos que, según lo que España informa a Europa, no
  recogen o no depuran sus aguas residuales como pide la directiva, y las zonas de baño que quedan aguas abajo.</p>
  <div class="figures">
    <div><b>{fmt(f["flagged"])}</b><span>aglomeraciones con alguna carencia, de {fmt(f["assessed"])} (informe de {rep["year"]})</span></div>
    <div><b>{fmt(f["flagged_pe"] / 1e6, 2)}</b><span>millones de habitantes-equivalentes en ellas</span></div>
    <div><b>{fmt(f["poor"])}</b><span>zonas de baño insuficientes en {rel["season"]}, de {fmt(f["zones"])}</span></div>
    <div><b>{fmt(f["poor_with_upstream"])}</b><span>de ellas con un vertido urbano aguas arriba ({fmt(f["poor_with_flagged_upstream"])} de una aglomeración con carencias)</span></div>
  </div>
</header>
<main>
  <p class="intro">La <a href="{DIRECTIVE}">Directiva 91/271/CEE</a> obliga desde hace más de treinta años a recoger y
  depurar las aguas residuales de cada aglomeración urbana de más de 2.000 habitantes-equivalentes (h-e). España llega
  tarde: el Tribunal de Justicia de la UE la condenó en 2018 a pagar una multa por las depuradoras que seguía sin
  construir (<a href="{JUDGMENT}">asunto C-205/17</a>). Esta página aplica las reglas de la directiva a lo que España
  declara en su último informe, situado a {long_date(rep["situation"])}, y sigue cada vertido río abajo hasta las zonas
  de baño. Es un indicio, no un veredicto: la Comisión tiene en cuenta plazos, excepciones e información que el informe no trae.</p>

  <div class="tools" role="group" aria-label="Capas del mapa">
    <button type="button" data-layer="flagged" aria-pressed="true">Aglomeraciones con carencias</button>
    <button type="button" data-layer="ok" aria-pressed="false">Aglomeraciones sin carencias</button>
    <button type="button" data-layer="zones" aria-pressed="true">Zonas de baño</button>
  </div>
  <div class="tools" role="group" aria-label="Ir a">
    <button type="button" data-view="40.2,-3.6,6">Península y Baleares</button>
    <button type="button" data-view="28.4,-15.9,8">Canarias</button>
  </div>
  <div id="map" role="region" aria-label="Mapa de aglomeraciones y zonas de baño"></div>
  <div class="legend">
    {"".join(f'<span><span class="dot" style="background:var(--g-{g})"></span>{GROUP_LABEL[g]} ({fmt(groups[g])})</span>' for g in GROUP_LABEL)}
    <span><span class="dot" style="background:var(--g-ok)"></span>Sin carencias</span>
  </div>
  <div class="legend">
    {"".join(f'<span><span class="sq" style="background:var(--q-{q})"></span>{QUALITY[q]} ({fmt(f["quality"][q])})</span>' for q in QUALITY)}
  </div>
  <p class="legend">Círculos: aglomeraciones, de tamaño según su carga. Rombos: zonas de baño, por su clasificación en {rel["season"]}.
  Al pulsar una, se dibujan sus enlaces aguas arriba o aguas abajo.</p>

  <h2 class="block" id="aglomeraciones">Aglomeraciones con carencias</h2>
  <p class="block">Ordenadas por carga. «Plan» es el año en que España prevé terminar las obras (programa del artículo 17),
  cuando lo declara. «Aguas abajo», las zonas de baño enlazadas con sus vertidos.</p>
  <div class="tools" role="group" aria-label="Filtrar por carencia">
    <button type="button" data-group="" aria-pressed="true">Todas ({fmt(len(flagged))})</button>
{chr(10).join(f'    <button type="button" data-group="{g}" aria-pressed="false">{GROUP_LABEL[g]} ({fmt(groups[g])})</button>' for g in GROUP_LABEL)}
  </div>
  <div class="wrap"><table class="list" id="agg-table">
    <thead><tr><th>Aglomeración</th><th class="num">Carga<br>h-e</th><th>Qué le falta</th><th class="num">Plan</th><th class="num">Aguas<br>abajo</th></tr></thead>
    <tbody>
{chr(10).join(_agg_row(a, zones) for a in flagged)}
    </tbody>
  </table></div>

  <h2 class="block" id="zonas">Zonas de baño insuficientes en {rel["season"]}</h2>
  <p class="block">Las {fmt(len(poor))} zonas con la peor clasificación, primero las que llevan más temporadas así.
  Cuadros: clasificación de {", ".join(list(poor[0]["history"])[:-1]) if poor else ""} y {list(poor[0]["history"])[-1] if poor else ""}.
  A la derecha, las aglomeraciones cuyos vertidos llegan hasta ellas.</p>
  <div class="wrap"><table class="list">
    <thead><tr><th>Zona de baño</th><th>Temporadas</th><th>Vertidos urbanos aguas arriba</th></tr></thead>
    <tbody>
{chr(10).join(_zone_row(z, aggs) for z in poor)}
    </tbody>
  </table></div>

  <section class="method">
    <h2>Cómo se calcula</h2>
    <ol>
      <li><b>Lo que España declara.</b> Cada dos años España envía a la Agencia Europea de Medio Ambiente (AEMA) el
      estado de sus aglomeraciones urbanas: la carga que generan en habitantes-equivalentes, qué parte llega al
      colector, qué parte se trata en sistemas individuales, qué parte se vierte sin tratar, qué depuradoras la reciben,
      qué tratamiento tienen, si sus controles cumplen y dónde vierten. El último informe es el de {rep["year"]}, con datos
      a {long_date(rep["situation"])}, entregado el {long_date(rep["version"])}.</li>
      <li><b>Las reglas de la directiva.</b> A cada aglomeración se le aplican los artículos 3, 4 y 5 de la Directiva
      91/271/CEE. <i>Colector</i>: al menos el {fmt(c.MIN_COLLECTED_PCT)} % de la carga debe ir al colector o a un sistema
      individual adecuado, y no más del {fmt(c.MAX_UNTREATED_PCT)} % puede verterse sin tratar. <i>Tratamiento
      secundario</i> (biológico): obligatorio desde {fmt(c.SECONDARY_FRESH_PE)} h-e si vierte a ríos, lagos o estuarios, y
      desde {fmt(c.SECONDARY_COASTAL_PE)} h-e si vierte al mar. <i>Tratamiento más riguroso</i> (eliminar nitrógeno o
      fósforo): obligatorio desde {fmt(c.STRINGENT_PE)} h-e si vierte en una zona sensible a la eutrofización. Si la
      depuradora tiene el tratamiento pero sus controles no cumplen, la carencia es de <i>rendimiento</i>.</li>
      <li><b>Lo que viene.</b> La <a href="{RECAST_URL}">refundición de 2024</a> (Directiva 2024/3019) exigirá a las
      depuradoras de más de {fmt(c.RECAST_LARGE_PE)} h-e eliminar nitrógeno y fósforo en 2039 y un tratamiento cuaternario
      contra microcontaminantes en 2045. Se muestran aparte, con borde discontinuo: hoy no son una carencia.</li>
      <li><b>Las zonas de baño.</b> Cada año la AEMA publica la clasificación de todas las zonas de baño según la
      Directiva 2006/7/CE: excelente, buena, suficiente o insuficiente, a partir de los análisis de <i>E. coli</i> y
      enterococos de las últimas cuatro temporadas. Aquí se usa la de {rel["season"]}, publicada el {long_date(rel["published"])}.</li>
      <li><b>El camino del agua.</b> Cada punto de vertido se une a las zonas de baño de tres maneras. <i>Río abajo</i>:
      el vertido y la zona están a menos de {fmt(c.RIVER_SNAP_KM)} km de un tramo de la red de ríos HydroRIVERS, y siguiendo
      la red desde el vertido se llega a la zona en menos de {fmt(c.RIVER_DOWNSTREAM_KM)} km. <i>Por la desembocadura</i>:
      el río llega al mar en menos de {fmt(c.RIVER_DOWNSTREAM_KM)} km y la zona de costa o de transición está a menos de
      {fmt(c.SAME_BODY_KM)} km de la desembocadura. <i>Misma masa de agua</i>: en la costa, estuarios y embalses, donde no
      hay río abajo, el vertido y la zona declaran la misma masa de agua y están a menos de {fmt(c.SAME_BODY_KM)} km.</li>
    </ol>
    <table class="params">
      <tr><th>Parámetro</th><th class="num">Valor</th></tr>
      <tr><td>Carga mínima recogida (colector + sistemas individuales)</td><td class="num">{fmt(c.MIN_COLLECTED_PCT)} %</td></tr>
      <tr><td>Carga máxima vertida sin tratar</td><td class="num">{fmt(c.MAX_UNTREATED_PCT)} %</td></tr>
      <tr><td>Secundario: aguas continentales y estuarios</td><td class="num">{fmt(c.SECONDARY_FRESH_PE)} h-e</td></tr>
      <tr><td>Secundario: aguas costeras</td><td class="num">{fmt(c.SECONDARY_COASTAL_PE)} h-e</td></tr>
      <tr><td>Más riguroso: zonas sensibles</td><td class="num">{fmt(c.STRINGENT_PE)} h-e</td></tr>
      <tr><td>Refundición de 2024: grandes depuradoras</td><td class="num">{fmt(c.RECAST_LARGE_PE)} h-e</td></tr>
      <tr><td>Distancia máxima de un punto a la red de ríos</td><td class="num">{fmt(c.RIVER_SNAP_KM)} km</td></tr>
      <tr><td>Recorrido máximo río abajo</td><td class="num">{fmt(c.RIVER_DOWNSTREAM_KM)} km</td></tr>
      <tr><td>Distancia máxima en costa, estuario o embalse</td><td class="num">{fmt(c.SAME_BODY_KM)} km</td></tr>
    </table>
    <h3>Contraste</h3>
    <ul>
      <li>Las {fmt(f["zones"])} zonas de baño y su reparto por clases coinciden con la publicación de la AEMA de {rel["season"]}:
      el {fmt(ok_pct, 1)} % llega al menos a «suficiente».</li>
      <li id="c205">{_c205(aggs)}</li>
      <li>De las {fmt(f["poor"])} zonas insuficientes, {fmt(f["poor"] - f["poor_with_upstream"])} no tienen ningún vertido de
      aglomeración enlazado: la mayoría son ríos de interior sin ninguna aglomeración del informe aguas arriba. La carga
      vendrá de pueblos de menos de 2.000 h-e, que el informe no incluye, o de la ganadería y la escorrentía.</li>
    </ul>
    <h3>Límites</h3>
    <ul>
      <li>Es un indicio, no un veredicto. La Comisión evalúa el cumplimiento con plazos, excepciones y aclaraciones
      que no están en el informe, y su evaluación no se publica como datos abiertos.</li>
      <li>El informe solo incluye aglomeraciones de 2.000 h-e o más. Los pueblos pequeños, que también deben tener un
      «tratamiento adecuado», no aparecen.</li>
      <li>El informe tiene dos años de retraso: una depuradora terminada después de {long_date(rep["situation"])} sigue
      apareciendo con su carencia hasta el informe siguiente.</li>
      <li>Para el tratamiento cuaternario se usa como aproximación la ozonización declarada: el informe aún no tiene un campo propio.</li>
      <li>HydroRIVERS es una red de ríos global a unos 500 m de resolución. Algunos puntos caen en el tramo vecino y
      los arroyos pequeños no están; un enlace puede faltar o sobrar. En la costa la distancia es en línea recta, sin corrientes.</li>
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
<script>
const DATA = {_map_data(data)};
const QUALITY = {json.dumps(QUALITY, ensure_ascii=False)};
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = n => n.toLocaleString('es-ES');
const map = L.map('map', {{preferCanvas: true}}).setView([40.2, -3.6], 6);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom: 18, attribution: '© OpenStreetMap'}}).addTo(map);
const layers = {{flagged: L.layerGroup().addTo(map), ok: L.layerGroup(), zones: L.layerGroup().addTo(map)}};
const lines = L.layerGroup().addTo(map), svg = L.svg({{padding: 1}}), LINK = '#173a75';
const aggBy = {{}}, zoneBy = {{}};
const esc = s => String(s).replace(/[&<>"]/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}})[ch]);

for (const a of DATA.aggs) {{
  const [code, name, muni, lon, lat, pe, group, gaps, recast, zs] = a;
  const m = L.circleMarker([lat, lon], {{radius: Math.max(3, Math.min(22, Math.sqrt(pe) / 40)),
    color: '#fff', weight: 1, fillColor: css(group ? '--g-' + group : '--g-ok'), fillOpacity: group ? .85 : .55}});
  m.bindPopup(() => `<h4>${{esc(name)}}</h4><div class="sub">${{esc(muni)}} · ${{code}}</div>
    <div>${{fmt(pe)}} h-e</div>
    <div>${{gaps.length ? '<b>Le falta:</b> ' + gaps.map(esc).join(', ') : 'Sin carencias según el informe'}}</div>
    ${{recast.length ? '<div class="sub">Refundición: ' + recast.map(esc).join(', ') + '</div>' : ''}}
    <div class="sub">${{zs.length}} zona(s) de baño aguas abajo</div>
    ${{group ? `<div><a href="#${{code}}">Ver en la tabla</a></div>` : ''}}`);
  a.targets = () => zs.map(z => zoneBy[z]).filter(Boolean).map(z => [z[4], z[3]]);
  m.on('click', () => draw([lat, lon], a.targets()));
  (group ? layers.flagged : layers.ok).addLayer(m);
  aggBy[code] = a; a.marker = m;
}}
const SIZE = {{insuficiente: 15, suficiente: 12, buena: 8, excelente: 7, sin_clasificar: 7}};
const RANK = {{insuficiente: 400, suficiente: 300, buena: 100, excelente: 0, sin_clasificar: 0}};
const diamond = (lat, lon, q) => L.marker([lat, lon], {{zIndexOffset: RANK[q], keyboard: false, icon: L.divIcon({{className: '',
  html: `<span class="sq" style="background:${{css('--q-' + q)}};border:1px solid #fff;width:${{SIZE[q]}}px;height:${{SIZE[q]}}px;opacity:${{RANK[q] ? 1 : .75}}"></span>`,
  iconSize: [SIZE[q], SIZE[q]]}})}});
for (const z of DATA.zones) {{
  const [id, name, muni, lon, lat, q, type, hist, ups] = z;
  zoneBy[id] = z;
}}
for (const z of DATA.zones) {{
  const [id, name, muni, lon, lat, q, type, hist, ups] = z;
  const m = diamond(lat, lon, q);
  m.bindPopup(() => `<h4>${{esc(name)}}</h4><div class="sub">${{esc(muni)}} · ${{type}}</div>
    <div>${{hist.map(([s, v]) => s + ': ' + QUALITY[v]).join(' · ')}}</div>
    ${{ups.length ? '<div><b>Aguas arriba:</b></div>' + ups.map(([c, how, km]) => {{
      const a = aggBy[c]; return a ? `<div>${{esc(a[1])}} <span class="sub">${{fmt(a[5])}} h-e · ${{how}}, ${{km.toLocaleString('es-ES')}} km${{a[6] ? ' · con carencias' : ''}}</span></div>` : '';
    }}).join('') : '<div class="sub">Ningún vertido de aglomeración enlazado</div>'}}`);
  z.targets = () => ups.map(([c]) => aggBy[c]).filter(Boolean).map(a => [a[4], a[3]]);
  m.on('click', () => draw([lat, lon], z.targets()));
  layers.zones.addLayer(m); z.marker = m;
}}
function draw(from, tos) {{
  lines.clearLayers();
  for (const to of tos) {{
    L.polyline([from, to], {{renderer: svg, color: LINK, weight: 2.5, dashArray: '5 4', interactive: false}}).addTo(lines);
    L.circleMarker(to, {{renderer: svg, radius: 6, color: LINK, weight: 2.5, fill: false, interactive: false}}).addTo(lines);
  }}
}}
map.on('popupclose', () => lines.clearLayers());

document.querySelectorAll('[data-layer]').forEach(b => b.addEventListener('click', () => {{
  const on = b.getAttribute('aria-pressed') !== 'true';
  b.setAttribute('aria-pressed', on);
  on ? layers[b.dataset.layer].addTo(map) : map.removeLayer(layers[b.dataset.layer]);
}}));
document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => {{
  const [lat, lon, z] = b.dataset.view.split(',').map(Number); map.setView([lat, lon], z);
}}));
document.querySelectorAll('[data-group]').forEach(b => b.addEventListener('click', () => {{
  b.parentElement.querySelectorAll('button').forEach(o => o.setAttribute('aria-pressed', o === b));
  document.querySelectorAll('#agg-table tbody tr').forEach(tr => tr.hidden = b.dataset.group && tr.dataset.group !== b.dataset.group);
}}));
document.addEventListener('click', e => {{
  const a = e.target.closest('a[data-agg],a[data-zone]');
  if (!a) return;
  const item = a.dataset.agg ? aggBy[a.dataset.agg] : zoneBy[a.dataset.zone];
  if (!item) return;
  setTimeout(() => {{
    map.fitBounds(L.latLngBounds([[item[4], item[3]], ...item.targets()]).pad(0.3), {{maxZoom: 12}});
    item.marker.fire('click');
  }}, 50);
}});
</script>
</body>
</html>
"""
    out = c.DOCS_DIR / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
