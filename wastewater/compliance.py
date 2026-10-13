"""What each agglomeration lacks under Directive 91/271/EEC, read from what Spain itself reports.

The Commission's own compliance assessment is not published as open data, so the rules of the
directive are applied here to the reported figures. The result is an indication, not a verdict:
the Commission also weighs deadlines, derogations and information that is not in the report.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import config as c

# Current gaps, from the most basic to the most demanding: the first one is "what it lacks".
GAPS = {
    "collection": "Colector",
    "untreated": "Vertido sin depurar",
    "no_plant": "Depuradora",
    "secondary": "Tratamiento secundario",
    "secondary_performance": "Rendimiento del secundario",
    "stringent": "Tratamiento más riguroso",
    "stringent_performance": "Rendimiento del más riguroso",
}
# What the 2024 recast will ask of the largest plants, with no gap today.
RECAST = {"recast_np": "Eliminar nitrógeno y fósforo (2039)", "recast_quaternary": "Tratamiento cuaternario (2045)"}

COASTAL = {"CW", "LC"}                       # coastal water, or land in a coastal catchment
SENSITIVE = {"SA", "A523", "A54", "A58", "CSA"}  # sensitive areas and their catchments (Art. 5)


@dataclass
class Assessment:
    code: str
    pe: int
    gaps: list[str] = field(default_factory=list)
    recast: list[str] = field(default_factory=list)
    plants: list[str] = field(default_factory=list)
    secondary_required: bool = False
    stringent_required: bool = False

    @property
    def compliant(self) -> bool:
        return not self.gaps

    @property
    def main_gap(self) -> str | None:
        return min(self.gaps, key=list(GAPS).index) if self.gaps else None


def _pct(v) -> float:
    return float(v or 0)


def assess(agg: dict, plants: list[dict], discharges: list[dict]) -> Assessment:
    """One agglomeration, with the active plants that treat its load and their discharge points."""
    pe = int(agg["aggGenerated"] or 0)
    a = Assessment(agg["aggCode"], pe, plants=[p["uwwCode"] for p in plants])
    if _pct(agg["aggC1"]) + _pct(agg["aggC2"]) < c.MIN_COLLECTED_PCT:
        a.gaps.append("collection")
    if _pct(agg["aggPercWithoutTreatment"]) > c.MAX_UNTREATED_PCT:
        a.gaps.append("untreated")
    if _pct(agg["aggC1"]) > 0 and not plants:
        a.gaps.append("no_plant")

    kinds = {d["dcpWaterBodyType"] for d in discharges if d["dcpWaterBodyType"]}
    a.secondary_required = pe >= c.SECONDARY_COASTAL_PE or (pe >= c.SECONDARY_FRESH_PE and bool(kinds - COASTAL))
    a.stringent_required = pe >= c.STRINGENT_PE and any(d["dcpTypeOfReceivingArea"] in SENSITIVE for d in discharges)

    if a.secondary_required:
        if any(not p["uwwSecondaryTreatment"] for p in plants):
            a.gaps.append("secondary")
        if any("F" in (p["uwwBOD5Perf"], p["uwwCODPerf"]) for p in plants):
            a.gaps.append("secondary_performance")
    if a.stringent_required:
        if any(not (p["uwwNRemoval"] or p["uwwPRemoval"]) for p in plants):
            a.gaps.append("stringent")
        if any("F" in (p["uwwNTotPerf"], p["uwwPTotPerf"]) for p in plants):
            a.gaps.append("stringent_performance")

    if pe >= c.RECAST_LARGE_PE and plants:
        if any(not (p["uwwNRemoval"] and p["uwwPRemoval"]) for p in plants):
            a.recast.append("recast_np")
        if any(not p["uwwOzonation"] for p in plants):
            a.recast.append("recast_quaternary")
    return a


def assess_all(aggs: list[dict], plants: list[dict], links: list[dict], discharges: list[dict]) -> dict[str, Assessment]:
    """Every active agglomeration. A plant counts for an agglomeration if it takes some of its load."""
    by_code = {p["uwwCode"]: p for p in plants if str(p["uwwState"]) == "1"}
    plants_of = defaultdict(list)
    for l in links:
        p = by_code.get(l["aucUwwCode"])
        if p and _pct(l["aucPercEnteringUWWTP"]) > 0:
            plants_of[l["aucAggCode"]].append(p)
    out_of = defaultdict(list)
    for d in discharges:
        if d["dcpState"] in (True, 1, "1", "true"):
            out_of[d["uwwCode"]].append(d)
    result = {}
    for agg in aggs:
        if str(agg["aggState"]) != "1":
            continue
        ps = plants_of[agg["aggCode"]]
        result[agg["aggCode"]] = assess(agg, ps, [d for p in ps for d in out_of[p["uwwCode"]]])
    return result
