"""France: bathing waters as the Ministry of Health reports them (data.gouv.fr, season after season).

Three files per season: the list of sites (commune and its INSEE code, coordinates), their
characteristics (the class of the season and the link to the bathing water profile) and the
information on the season (closures and their kind: health ban, cyanobacteria, short-term pollution...).
The class is the same the EEA publishes; the ministry adds the commune and the closures.

The closures come with free text (management measures, remarks) that is not kept: only how many
closures of each kind and how many days, per site.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date

import requests

from ..config import BAIGNADE_DATASET, data_dir
from ..store import read_json, read_rows, write_json, write_rows
from .bathing import QUALITY

DIR = data_dir("FR") / "baignade"
KINDS = {"liste": "list", "caracteristiques": "characteristics", "informations": "season"}
ID = "Code unique d'identification du site de baignade"
EVENTS = {"Interdiction sanitaire": "health_ban", "Prolifération de cyanobactéries": "cyanobacteria",
          "Pollution à court terme": "short_term_pollution", "Situation anormale": "abnormal_situation",
          "Interdiction non sanitaire": "other_ban", "Changement de qualité d'eau": "quality_change",
          "Site supprimé": "removed"}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s)


def resources() -> dict[int, dict[str, dict]]:
    """season -> kind -> resource, from titles that are not written the same way every year."""
    out: dict[int, dict[str, dict]] = {}
    for r in requests.get(BAIGNADE_DATASET, timeout=60).json()["resources"]:
        t = _plain(r["title"])
        season = re.search(r"saison balneaire (\d{4})", t)
        kind = next((v for k, v in KINDS.items() if k in t), None)
        if season and kind and r["format"] == "csv":
            out.setdefault(int(season.group(1)), {})[kind] = r
    return out


def latest_season(res: dict | None = None) -> int:
    """The latest season with its three files."""
    res = res if res is not None else resources()
    return max(s for s, k in res.items() if len(k) == len(KINDS))


def _csv(url: str) -> list[dict]:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    text = r.content.decode("latin-1")
    return [{k.strip(): (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(io.StringIO(text, newline=""), delimiter=";")]


def _day(s: str) -> date | None:
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    return date(int(m[3]), int(m[2]), int(m[1])) if m else None


def _coord(s: str) -> float | None:
    try:
        return round(float(s.replace(",", ".")), 6)
    except ValueError:
        return None


def build(season: int, listing: list[dict], characteristics: list[dict], info: list[dict]):
    sites: dict[str, dict] = {}
    for r in listing:
        sites[r[ID]] = {"id": r[ID], "name": r.get("Nom du site de baignade") or None,
                        "insee": r.get("Code INSEE de la commune") or None,
                        "commune": r.get("Nom de la commune") or None, "dept": r.get("Département") or None,
                        "region": r.get("Région") or None, "water": r.get("Type d'eau") or None,
                        "lon": _coord(r.get("Longitude (ETRS 89)", "")), "lat": _coord(r.get("Latitude (ETRS 89)", "")),
                        "quality": None, "profile": None}
    for r in characteristics:
        s = sites.setdefault(r[ID], {"id": r[ID], "name": None, "insee": None, "commune": None,
                                     "dept": r.get("Département") or None, "region": r.get("Région") or None,
                                     "water": None, "lon": None, "lat": None, "profile": None})
        s["quality"] = QUALITY.get((r.get("Classement") or "0")[:1], "sin_clasificar")
        s["profile"] = r.get("Lien URL vers le profil de baignade") or None

    # each site's own season: closures are counted within it ("31/12/9999" means "until further notice")
    year = (date(season, 1, 1), date(season, 12, 31))
    window = {}
    for r in info:
        if r.get("Type d'événement") == "Saison balnéaire":
            start, end = _day(r.get("Date de début", "")), _day(r.get("Date de fin", ""))
            if start and end and end >= start:
                window[r[ID]] = (max(start, year[0]), min(end, year[1]))
    events: dict[tuple[str, str], dict] = {}
    for r in info:
        kind = EVENTS.get(r.get("Type d'événement", ""))
        if kind is None:                                  # "Saison balnéaire": the dates of the season
            continue
        start, end = _day(r.get("Date de début", "")), _day(r.get("Date de fin", ""))
        e = events.setdefault((r[ID], kind), {"id": r[ID], "kind": kind, "count": 0, "days": 0})
        e["count"] += 1
        lo, hi = window.get(r[ID], year)
        if start and end:
            start, end = max(start, lo), min(end, hi)
            if end >= start:
                e["days"] += (end - start).days + 1
    return (sorted(sites.values(), key=lambda s: s["id"]),
            sorted(events.values(), key=lambda e: (e["id"], e["kind"])))


def fetch(season: int | None = None) -> dict[str, int]:
    res = resources()
    season = season or latest_season(res)
    files = res[season]
    sites, events = build(season, _csv(files["list"]["url"]), _csv(files["characteristics"]["url"]),
                          _csv(files["season"]["url"]))
    write_rows(DIR / "sites.json", sites)
    write_rows(DIR / "events.json", events)
    write_json(DIR / "release.json", {"season": season, "sites": len(sites),
                                      "updated": max(f["last_modified"][:10] for f in files.values())})
    return {"sites": len(sites), "events": len(events)}


def release() -> dict | None:
    return read_json(DIR / "release.json")


def sites() -> list[dict]:
    return read_rows(DIR / "sites.json")


def events() -> list[dict]:
    return read_rows(DIR / "events.json")
