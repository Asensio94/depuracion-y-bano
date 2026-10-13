from wastewater import signals
from wastewater.places import ine_from_agglomeration, nice_name

REQUIRED = {"id", "kind", "date", "title", "url", "precision"}
PRECISIONS = {"parcelas", "municipio", "perimetro", "focos", "punto", "lamina", "pixeles", "radar"}


def test_ine_from_agglomeration():
    assert ine_from_agglomeration("ES10030020001010") == "03002"
    assert ine_from_agglomeration("ES5380170131038") == "38017"
    assert ine_from_agglomeration("ESX") is None


def test_nice_name():
    assert nice_name("SANTIAGO DE COMPOSTELA") == "Santiago de Compostela"
    assert nice_name("RIO TAMBRE TRAZO PM1") == "Rio Tambre Trazo PM1"
    assert nice_name("PALMA II") == "Palma II"
    assert nice_name("L'HOSPITALET DE LLOBREGAT") == "L'Hospitalet de Llobregat"


def test_signals_follow_the_contract():
    data = {
        "report": {"year": "2022", "situation": "2022-12-31", "version": "2024-06-30"},
        "release": {"season": 2025, "published": "2026-06-02T00:00:00", "uuid": "u", "version": "1.0"},
        "aggs": [{"code": "ES1290080001010", "name": "ALHAURIN EL GRANDE", "ine": "29008", "lon": -4.68, "lat": 36.64,
                  "pe": 21956, "gaps": ["secondary"], "main_gap": "secondary", "recast": [], "plan": None, "zones": []},
                 {"code": "ES2", "name": "OK", "ine": "1", "lon": 0, "lat": 0, "pe": 1, "gaps": [], "main_gap": None,
                  "recast": [], "plan": None, "zones": []}],
        "zones": [{"id": "Z", "name": "PLAYA", "ine": "15069", "lon": -8.1, "lat": 43.4, "quality": "insuficiente",
                   "history": {"2024": "suficiente", "2025": "insuficiente"}, "upstream": [{"code": "ES1290080001010"}]},
                  {"id": "Y", "name": "OTRA", "ine": None, "lon": 0, "lat": 0, "quality": "excelente",
                   "history": {"2025": "excelente"}, "upstream": []}],
    }
    out = signals.build(data)
    assert [s["kind"] for s in out["signals"]] == ["wastewater", "bathing_water"]
    for s in out["signals"]:
        assert REQUIRED <= s.keys() and s["precision"] in PRECISIONS
        assert len(s["date"]) == 10 and s["url"].endswith("#" + s["id"])
        assert all(len(m) == 5 for m in s["municipalities"])
        assert len(s["details"]["point"]) == 2
    assert out["signals"][0]["title"] == "Alhaurin el Grande: tratamiento secundario (21.956 h-e)"
