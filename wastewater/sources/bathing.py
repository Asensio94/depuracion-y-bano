"""Bathing waters (Directive 2006/7/EC) as reported to the EEA.

Two pieces: the yearly classification of every bathing water ("Status of bathing water", an
Excel file the EEA publishes each June), and the register of bathing waters with the water body
each one belongs to (Discodata). The EEA catalogue says which classification release is the latest.
"""
from __future__ import annotations

import io
import re
import zipfile

import openpyxl
import requests

from ..config import BATHING_SEASONS_KEPT, BATHING_TITLE, BWD_DB, DATA_DIR, EEA_CATALOGUE, EEA_DATA
from ..store import read_json, read_rows, write_json, write_rows
from .discodata import query

DIR = DATA_DIR / "bathing"

# EEA class -> the Spanish name the Ministry of Health uses for it.
QUALITY = {"1": "excelente", "2": "buena", "3": "suficiente", "4": "insuficiente", "0": "sin_clasificar"}


def latest_release() -> dict:
    """The newest "Status of bathing water, YYYY" record in the EEA catalogue."""
    body = {"size": 20, "_source": ["resourceTitleObject.default", "uuid", "publicationDateForResource"],
            "query": {"match_phrase": {"resourceTitleObject.default": BATHING_TITLE}}}
    r = requests.post(EEA_CATALOGUE, json=body, headers={"Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    best = None
    for h in r.json()["hits"]["hits"]:
        src = h["_source"]
        m = re.search(r"Status of bathing water, (\d{4}) v\.?(\d+)\.(\d+)", src["resourceTitleObject"]["default"])
        if not m:
            continue
        key = tuple(int(x) for x in m.groups())
        if best is None or key > best[0]:
            best = (key, {"uuid": src["uuid"], "season": key[0], "version": f"{key[1]}.{key[2]}",
                          "published": (src.get("publicationDateForResource") or [None])[0]})
    if best is None:
        raise RuntimeError("No bathing water release found in the EEA catalogue")
    return best[1]


def _download(uuid: str) -> bytes:
    """The data link opens a share page; its "download" link serves the zip."""
    page = requests.get(EEA_DATA.format(uuid=uuid), timeout=60)
    page.raise_for_status()
    m = re.search(r'href="(https://sdi\.eea\.europa\.eu/datashare/s/[^"/]+/download)"', page.text)
    if not m:
        raise RuntimeError(f"No download link for {uuid}")
    r = requests.get(m.group(1), timeout=600)
    r.raise_for_status()
    return r.content


def fetch_status(release: dict) -> int:
    """Spanish rows of the last seasons, from the Excel inside the release zip."""
    z = zipfile.ZipFile(io.BytesIO(_download(release["uuid"])))
    name = next(n for n in z.namelist() if n.endswith(".xlsx"))
    ws = openpyxl.load_workbook(io.BytesIO(z.read(name)), read_only=True).worksheets[0]
    rows = ws.iter_rows(values_only=True)
    head = {h: i for i, h in enumerate(next(rows))}
    first = release["season"] - BATHING_SEASONS_KEPT + 1
    out = []
    for r in rows:
        if r[head["countryCode"]] != "ES" or not r[head["season"]] or r[head["season"]] < first:
            continue
        out.append({"id": r[head["bathingWaterIdentifier"]], "season": int(r[head["season"]]),
                    "quality": QUALITY.get(str(r[head["quality"]] or "0")[0], "sin_clasificar"),
                    "name": (r[head["bathingWaterName"]] or "").strip(), "type": r[head["bathingWaterType"]],
                    "lon": r[head["lon"]], "lat": r[head["lat"]]})
    out.sort(key=lambda x: (x["id"], x["season"]))
    write_rows(DIR / "status.json", out)
    write_json(DIR / "release.json", release)
    return len(out)


def fetch_zones() -> int:
    """Each bathing water with its water body: the latest record of the register for every identifier."""
    rows = query(f"SELECT thematicIdIdentifier, nameText, specialisedZoneType, relatedZoneIdentifier, "
                 f"relatedZoneIdentifierScheme, lon, lat, cYear FROM {BWD_DB}.[spatial_ProtectedArea] "
                 f"WHERE countryCode='ES'")
    rows.sort(key=lambda r: (r["thematicIdIdentifier"], r["cYear"] or 0))
    latest: dict[str, dict] = {}
    for r in rows:                                  # ordered by year: the last one wins
        latest[r["thematicIdIdentifier"]] = r
    out = [{"id": k, "name": (r["nameText"] or "").strip(), "type": r["specialisedZoneType"],
            "water_body": r["relatedZoneIdentifier"] if r["relatedZoneIdentifierScheme"] == "euSurfaceWaterBodyCode" else None,
            "lon": float(r["lon"]) if r["lon"] is not None else None,
            "lat": float(r["lat"]) if r["lat"] is not None else None, "year": r["cYear"]}
           for k, r in sorted(latest.items())]
    write_rows(DIR / "zones.json", out)
    return len(out)


def release() -> dict | None:
    return read_json(DIR / "release.json")


def status() -> list[dict]:
    return read_rows(DIR / "status.json")


def zones() -> list[dict]:
    return read_rows(DIR / "zones.json")
