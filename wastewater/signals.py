"""docs/signals.json for estado-iba (CONTRATO.md, version 2: one coverage per country).

Two kinds: `wastewater`, one per agglomeration that misses some requirement of the directive, and
`bathing_water`, one per bathing water rated "insuficiente" in the latest season. Points and
municipality codes only (INE in Spain, INSEE in France): agglomerations and bathing waters are
public facilities, no person is named. Each signal says its country; its title is in that
country's language and its link goes to that country's page.

In Spain an agglomeration is flagged by the rule of the directive applied to the report to the
EEA; in France, by the official verdict of the State services (conformité globale « Non »).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .compliance import GAPS, RECAST
from .config import DOCS_DIR, PAGES, PAGES_FR
from .i18n import n, t
from .places import nice_name

QUALITY_LABEL = {"excelente": "excelente", "buena": "buena", "suficiente": "suficiente",
                 "insuficiente": "insuficiente", "sin_clasificar": "sin clasificar"}


def _fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def wastewater(a: dict, report: dict) -> dict:
    return {
        "id": a["code"],
        "country": "ES",
        "kind": "wastewater",
        "date": report["version"],
        "title": f"{nice_name(a['name'])}: {GAPS[a['main_gap']].lower()} ({_fmt(a['pe'])} h-e)",
        "url": f"{PAGES}#{a['code']}",
        "municipalities": [a["ine"]] if a["ine"] else [],
        "precision": "punto",
        "status": "indicio",
        "value": {"amount": a["pe"], "unit": "h-e"},
        "details": {
            "point": [a["lon"], a["lat"]],
            "carencias": [GAPS[g] for g in a["gaps"]],
            "refundicion_2024": [RECAST[g] for g in a["recast"]],
            "informe": report["year"], "situacion_a": report["situation"],
            "plan_fin_previsto": a["plan"]["date"] if a["plan"] else None,
            "zonas_bano_aguas_abajo": [z["id"] for z in a["zones"]],
        },
    }


def bathing_water(z: dict, release: dict) -> dict:
    return {
        "id": z["id"],
        "country": "ES",
        "kind": "bathing_water",
        "date": release["published"][:10],
        "title": f"Zona de baño {nice_name(z['name'])}: insuficiente en {release['season']}",
        "url": f"{PAGES}#{z['id']}",
        "municipalities": [z["ine"]] if z["ine"] else [],
        "precision": "punto",
        "status": "insuficiente",
        "value": {"amount": sum(q == "insuficiente" for q in z["history"].values()), "unit": "temporadas insuficientes"},
        "details": {
            "point": [z["lon"], z["lat"]],
            "temporada": release["season"],
            "historial": {s: QUALITY_LABEL[q] for s, q in z["history"].items()},
            "aglomeraciones_aguas_arriba": [u["code"] for u in z["upstream"]],
        },
    }


def wastewater_fr(a: dict, eru: dict) -> dict:
    fails = ", ".join(t("fr", f"fail_{f}") for f in a["fails"])
    return {
        "id": a["code"],
        "country": "FR",
        "kind": "wastewater",
        "date": eru["updated"],
        "title": f"{a['name']} : non conforme{f' ({fails})' if fails else ''}, {n(a['pe'], 'fr')} EH",
        "url": f"{PAGES_FR}#{a['code']}",
        "municipalities": [a["insee"]] if a["insee"] else [],
        "precision": "punto",
        "status": "non_conforme",
        "value": {"amount": a["pe"], "unit": "EH"},
        "details": {
            "point": [a["lon"], a["lat"]],
            "non_conformites": [t("fr", f"fail_{f}") for f in a["fails"]],
            "causes": a["causes"],
            "annee_eru": eru["year"],
            "lecture_aee_2022": [t("fr", f"gap_{g}") for g in a["eea"]["gaps"]] if a["eea"] else None,
            "baignades_en_aval": [z["id"] for z in a["zones"]],
        },
    }


def bathing_water_fr(z: dict, release: dict) -> dict:
    return {
        "id": z["id"],
        "country": "FR",
        "kind": "bathing_water",
        "date": release["published"][:10],
        "title": f"Baignade {nice_name(z['name'], 'fr')} : insuffisante en {release['season']}",
        "url": f"{PAGES_FR}#{z['id']}",
        "municipalities": [z["insee"]] if z["insee"] else [],
        "precision": "punto",
        "status": "insuffisante",
        "value": {"amount": sum(q == "insuficiente" for q in z["history"].values()), "unit": "saisons insuffisantes"},
        "details": {
            "point": [z["lon"], z["lat"]],
            "saison": release["season"],
            "historique": {s: t("fr", f"q_{q}") for s, q in z["history"].items()},
            "agglomerations_en_amont": [u["code"] for u in z["upstream"]],
            "interdictions_sanitaires": z["events"].get("health_ban", {}).get("count", 0),
        },
    }


def build(data: dict, fr: dict | None = None) -> dict:
    rep, rel = data["report"], data["release"]
    coverage = {
        "ES": {
            "label": "Toda España",
            "sites": None,
            "note": f"Aglomeraciones urbanas de más de 2.000 h-e del informe de {rep['year']} a la AEMA "
                    f"(Directiva 91/271/CEE), evaluadas con las reglas de la directiva; zonas de baño "
                    f"clasificadas en la temporada {rel['season']}.",
        },
    }
    out = ([wastewater(a, rep) for a in data["aggs"] if a["gaps"]]
           + [bathing_water(z, rel) for z in data["zones"] if z["quality"] == "insuficiente"])
    if fr:
        coverage["FR"] = {
            "label": "Toute la France",
            "sites": None,
            "note": f"Agglomérations d'assainissement de 2 000 EH ou plus, avec la conformité réglementaire "
                    f"{fr['eru']['year']} des services de l'État (portail de l'assainissement collectif, "
                    f"directive 91/271/CEE), métropole et outre-mer ; baignades classées en "
                    f"{fr['release']['season']}.",
        }
        out += ([wastewater_fr(a, fr["eru"]) for a in fr["aggs"] if a["verdict"] == "no"]
                + [bathing_water_fr(z, fr["release"]) for z in fr["zones"] if z["quality"] == "insuficiente"])
    return {
        "source": "depuracion-y-bano",
        "version": 2,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "coverage": coverage,
        "signals": out,
    }


def write(data: dict, fr: dict | None = None) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / "signals.json"
    path.write_text(json.dumps(build(data, fr), ensure_ascii=False, indent=1), encoding="utf-8")
    return path
