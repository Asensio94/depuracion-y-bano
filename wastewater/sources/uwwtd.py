"""Urban Waste Water Treatment Directive: what each country reports to the EEA (Waterbase UWWTD).

Five tables, all keyed by the codes the country assigns: agglomerations (aggCode), treatment plants
(uwwCode), the links between both, discharge points (dcpCode) and the Article 17 programme
(works planned for the agglomerations that do not comply yet). Spain and France, only what the
page uses; one JSON file per table and country, sorted by code so that a new report shows up as a clean diff.
"""
from __future__ import annotations

from ..config import UWWTD_DB, data_dir
from ..store import read_rows, write_rows
from .discodata import query

TABLES = {
    "report": ("T_ReportPeriod", "repReportedPeriod",
               "repReportedPeriod, repSituationAt, repVersion"),
    "agglomerations": ("T_Agglomerations", "aggCode",
                       "aggCode, aggName, aggState, aggGenerated, aggC1, aggC2, aggPercWithoutTreatment, "
                       "aggLatitude, aggLongitude, aggNUTS"),
    "plants": ("T_UWWTPs", "uwwCode",
               "uwwCode, uwwName, uwwState, uwwLoadEnteringUWWTP, uwwCapacity, uwwPrimaryTreatment, "
               "uwwSecondaryTreatment, uwwOtherTreatment, uwwNRemoval, uwwPRemoval, uwwUV, uwwChlorination, "
               "uwwOzonation, uwwSandFiltration, uwwMicroFiltration, uwwBOD5Perf, uwwCODPerf, uwwTSSPerf, "
               "uwwNTotPerf, uwwPTotPerf, uwwLatitude, uwwLongitude"),
    "plant_agglomerations": ("T_UWWTPAgglos", "aucUwwCode, aucAggCode",
                             "aucUwwCode, aucAggCode, aucPercEnteringUWWTP"),
    "discharges": ("T_DischargePoints", "dcpCode",
                   "dcpCode, uwwCode, dcpName, dcpState, dcpWaterBodyType, dcpTypeOfReceivingArea, rcaCode, "
                   "dcpWaterbodyID, dcpLatitude, dcpLongitude"),
    "programme": ("T_Art17_FLAAgglomeration", "aggCode",
                  "aggCode, flaggStatus, flaggReasons, flaggMeasures, flaggExpecDateCompletion, flaggInv"),
}


def _dir(country: str):
    return data_dir(country) / "uwwtd"


def fetch(country: str = "ES") -> dict[str, int]:
    counts = {}
    for name, (table, order, cols) in TABLES.items():
        rows = query(f"SELECT {cols} FROM {UWWTD_DB}.[{table}] WHERE CountryCode='{country}'")
        keys = [k.strip() for k in order.split(",")]
        rows.sort(key=lambda r: tuple(str(r[k]) for k in keys))
        for r in rows:
            for k, v in r.items():
                if isinstance(v, str):
                    r[k] = v.strip()
        write_rows(_dir(country) / f"{name}.json", rows)
        counts[name] = len(rows)
    return counts


def load(name: str, country: str = "ES") -> list[dict]:
    return read_rows(_dir(country) / f"{name}.json")


def report(country: str = "ES") -> dict:
    """Which report is in use: the reported year, the situation date and when the country sent it."""
    r = max(load("report", country), key=lambda r: str(r["repReportedPeriod"]))
    return {"year": r["repReportedPeriod"], "situation": r["repSituationAt"][:10], "version": r["repVersion"][:10]}


def query_report(country: str = "ES") -> dict:
    """The report currently published, straight from Discodata (to decide whether to fetch again)."""
    r = max(query(f"SELECT {TABLES['report'][2]} FROM {UWWTD_DB}.[T_ReportPeriod] WHERE CountryCode='{country}'"),
            key=lambda r: str(r["repReportedPeriod"]))
    return {"year": r["repReportedPeriod"], "version": r["repVersion"][:10]}
