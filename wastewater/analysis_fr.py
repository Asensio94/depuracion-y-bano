"""France: everything the French page and the French signals show, from the stored data.

Two readings of the same agglomerations:

- the official one, the verdict of the State services on each agglomeration of 2,000 p.e. or more
  (portail de l'assainissement collectif, ERU year 2024): equipment, performance and collection,
  with the cause they give when a plant fails. This is the one the page and the signals are built on;
- the reading of this project, the rule of the directive applied to what France reported to the
  EEA (2022, the same code as Spain's page): a second opinion, shown with how often both agree.

Bathing waters: the EEA classes (four seasons, as for Spain), the commune from the Ministry of
Health and the closures of the last season. Links between discharges and bathing waters: the
discharge points of the ERU year, with the same three methods as Spain (data/fr/links.json).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

from . import compliance, link
from .analysis import QUALITY_ORDER, latest_zones
from .config import FRANCE_BBOX, data_dir
from .places import nice_name
from .sources import baignade_fr, eru_fr, uwwtd
from .store import read_rows, write_rows

LINKS = data_dir("FR") / "links.json"
DIMENSIONS = {"equipment": "agg_equipment", "performance": "agg_performance", "collection": "agg_collection"}
CHECKS = {"bod": "perf_bod", "cod": "perf_cod", "n": "perf_n", "p": "perf_p"}
# Ministry water type -> EEA type, for the few sites the EEA does not list yet.
# An agglomeration declared this many times larger than the capacity of its plants is a typing error
# in the portal (Villefranche-sur-Saône, 2024: 14 million p.e. for 176,000 of capacity); its size is
# then taken from the report to the EEA, and the page says so. When the portal leaves the size empty,
# it comes from the report to the EEA too, or else from the capacity of the plants.
MAX_PE_OVER_CAPACITY = 20
WATER = {"Eau côtière": "coastalBathingWater", "Lac": "lakeBathingWater", "Rivière": "riverBathingWater",
         "Eau de transition": "transitionalBathingWater"}


def metropolitan(lon, lat) -> bool:
    """Mainland France and Corsica: the area of the river network. Overseas departments are outside."""
    w, s, e, n = FRANCE_BBOX
    return lon is not None and lat is not None and w <= lon <= e and s <= lat <= n


def discharges(plants: list[dict]) -> list[dict]:
    """ERU discharge points in the shape link.build expects (one per plant, as the portal gives them)."""
    return [{"dcpCode": p["code"], "dcpState": True, "dcpLatitude": p["dcp_lat"], "dcpLongitude": p["dcp_lon"],
             "dcpWaterBodyType": p["medium"] if p["medium"] in ("FW", "CW", "ES") else None,
             "dcpWaterbodyID": p["water_body"]}
            for p in plants if p["dcp_lat"] is not None and p["in_service"]]


def zones() -> tuple[dict, list[dict]]:
    """Bathing waters of the latest season: EEA class and history, plus the ministry's commune."""
    rel, out = latest_zones("FR")
    sites = {s["id"]: s for s in baignade_fr.sites()}
    known = {z["id"] for z in out}
    for s in sites.values():                      # listed by the ministry, not yet by the EEA
        if s["id"] not in known and s["quality"] and s["lon"] is not None:
            out.append({"id": s["id"], "name": s["name"] or "", "type": WATER.get(s["water"]), "water_body": None,
                        "quality": s["quality"], "profile": s["profile"], "lon": s["lon"], "lat": s["lat"],
                        "history": {str(baignade_fr.release()["season"]): s["quality"]}, "eea": False})
    for z in out:
        s = sites.get(z["id"], {})
        z["insee"], z["commune"], z["ministry_quality"] = s.get("insee"), s.get("commune"), s.get("quality")
        z.setdefault("eea", True)
    out.sort(key=lambda z: z["id"])
    return rel, out


def build_links(net: link.Network | None = None) -> int:
    _, zs = zones()
    links = link.build(discharges(eru_fr.plants()), zs, net or link.Network.load("FR"))
    write_rows(LINKS, [l.__dict__ for l in links])
    return len(links)


def _fold(ch: str) -> str:
    return unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode().lower()


def _split_commune(name: str, commune: str) -> tuple[str, str] | None:
    """If the name starts with the commune (accents, case and separators aside), the rest of the name."""
    want = [ch for ch in _fold(commune) if ch.isalnum()]
    commune = nice_name(commune, "fr") if commune.isupper() else commune
    i = 0
    for j, ch in enumerate(name):
        if not want[i:]:
            return commune, name[j:].strip(" -_/")
        f = _fold(ch)
        if f.isalnum():
            if f != want[i]:
                return None
            i += 1
    return (commune, "") if want and not want[i:] else None


def display_name(name: str, commune: str | None = None) -> str:
    """The portal mixes cases and glues words: "ParisZONE CENTRALE" -> "Paris Zone Centrale",
    "TOULOUSEZC" -> "Toulouse ZC", "Lyon1" -> "Lyon 1", "EVRY-COURCOURONNES" -> "Évry-Courcouronnes"."""
    name = " ".join((name or "").split())
    split = _split_commune(name, commune) if commune else None
    if split:
        head, rest = split
        return f"{head} {display_name(rest)}".strip() if rest else head
    name = re.sub(r"([a-zà-ÿ])([A-ZÀ-Ý]{2})", r"\1 \2", name)          # a commune glued to a name in capitals
    caps = r"[A-ZÀ-Ý][A-ZÀ-Ý0-9'\-]+(?: [A-ZÀ-Ý0-9'\-]+)*"
    return re.sub(caps, lambda m: nice_name(m.group(), "fr") if len(m.group()) > 3 else m.group(), name)


def second_reading() -> dict[str, compliance.Assessment]:
    """The rule of the directive on the 2022 report to the EEA, keyed by the SANDRE code (no "FR")."""
    aggs = uwwtd.load("agglomerations", "FR")
    result = compliance.assess_all(aggs, uwwtd.load("plants", "FR"), uwwtd.load("plant_agglomerations", "FR"),
                                   uwwtd.load("discharges", "FR"))
    return {code[2:]: r for code, r in result.items()}


def build() -> dict:
    rep, eru, bai = uwwtd.report("FR"), eru_fr.release(), baignade_fr.release()
    rel, zs = zones()
    plants = eru_fr.plants()
    eea = second_reading()
    eea_pe = {a["aggCode"][2:]: int(a["aggGenerated"] or 0) for a in uwwtd.load("agglomerations", "FR")}

    by_agg = defaultdict(list)
    for p in plants:
        by_agg[p["agg"]].append(p)

    downstream = defaultdict(dict)      # agg -> zone -> (rank, method, km)
    upstream = defaultdict(dict)        # zone -> agg -> (rank, method, km)
    agg_of_plant = {p["code"]: p["agg"] for p in plants}
    for l in read_rows(LINKS) if LINKS.exists() else []:
        a = agg_of_plant.get(l["discharge"])
        if a is None:
            continue
        best = (l["method"] != "river", l["km"])
        if l["zone"] not in downstream[a] or best < downstream[a][l["zone"]][0]:
            downstream[a][l["zone"]] = (best, l["method"], l["km"])
            upstream[l["zone"]][a] = (best, l["method"], l["km"])

    agg_rows = []
    for code, ps in by_agg.items():
        a = ps[0]
        second = eea.get(code)
        capacity = sum(p["capacity"] or 0 for p in ps)
        pe, pe_source = a["agg_pe"] or 0, "portal"
        if pe > MAX_PE_OVER_CAPACITY * capacity and eea_pe.get(code):
            pe, pe_source = eea_pe[code], "eea_fixed"
        elif not pe:                              # size left empty in the portal
            pe, pe_source = (eea_pe[code], "eea") if eea_pe.get(code) else (capacity, "capacity")
        pe_fixed = pe_source == "eea_fixed"
        agg_rows.append({
            "code": code, "name": display_name(a["agg_name"] or a["commune"] or code, a["commune"]),
            "commune": nice_name(a["commune"], "fr") if (a["commune"] or "").isupper() else a["commune"],
            "insee": a["insee"], "dept": a["dept"], "region": a["region"],
            "basin": a["basin"], "pe": pe, "pe_fixed": pe_fixed, "pe_source": pe_source, "band": a["band"],
            "lon": ps[0]["lon"], "lat": ps[0]["lat"], "metropolitan": metropolitan(ps[0]["lon"], ps[0]["lat"]),
            "verdict": a["agg_global"], "fails": [k for k, col in DIMENSIONS.items() if a[col] == "no"],
            "collection": a["agg_collection"], "dry_weather_pct": a["dry_weather_pct"],
            "causes": sorted({p["cause"] for p in ps if p["cause"]}),
            "plants": [{"code": p["code"], "name": display_name(p["name"] or ""), "capacity": p["capacity"],
                        "load": p["load"], "equipment": p["equipment"], "performance": p["performance"],
                        "failed": [k for k, col in CHECKS.items() if p[col] == "no"], "cause": p["cause"],
                        "medium": p["medium"], "sensitive": p["sensitive_n"] == "yes" or p["sensitive_p"] == "yes",
                        "required": [p["required_bio"], p["required_n"], p["required_p"]],
                        "existing": [p["existing_bio"], p["existing_n"], p["existing_p"], p["existing_disinfection"]]}
                       for p in ps],
            "eea": {"gaps": second.gaps, "main_gap": second.main_gap, "recast": second.recast} if second else None,
            "zones": [{"id": z, "method": m, "km": km} for z, (_, m, km) in sorted(downstream[code].items())],
        })
    agg_rows.sort(key=lambda x: (-x["pe"], x["code"]))
    by_code = {a["code"]: a for a in agg_rows}

    events = defaultdict(dict)
    for e in baignade_fr.events():
        events[e["id"]][e["kind"]] = {"count": e["count"], "days": e["days"]}
    for z in zs:
        z["events"] = events.get(z["id"], {})
        z["upstream"] = [{"code": a, "method": m, "km": km}
                         for a, (_, m, km) in sorted(upstream[z["id"]].items(), key=lambda kv: (kv[1][0], kv[0]))]

    bad = [a for a in agg_rows if a["verdict"] == "no"]
    poor = [z for z in zs if z["quality"] == "insuficiente"]
    both = [a for a in agg_rows if a["eea"] is not None]
    agree = Counter((a["verdict"] == "no", bool(a["eea"]["gaps"])) for a in both)
    closed = [z for z in zs if "health_ban" in z["events"]]
    return {
        "report": rep, "eru": eru, "baignade": bai, "release": rel, "aggs": agg_rows, "zones": zs,
        "figures": {
            "assessed": len(agg_rows), "noncompliant": len(bad), "noncompliant_pe": sum(a["pe"] for a in bad),
            "total_pe": sum(a["pe"] for a in agg_rows), "plants": len(plants),
            "overseas": sum(not a["metropolitan"] for a in agg_rows),
            "pe_fixed": [a["code"] for a in agg_rows if a["pe_fixed"]],
            "pe_missing": Counter(a["pe_source"] for a in agg_rows if a["pe_source"] in ("eea", "capacity")),
            "fails": {k: sum(k in a["fails"] for a in bad) for k in DIMENSIONS},
            "causes": Counter(c for a in bad for c in a["causes"]).most_common(),
            "collection_pending": sum(a["collection"] == "ongoing" for a in agg_rows),
            "agreement": {"both": agree[(True, True)], "official_only": agree[(True, False)],
                          "eea_only": agree[(False, True)], "neither": agree[(False, False)],
                          "missing": len(agg_rows) - len(both), "compared": len(both)},
            "eea_flagged": sum(bool(a["eea"]["gaps"]) for a in both),
            "zones": len(zs), "eea_zones": sum(z["eea"] for z in zs),
            "class_differ": [z["id"] for z in zs if z["eea"] and z["ministry_quality"] and z["ministry_quality"] != z["quality"]],
            "poor": len(poor), "quality": {q: sum(z["quality"] == q for z in zs) for q in QUALITY_ORDER},
            "poor_with_upstream": sum(bool(z["upstream"]) for z in poor),
            "poor_with_noncompliant_upstream": sum(any(by_code[u["code"]]["verdict"] == "no" for u in z["upstream"])
                                                    for z in poor),
            "zones_with_upstream": sum(bool(z["upstream"]) for z in zs),
            "health_ban_sites": len(closed),
            "health_ban_days": sum(z["events"]["health_ban"]["days"] for z in closed),
            "events": {k: sum(z["events"].get(k, {}).get("count", 0) for z in zs)
                       for k in ("health_ban", "cyanobacteria", "short_term_pollution", "abnormal_situation",
                                 "other_ban", "quality_change", "removed")},
        },
    }
