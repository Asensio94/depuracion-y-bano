from datetime import date

from wastewater import signals
from wastewater.analysis_fr import display_name
from wastewater.i18n import NNBSP, d, n, p
from wastewater.places import nice_name
from wastewater.sources import baignade_fr, eru_fr
from wastewater.web_fr import typo

NBSP = " "


def test_french_numbers():
    assert n(46709, "fr") == f"46{NNBSP}709" and n(46709, "es") == "46.709"
    assert d(1234.56, "fr") == f"1{NNBSP}234,6"
    assert p(0.15, "fr") == f"15{NNBSP}%"


def test_french_typography_in_prose():
    assert typo("Note : bien ; oui ? « mot »") == f"Note{NBSP}: bien{NNBSP}; oui{NNBSP}? «{NBSP}mot{NBSP}»"
    assert typo('<a href="x:y">a</a> 12:30') == '<a href="x:y">a</a> 12:30'      # only a spaced colon


def test_french_names():
    assert nice_name("PONT-L'ABBE", "fr") == "Pont-l'Abbe"
    assert nice_name("SAINT-MARTIN-DE-RE", "fr") == "Saint-Martin-de-Re"
    assert nice_name("CHALONS EN CHAMPAGNE", "fr") == "Chalons en Champagne"
    assert nice_name("SANTIAGO DE COMPOSTELA") == "Santiago de Compostela"                # Spanish untouched


def test_portal_names():
    assert display_name("ParisZONE CENTRALE", "Paris") == "Paris Zone Centrale"
    assert display_name("TOULOUSEZC", "Toulouse") == "Toulouse ZC"
    assert display_name("Lyon1", "Lyon") == "Lyon 1"
    assert display_name("EVRY-COURCOURONNES", "Évry-Courcouronnes") == "Évry-Courcouronnes"
    assert display_name("ORLEANSCHAPELLE-ST-MESMIN", "Orléans") == "Orléans Chapelle-St-Mesmin"
    assert display_name("MEYTHET", "MEYTHET") == "Meythet"
    assert display_name("Beauvoir-sur-Mer", "Saint-Gervais") == "Beauvoir-sur-Mer"


def _eru_csv(rows: list[dict]) -> str:
    cols = [*eru_fr.AGG.values(), *eru_fr.TEXT.values(), *eru_fr.VERDICTS.values(), *eru_fr.NUMBERS.values(),
            "Tranche obligation", "Type du milieu du rejet", "Etat du STEU (en service, ...)",
            "Date de mise à jour agglo", "Code du STEU"]                     # the export repeats some headers
    lines = ["|".join(cols)]
    for r in rows:
        lines.append("|".join(r.get(col, "") for col in cols[:-1]) + "|DUPLICATE")
    return "\n".join(lines) + "\n"


def test_eru_keeps_the_directive_bands_and_no_owner():
    base = {"Code SANDRE de l'agglomération": "060000169123", "Code du STEU": "060969123001",
            "Conformité agglo globale réglementaire": "Non", "Conformité agglo perf réglementaire": "Non",
            "Taille agglomération (EH)": "1637927", "Latitude du rejet (WGS84)": "45,78",
            "Type du milieu du rejet": "Eau douce de surface", "Etat du STEU (en service, ...)": "En service",
            "Date de mise à jour agglo": "2025-12-19", "Tranche obligation": "[ 100 000 ; ... [ EH"}
    small = {**base, "Code SANDRE de l'agglomération": "X", "Tranche obligation": "[ 200 ; 2 000 [ EH"}
    rows = eru_fr.parse(_eru_csv([base, small]))
    assert len(rows) == 1
    r = rows[0]
    assert r["code"] == "060969123001"                                       # first column with that header
    assert r["agg_global"] == "no" and r["agg_performance"] == "no" and r["agg_pe"] == 1637927
    assert r["dcp_lat"] == 45.78 and r["medium"] == "FW" and r["in_service"] and r["band"] == "100000"
    assert not any("ouvrage" in k or "exploitant" in k for k in r)


def test_closures_are_counted_within_the_season():
    site = "Code unique d'identification du site de baignade"
    listing = [{site: "S1", "Nom du site de baignade": "PLAGE", "Code INSEE de la commune": "2A004",
                "Longitude (ETRS 89)": "8,7", "Latitude (ETRS 89)": "41,9"}]
    chars = [{site: "S1", "Classement": "4"}]
    info = [{site: "S1", "Type d'événement": "Saison balnéaire", "Date de début": "15/06/2025", "Date de fin": "15/09/2025"},
            {site: "S1", "Type d'événement": "Interdiction sanitaire", "Date de début": "10/09/2025", "Date de fin": "31/12/9999",
             "Mesures": "texte libre"},
            {site: "S1", "Type d'événement": "Interdiction sanitaire", "Date de début": "01/07/2025", "Date de fin": "02/07/2025"}]
    sites, events = baignade_fr.build(2025, listing, chars, info)
    assert sites[0]["insee"] == "2A004" and sites[0]["quality"] == "insuficiente" and sites[0]["lon"] == 8.7
    assert events == [{"id": "S1", "kind": "health_ban", "count": 2, "days": 6 + 2}]
    assert baignade_fr._day("31/12/9999") == date(9999, 12, 31)


def _spain():
    return {"report": {"year": "2022", "situation": "2022-12-31", "version": "v"},
            "release": {"season": 2025, "published": "2026-06-02T00:00:00", "uuid": "u", "version": "1.0"},
            "aggs": [], "zones": []}


def test_french_signals():
    agg = {"code": "060000169123", "name": "Lyon 1", "insee": "69123", "lon": 4.72, "lat": 45.78, "pe": 1637927,
           "verdict": "no", "fails": ["performance", "collection"], "causes": ["Mauvaises performances"],
           "eea": {"gaps": [], "main_gap": None, "recast": []}, "zones": [{"id": "Z"}]}
    ok = {**agg, "code": "2", "verdict": "yes"}
    zone = {"id": "FRZ", "name": "PLAGE DU CENTRE", "insee": "2A004", "lon": 8.7, "lat": 41.9, "quality": "insuficiente",
            "history": {"2024": "suficiente", "2025": "insuficiente"}, "upstream": [], "events": {"health_ban": {"count": 3}}}
    fr = {"eru": {"year": 2024, "updated": "2025-12-19"}, "aggs": [agg, ok], "zones": [zone],
          "release": {"season": 2025, "published": "2026-06-02"}}
    out = signals.build(_spain(), fr)
    assert out["version"] == 2 and set(out["coverage"]) == {"ES", "FR"}
    w, b = out["signals"]
    assert w["country"] == b["country"] == "FR"
    assert w["title"] == f"Lyon 1 : non conforme (performance, collecte), 1{NNBSP}637{NNBSP}927 EH"
    assert w["url"].endswith("/fr/#060000169123") and w["municipalities"] == ["69123"]
    assert b["municipalities"] == ["2A004"] and b["title"] == "Baignade Plage du Centre : insuffisante en 2025"
    assert b["details"]["interdictions_sanitaires"] == 3
