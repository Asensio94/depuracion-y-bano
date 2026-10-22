"""Which bathing waters lie downstream of each discharge point.

Three ways, from the most to the least precise:

- river: the discharge and the bathing water sit on the HydroRIVERS network and the bathing water is
  downstream, at most RIVER_DOWNSTREAM_KM along the river;
- mouth: the river reaches the sea within that distance and a coastal or transitional bathing
  water lies within SAME_BODY_KM of the river mouth;
- water_body: discharge and bathing water share the water body code both report to the EEA and
  lie within SAME_BODY_KM of each other (coast, estuaries and lakes, where there is no "downstream").
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np
import pyogrio
import requests
import shapely
from shapely import STRtree
from shapely.geometry import Point

from . import config as c

KM_Y = 110.57                                 # km per degree of latitude


def km_x(lat: float) -> float:
    """km per degree of longitude around a latitude."""
    return 111.32 * math.cos(math.radians(lat))


KM_X = km_x(c.KM_LATITUDE["ES"])              # around 40° N, the middle of Spain
RIVER_TYPES = {"riverBathingWater", "lakeBathingWater"}
SEA_TYPES = {"coastalBathingWater", "transitionalBathingWater"}


def to_km(lon: float, lat: float) -> tuple[float, float]:
    """A flat plane in km around 40° N. Across Spain it is off by under 10 %, which only moves the thresholds a little."""
    return lon * KM_X, lat * KM_Y


def norm_body(code: str | None) -> str | None:
    """Water body codes are written with and without dashes; compare them on letters and digits."""
    return re.sub(r"[^A-Z0-9]", "", code.upper()) if code else None


@dataclass
class Link:
    discharge: str
    zone: str
    method: str          # river | mouth | water_body
    km: float            # along the river (river, mouth) or straight line (water_body)


class Network:
    """HydroRIVERS reaches: geometry in km, downstream neighbour and length."""

    def __init__(self, ids, next_down, length_km, lines, kx: float = KM_X):
        self.kx = kx
        self.next = {int(i): int(n) for i, n in zip(ids, next_down)}
        self.length = {int(i): float(v) for i, v in zip(ids, length_km)}
        self.ids = [int(i) for i in ids]
        self.lines = lines
        self.tree = STRtree(lines)

    def to_km(self, lon: float, lat: float) -> tuple[float, float]:
        return lon * self.kx, lat * KM_Y

    @classmethod
    def load(cls, country: str = "ES") -> "Network":
        path = c.CACHE_DIR / "hydrorivers_eu.zip"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(c.HYDRORIVERS_URL, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        src = f"/vsizip/{path.as_posix()}/HydroRIVERS_v10_eu_shp/HydroRIVERS_v10_eu.shp"
        _, _, wkb, (ids, nxt, length) = pyogrio.raw.read(
            src, bbox=c.RIVER_BBOX[country], columns=["HYRIV_ID", "NEXT_DOWN", "LENGTH_KM"])
        kx = km_x(c.KM_LATITUDE[country])
        lines = shapely.transform(shapely.from_wkb(wkb), lambda xy: xy * np.array([kx, KM_Y]))
        return cls(ids, nxt, length, list(lines), kx)

    def snap(self, lon: float, lat: float) -> tuple[int, float] | None:
        """(reach id, km from the start of the reach) of the closest reach, if close enough."""
        p = Point(*self.to_km(lon, lat))
        hit = self.tree.query_nearest(p, max_distance=c.RIVER_SNAP_KM)
        if not len(hit):
            return None
        k = int(hit[0])
        line = self.lines[k]
        frac = line.project(p) / line.length if line.length else 0.0
        rid = self.ids[k]
        return rid, frac * self.length[rid]

    def downstream(self, rid: int, at_km: float, limit: float):
        """(reach id, km from the discharge to the start of that reach) down to `limit`, then the mouth.

        Yields ("reach", rid, offset) for each reach and finally ("mouth", rid, km) if the river ends
        within the limit. The first offset is negative: the discharge sits partway along its reach.
        """
        offset = -at_km
        seen = set()
        while rid in self.length and rid not in seen and offset <= limit:   # leaves the box: stop
            seen.add(rid)
            yield "reach", rid, offset
            end = offset + self.length[rid]
            nxt = self.next.get(rid, 0)
            if nxt == 0:
                if end <= limit:
                    yield "mouth", rid, end
                return
            rid, offset = nxt, end

    def mouth_point(self, rid: int) -> tuple[float, float]:
        x, y = self.lines[self.ids.index(rid)].coords[-1]
        return x, y


def build(discharges: list[dict], zones: list[dict], net: Network) -> list[Link]:
    """Links between active discharge points and the bathing waters listed in `zones`.

    `zones` items: id, type, water_body, lon, lat.
    """
    links: dict[tuple[str, str], Link] = {}

    def keep(l: Link):
        old = links.get((l.discharge, l.zone))
        rank = {"river": 0, "mouth": 1, "water_body": 2}
        if old is None or (rank[l.method], l.km) < (rank[old.method], old.km):
            links[(l.discharge, l.zone)] = l

    on_reach: dict[int, list[tuple[dict, float]]] = {}
    for z in zones:
        if z["type"] in RIVER_TYPES and z["lon"] is not None:
            s = net.snap(z["lon"], z["lat"])
            if s:
                on_reach.setdefault(s[0], []).append((z, s[1]))
    sea = [z for z in zones if z["type"] in SEA_TYPES and z["lon"] is not None]
    sea_xy = STRtree([Point(*net.to_km(z["lon"], z["lat"])) for z in sea]) if sea else None
    by_body: dict[str, list[dict]] = {}
    for z in zones:
        b = norm_body(z.get("water_body"))
        if b and z["lon"] is not None:
            by_body.setdefault(b, []).append(z)

    for d in discharges:
        if d["dcpState"] not in (True, 1, "1", "true") or d["dcpLatitude"] is None:
            continue
        lon, lat = float(d["dcpLongitude"]), float(d["dcpLatitude"])
        if d["dcpWaterBodyType"] == "FW":
            s = net.snap(lon, lat)
            if s:
                for kind, rid, km in net.downstream(s[0], s[1], c.RIVER_DOWNSTREAM_KM):
                    if kind == "reach":
                        for z, at in on_reach.get(rid, []):
                            dist = km + at
                            if 0 <= dist <= c.RIVER_DOWNSTREAM_KM:
                                keep(Link(d["dcpCode"], z["id"], "river", round(dist, 1)))
                    elif sea_xy is not None:
                        mouth = Point(*net.mouth_point(rid))
                        for i in sea_xy.query(mouth, predicate="dwithin", distance=c.SAME_BODY_KM):
                            keep(Link(d["dcpCode"], sea[int(i)]["id"], "mouth", round(km, 1)))
        b = norm_body(d["dcpWaterbodyID"])
        if b:
            here = Point(*net.to_km(lon, lat))
            for z in by_body.get(b, []):
                if z["type"] == "riverBathingWater":
                    continue                                   # direction matters on a river
                dist = here.distance(Point(*net.to_km(z["lon"], z["lat"])))
                if dist <= c.SAME_BODY_KM:
                    keep(Link(d["dcpCode"], z["id"], "water_body", round(dist, 1)))
    return sorted(links.values(), key=lambda l: (l.discharge, l.zone))
