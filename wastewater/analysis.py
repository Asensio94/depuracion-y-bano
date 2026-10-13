"""Everything the page and the signals show, from the stored data: no network access here.

Agglomeration -> plants that take its load -> their discharge points -> bathing waters downstream
(data/links.json, written by `cli link`), and the other way round for each bathing water.
"""
from __future__ import annotations

import unicodedata
from collections import defaultdict

from . import compliance, link
from .config import DATA_DIR
from .places import Locator, ine_from_agglomeration, municipalities
from .sources import bathing, uwwtd
from .store import read_rows, write_rows

LINKS = DATA_DIR / "links.json"
QUALITY_ORDER = ["insuficiente", "suficiente", "buena", "excelente", "sin_clasificar"]


def _plain(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s.upper()) if unicodedata.category(ch) != "Mn")


def display_name(name: str, municipality: str) -> str:
    """The report writes names in capitals without accents; when it is the municipality, take the IGN spelling."""
    return municipality if municipality and _plain(municipality) == _plain(name) else name


def latest_zones() -> tuple[dict, list[dict]]:
    """The bathing waters classified in the latest season, with their register data and history."""
    rel = bathing.release()
    history = defaultdict(dict)
    rows = {}
    for r in bathing.status():
        history[r["id"]][r["season"]] = r["quality"]
        if r["season"] == rel["season"]:
            rows[r["id"]] = r
    register = {z["id"]: z for z in bathing.zones()}
    out = []
    for i, r in sorted(rows.items()):
        z = register.get(i, {})
        out.append({"id": i, "name": r["name"] or z.get("name", ""), "type": z.get("type") or r["type"],
                    "water_body": z.get("water_body"), "quality": r["quality"],
                    "lon": z.get("lon") if z.get("lon") is not None else r["lon"],
                    "lat": z.get("lat") if z.get("lat") is not None else r["lat"],
                    "history": {str(s): q for s, q in sorted(history[i].items())}})
    return rel, out


def build_links(net: link.Network | None = None) -> int:
    _, zones = latest_zones()
    links = link.build(uwwtd.load("discharges"), zones, net or link.Network.load())
    write_rows(LINKS, [l.__dict__ for l in links])
    return len(links)


def build() -> dict:
    rep, (rel, zones) = uwwtd.report(), latest_zones()
    aggs = {a["aggCode"]: a for a in uwwtd.load("agglomerations")}
    plants, plant_aggs = uwwtd.load("plants"), uwwtd.load("plant_agglomerations")
    discharges = uwwtd.load("discharges")
    result = compliance.assess_all(list(aggs.values()), plants, plant_aggs, discharges)
    programme = {p["aggCode"]: p for p in uwwtd.load("programme")}

    # discharge point -> agglomerations whose load reaches its plant
    aggs_of_plant = defaultdict(set)
    for l in plant_aggs:
        if float(l["aucPercEnteringUWWTP"] or 0) > 0 and l["aucAggCode"] in result:
            aggs_of_plant[l["aucUwwCode"]].add(l["aucAggCode"])
    aggs_of_discharge = {d["dcpCode"]: aggs_of_plant.get(d["uwwCode"], set()) for d in discharges}

    downstream = defaultdict(dict)      # agg -> zone -> (method, km)
    upstream = defaultdict(dict)        # zone -> agg -> (method, km)
    for l in read_rows(LINKS):
        for a in aggs_of_discharge.get(l["discharge"], ()):
            best = (l["method"] != "river", l["km"])
            if l["zone"] not in downstream[a] or best < downstream[a][l["zone"]][0]:
                downstream[a][l["zone"]] = (best, l["method"], l["km"])
                upstream[l["zone"]][a] = (best, l["method"], l["km"])

    locate = Locator(municipalities())
    names = locate.names
    agg_rows = []
    for code, r in result.items():
        a = aggs[code]
        ine = ine_from_agglomeration(code) or locate(a["aggLongitude"], a["aggLatitude"])
        p = programme.get(code)
        agg_rows.append({
            "code": code, "name": display_name(a["aggName"], names.get(ine, "")), "ine": ine, "municipality": names.get(ine, ""),
            "lon": a["aggLongitude"], "lat": a["aggLatitude"], "pe": r.pe,
            "gaps": r.gaps, "main_gap": r.main_gap, "recast": r.recast,
            "collected": a["aggC1"], "individual": a["aggC2"], "untreated": a["aggPercWithoutTreatment"],
            "plan": {"date": p["flaggExpecDateCompletion"], "status": p["flaggStatus"],
                     "investment": p["flaggInv"]} if p else None,
            "zones": [{"id": z, "method": m, "km": km} for z, (_, m, km) in sorted(downstream[code].items())],
        })
    agg_rows.sort(key=lambda x: (-x["pe"], x["code"]))

    for z in zones:
        z["ine"] = locate(z["lon"], z["lat"])
        z["municipality"] = names.get(z["ine"], "")
        z["upstream"] = [{"code": a, "method": m, "km": km}
                         for a, (_, m, km) in sorted(upstream[z["id"]].items(), key=lambda kv: kv[1][0])]

    flagged = [a for a in agg_rows if a["gaps"]]
    by_code = {a["code"]: a for a in agg_rows}
    poor = [z for z in zones if z["quality"] == "insuficiente"]
    return {
        "report": rep, "release": rel, "aggs": agg_rows, "zones": zones,
        "figures": {
            "assessed": len(agg_rows), "flagged": len(flagged), "flagged_pe": sum(a["pe"] for a in flagged),
            "total_pe": sum(a["pe"] for a in agg_rows), "zones": len(zones), "poor": len(poor),
            "poor_with_flagged_upstream": sum(any(by_code[u["code"]]["gaps"] for u in z["upstream"]) for z in poor),
            "poor_with_upstream": sum(bool(z["upstream"]) for z in poor),
            "quality": {q: sum(z["quality"] == q for z in zones) for q in QUALITY_ORDER},
            "gaps": {g: sum(a["main_gap"] == g for a in flagged) for g in compliance.GAPS},
            "recast": {g: sum(g in a["recast"] for a in agg_rows) for g in compliance.RECAST},
        },
    }
