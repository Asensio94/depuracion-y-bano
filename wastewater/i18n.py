"""Number formats and labels, one dictionary per language.

Each country's page is written in that country's language: the Spanish one in Spanish, the French
one in French. Data files (JSON, signals values) stay in canonical, language-independent values;
only what a reader sees goes through here. Same pattern as humedales/i18n.py in vigilancia-humedales.
"""
from __future__ import annotations

LANG_BY_COUNTRY = {"ES": "es", "FR": "fr"}

# French typography: a narrow no-break space as thousands separator and before «%».
NNBSP = " "


def lang_of(country: str) -> str:
    return LANG_BY_COUNTRY.get(country, "es")


def n(v: float, lang: str) -> str:
    """Integer with the thousands separator of the language: 46.709 / 46 709."""
    s = f"{v:,.0f}"
    return s.replace(",", "." if lang == "es" else NNBSP)


def d(v: float, lang: str, nd: int = 1) -> str:
    """Decimal with comma, in both languages: 2,7. Format the number, never the sentence."""
    s = f"{v:,.{nd}f}".replace(",", "_").replace(".", ",")
    return s.replace("_", "." if lang == "es" else NNBSP)


def p(x: float, lang: str) -> str:
    """A fraction as a percentage without decimals: 15 % / 15 %."""
    return f"{100 * x:.0f}{' ' if lang == 'es' else NNBSP}%"


UI: dict[str, dict[str, str]] = {
    "es": {
        "pe": "h-e",
        "q_excelente": "excelente", "q_buena": "buena", "q_suficiente": "suficiente",
        "q_insuficiente": "insuficiente", "q_sin_clasificar": "sin clasificar",
    },
    "fr": {
        "pe": "EH",
        "q_excelente": "excellente", "q_buena": "bonne", "q_suficiente": "suffisante",
        "q_insuficiente": "insuffisante", "q_sin_clasificar": "non classée",
        # what fails in the official verdict of the agglomeration
        "fail_equipment": "équipement", "fail_performance": "performance", "fail_collection": "collecte",
        # the second reading: the rule of the directive applied to the 2022 report to the EEA
        "gap_collection": "collecte insuffisante",
        "gap_untreated": "rejets sans traitement",
        "gap_no_plant": "sans station d'épuration",
        "gap_secondary": "traitement secondaire",
        "gap_secondary_performance": "performances du traitement secondaire",
        "gap_stringent": "traitement plus rigoureux (azote, phosphore)",
        "gap_stringent_performance": "performances du traitement plus rigoureux",
        "recast_np": "éliminer l'azote et le phosphore (2039)",
        "recast_quaternary": "traitement quaternaire (2045)",
        # closures of the bathing season, as the Ministry of Health names them
        "ev_health_ban": "interdiction sanitaire", "ev_cyanobacteria": "prolifération de cyanobactéries",
        "ev_short_term_pollution": "pollution à court terme", "ev_abnormal_situation": "situation anormale",
        "ev_other_ban": "interdiction non sanitaire", "ev_quality_change": "changement de qualité d'eau",
        "ev_removed": "site supprimé",
        # links between a discharge and a bathing water
        "m_river": "en aval sur la rivière", "m_mouth": "près de l'embouchure",
        "m_water_body": "même masse d'eau",
        "medium_FW": "eau douce", "medium_CW": "mer", "medium_ES": "estuaire", "medium_soil": "sol",
        "medium_diffuse": "rejet diffus",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """The string in that language, or the Spanish one, or the key itself."""
    s = UI.get(lang, {}).get(key) or UI["es"].get(key) or key
    return s.format(**kw) if kw else s
