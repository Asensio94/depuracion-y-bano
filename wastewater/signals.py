"""docs/signals.json for estado-iba (CONTRATO.md).

Two kinds: `wastewater`, one per agglomeration that misses some requirement of the directive, and
`bathing_water`, one per bathing water rated "insuficiente" in the latest season. Points and INE codes
only: agglomerations and bathing waters are public facilities, no person is named.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .compliance import GAPS, RECAST
from .config import DOCS_DIR, PAGES
from .places import nice_name

QUALITY_LABEL = {"excelente": "excelente", "buena": "buena", "suficiente": "suficiente",
                 "insuficiente": "insuficiente", "sin_clasificar": "sin clasificar"}


def _fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def wastewater(a: dict, report: dict) -> dict:
    return {
        "id": a["code"],
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


def build(data: dict) -> dict:
    rep, rel = data["report"], data["release"]
    return {
        "source": "depuracion-y-bano",
        "version": 1,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "coverage": {
            "label": "Toda España",
            "sites": None,
            "note": f"Aglomeraciones urbanas de más de 2.000 h-e del informe de {rep['year']} a la AEMA "
                    f"(Directiva 91/271/CEE), evaluadas con las reglas de la directiva; zonas de baño "
                    f"clasificadas en la temporada {rel['season']}.",
        },
        "signals": [wastewater(a, rep) for a in data["aggs"] if a["gaps"]]
                   + [bathing_water(z, rel) for z in data["zones"] if z["quality"] == "insuficiente"],
    }


def write(data: dict) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / "signals.json"
    path.write_text(json.dumps(build(data), ensure_ascii=False, indent=1), encoding="utf-8")
    return path
