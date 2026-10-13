"""Municipalities (INE codes): from the agglomeration code, or by locating a point on the IGN layer."""
from __future__ import annotations

import json
import re

import requests
from shapely import STRtree, make_valid
from shapely.geometry import Point, shape

from .config import CACHE_DIR, MUNICIPALITIES_URL, MUNICIPALITY_SNAP_DEG


def ine_from_agglomeration(code: str) -> str | None:
    """Spain builds its agglomeration codes on the INE code of the main municipality.

    ES + a regional prefix (one or two digits) + the 5-digit INE code + a 7-digit serial:
    ES1 0 03002 0001010 is Agost (03002), ES5 38017 0131038 is Granadilla de Abona (38017).
    """
    m = re.fullmatch(r"ES\d{1,2}(\d{5})\d{7}", code or "")
    return m.group(1) if m else None


def _decode(topo: dict, name: str) -> list[dict]:
    """TopoJSON polygons of one object as (INE, name, shapely geometry); same decoding as estado-iba."""
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(refs):
        pts = []
        for i in refs:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a[1:] if pts else a)
        return pts

    out = []
    for g in topo["objects"][name]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        rings = [[r for r in (ring(a) for a in p) if len(r) >= 4] for p in polys]
        rings = [p for p in rings if p]
        if rings:
            geom = make_valid(shape({"type": "MultiPolygon", "coordinates": rings}))
            out.append({"ine": g["id"], "name": (g.get("properties") or {}).get("name", ""), "geom": geom})
    return out


def municipalities() -> list[dict]:
    path = CACHE_DIR / "municipalities.json"
    if not path.exists():
        r = requests.get(MUNICIPALITIES_URL, timeout=120)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return _decode(json.loads(path.read_text(encoding="utf-8")), "municipalities")


class Locator:
    """(lon, lat) -> INE code: the municipality that contains the point, or the nearest one close by."""

    def __init__(self, munis: list[dict]):
        self.munis = munis
        self.names = {m["ine"]: m["name"] for m in munis}
        self.tree = STRtree([m["geom"] for m in munis])

    def __call__(self, lon: float | None, lat: float | None) -> str | None:
        if lon is None or lat is None:
            return None
        p = Point(lon, lat)
        inside = self.tree.query(p, predicate="intersects")
        if len(inside):
            return self.munis[inside[0]]["ine"]
        i = self.tree.query_nearest(p, max_distance=MUNICIPALITY_SNAP_DEG)
        return self.munis[i[0]]["ine"] if len(i) else None


SMALL = {"de", "del", "la", "las", "los", "el", "y", "e", "o", "en", "a"}


def _cap(w: str, first: bool) -> str:
    """One word: "l'hospitalet" -> "L'Hospitalet", "d'ebre" -> "d'Ebre" inside a name."""
    if "'" in w[:3]:
        pre, rest = w.split("'", 1)
        return (pre.capitalize() if first else pre) + "'" + rest[:1].upper() + rest[1:]
    return w[:1].upper() + w[1:]


def nice_name(s: str) -> str:
    """Names come in capitals: "SANTIAGO DE COMPOSTELA" -> "Santiago de Compostela"; codes such as "PM1" stay."""
    s = " ".join((s or "").split())
    if s != s.upper():
        return s                                   # already written in mixed case (IGN, some islands)
    words = []
    for i, w in enumerate((s or "").split()):
        low = w.lower()
        if any(ch.isdigit() for ch in w) or (i and re.fullmatch(r"[IVX]{2,4}", w)):   # PM1, PALMA II
            words.append(w)
        elif i and low in SMALL:
            words.append(low)
        else:
            words.append("-".join(_cap(p, i == 0) for p in low.split("-")))
    return " ".join(words)
