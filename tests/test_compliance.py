from wastewater.compliance import assess

AGG = {"aggCode": "ES1", "aggGenerated": 20000, "aggC1": 100.0, "aggC2": 0.0, "aggPercWithoutTreatment": 0.0}
PLANT = {"uwwCode": "P1", "uwwSecondaryTreatment": True, "uwwNRemoval": True, "uwwPRemoval": True,
         "uwwOzonation": False, "uwwBOD5Perf": "P", "uwwCODPerf": "P", "uwwNTotPerf": "P", "uwwPTotPerf": "P"}
RIVER = {"dcpWaterBodyType": "FW", "dcpTypeOfReceivingArea": "NA"}
SENSITIVE = {"dcpWaterBodyType": "FW", "dcpTypeOfReceivingArea": "A523"}
SEA = {"dcpWaterBodyType": "CW", "dcpTypeOfReceivingArea": "NA"}


def test_compliant():
    assert assess(AGG, [PLANT], [RIVER]).compliant


def test_collection_counts_individual_systems():
    assert assess({**AGG, "aggC1": 90.0, "aggC2": 9.0}, [PLANT], [RIVER]).compliant
    assert assess({**AGG, "aggC1": 90.0, "aggC2": 5.0}, [PLANT], [RIVER]).gaps == ["collection"]


def test_secondary_threshold_depends_on_receiving_water():
    small = {**AGG, "aggGenerated": 5000}
    primary = {**PLANT, "uwwSecondaryTreatment": False}
    assert assess(small, [primary], [RIVER]).main_gap == "secondary"
    assert assess(small, [primary], [SEA]).compliant


def test_stringent_only_in_sensitive_areas():
    plain = {**PLANT, "uwwNRemoval": False, "uwwPRemoval": False}
    assert assess(AGG, [plain], [RIVER]).compliant
    assert assess(AGG, [plain], [SENSITIVE]).gaps == ["stringent"]


def test_performance_failures():
    a = assess(AGG, [{**PLANT, "uwwBOD5Perf": "F", "uwwPTotPerf": "F"}], [SENSITIVE])
    assert a.gaps == ["secondary_performance", "stringent_performance"]
    assert a.main_gap == "secondary_performance"


def test_recast_is_not_a_gap():
    a = assess({**AGG, "aggGenerated": 200000}, [{**PLANT, "uwwPRemoval": False}], [RIVER])
    assert a.compliant and a.recast == ["recast_np", "recast_quaternary"]
