"""France: the official compliance verdict of each treatment plant (portail de l'assainissement collectif).

The Ministry of Ecological Transition publishes, every year, one row per plant (STEU) with the
verdict of the State services on its agglomeration: equipment, performance, collection and the
overall verdict, plus why it fails, its discharge point and the receiving water. It is the French
reading of the directive, one year more recent than what France reports to the EEA.

Only agglomerations of 2,000 p.e. or more (those the directive covers) and only the columns the
page uses: never the owner (maître d'ouvrage), the operator or their addresses.
"""
from __future__ import annotations

import csv
import io
import re

import requests

from ..config import ERU_DOWNLOAD_PAGE, ERU_EXPORT, data_dir
from ..store import read_json, read_rows, write_json, write_rows

DIR = data_dir("FR") / "eru"
UA = {"User-Agent": "depuracion-y-bano (github.com/Asensio94/depuracion-y-bano)"}

# The three bands of the directive; the two smaller ones ([0;200[ and [200;2000[) stay out.
BANDS = {"[ 2 000 ; 10 000 [ EH": "2000", "[ 10 000 ; 100 000 [ E": "10000", "[ 100 000 ; ... [ EH": "100000"}
VERDICT = {"Oui": "yes", "Non": "no", "Inc": "unknown", "Enc": "ongoing", "N/A": "na"}
MEDIUM = {"Eau douce de surface": "FW", "Eau côtière": "CW", "Marin": "CW", "Estuaire (dont étang salé)": "ES",
          "Sol": "soil", "Rejet diffus": "diffuse"}

# kept field -> source column (first column with that header: the export repeats some of them)
AGG = {"agg": "Code SANDRE de l'agglomération", "agg_name": "Nom de l'agglomération",
       "commune": "Nom de la commune principale", "insee": "Code INSEE commune principale",
       "dept": "Numéro département", "basin": "Libellé du bassin", "region": "Nom de la région"}
VERDICTS = {"agg_equipment": "Conformité  agglo equipement réglementaire",
            "agg_performance": "Conformité agglo perf réglementaire",
            "agg_collection": "Conformité collecte réglementaire agglo",
            "agg_global": "Conformité agglo globale réglementaire",
            "equipment": "Conformité réglementaire équipement STEU",
            "perf_bod": "Conformité réglementaire STEU perf DBO", "perf_cod": "Conformité réglementaire STEU perf DCO",
            "perf_n": "Conformité réglementaire STEU perf NGL", "perf_p": "Conformité réglementaire STEU perf PT",
            "performance": "Conformité globale STEU réglementaire performances",
            "rain": "Conformité réglementaire temps pluie (TP) du SCL",
            "sensitive_n": "Sensibilité azote", "sensitive_p": "Sensibilité phosphore"}
TEXT = {"code": "Code du STEU", "name": "Nom du STEU", "cause": "Cause de non conformité",
        "dry_weather": "Existence de rejets par temps sec",
        "required_bio": "Niveau traitement requis ERU : biologique",
        "required_n": "Niveau traitement requis ERU : azote", "required_p": "Niveau traitement requis ERU : phosphore",
        "existing_bio": "Niveau traitement existant : biologique", "existing_n": "Niveau traitement existant : azote",
        "existing_p": "Niveau traitement existant : phosphore",
        "existing_disinfection": "Niveau traitement existant : désinfection",
        "water_body": "Code de masse eau", "sensitive_area": "Code ZS"}
NUMBERS = {"agg_pe": "Taille agglomération (EH)", "capacity": "Capacité nominale en EH",
           "load": "Charge maximale entrante (EH)", "dry_weather_pct": "Pourcentage rejet direct temps sec",
           "lat": "Latitude du STEU (WGS84)", "lon": "Longitude du STEU (WGS84)",
           "dcp_lat": "Latitude du rejet (WGS84)", "dcp_lon": "Longitude du rejet (WGS84)"}


def latest_year() -> int:
    """The most recent year offered by the download form."""
    html = requests.get(ERU_DOWNLOAD_PAGE, headers=UA, timeout=60).text
    select = re.search(r'<select[^>]*id="annee".*?</select>', html, re.S)
    years = [int(y) for y in re.findall(r'<option value="(\d{4})"', select.group(0) if select else html)]
    if not years:
        raise RuntimeError("no year in the ERU download form")
    return max(years)


def _download(year: int) -> str:
    form = {"bassin": "ALL", "region": "ALL", "departement": "ALL", "annee": str(year), "format": "csv",
            "tranche": "ALL", "confEquip": "ALL", "confPerf": "ALL"}
    r = requests.post(ERU_EXPORT, files={k: (None, v) for k, v in form.items()}, headers=UA, timeout=600)
    r.raise_for_status()
    return r.content.decode("utf-8-sig")


def _number(v: str):
    v = (v or "").strip().replace(",", ".")
    try:
        x = float(v)
    except ValueError:
        return None
    return int(x) if x.is_integer() and "." not in v else x


def parse(text: str) -> list[dict]:
    rows = csv.reader(io.StringIO(text, newline=""), delimiter="|")
    head = [h.strip().strip('"') for h in next(rows)]
    idx = {h: i for i, h in reversed(list(enumerate(head)))}
    out = []
    for r in rows:
        if len(r) != len(head):
            raise ValueError(f"ERU export: a row with {len(r)} fields instead of {len(head)}")
        get = lambda col: r[idx[col]].strip()
        band = BANDS.get(get("Tranche obligation"))
        if band is None:
            continue
        x = {k: get(col) or None for k, col in {**AGG, **TEXT}.items()}
        x.update({k: VERDICT.get(get(col), get(col) or None) for k, col in VERDICTS.items()})
        x.update({k: _number(get(col)) for k, col in NUMBERS.items()})
        x["band"] = band
        x["medium"] = MEDIUM.get(get("Type du milieu du rejet"), get("Type du milieu du rejet") or None)
        x["in_service"] = get(next(h for h in head if h.startswith("Etat du STEU"))) == "En service"
        x["updated"] = get("Date de mise à jour agglo") or None
        out.append(x)
    out.sort(key=lambda x: (x["agg"], x["code"] or ""))
    return out


def fetch(year: int | None = None) -> int:
    year = year or latest_year()
    rows = parse(_download(year))
    write_rows(DIR / "steu.json", rows)
    write_json(DIR / "release.json", {"year": year, "plants": len(rows),
                                      "agglomerations": len({r["agg"] for r in rows}),
                                      "updated": max(r["updated"] for r in rows if r["updated"])})
    return len(rows)


def release() -> dict | None:
    return read_json(DIR / "release.json")


def plants() -> list[dict]:
    return read_rows(DIR / "steu.json")
