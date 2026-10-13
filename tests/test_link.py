from shapely.geometry import LineString

from wastewater import config as c
from wastewater import link


def km_line(*pts):
    return LineString([link.to_km(*p) for p in pts])


def net():
    # 1 -> 2 -> 3 -> sea, each reach 0.1° of longitude (~8.5 km) along 40° N, flowing east.
    lines = [km_line((0.0, 40), (0.1, 40)), km_line((0.1, 40), (0.2, 40)), km_line((0.2, 40), (0.3, 40)),
             km_line((0.0, 40.5), (0.1, 40.5))]
    lengths = [l.length for l in lines]
    return link.Network([1, 2, 3, 9], [2, 3, 0, 0], lengths, lines)


def discharge(code, lon, lat, kind="FW", body=None):
    return {"dcpCode": code, "dcpState": True, "dcpLongitude": lon, "dcpLatitude": lat,
            "dcpWaterBodyType": kind, "dcpWaterbodyID": body}


def test_snap_and_walk():
    n = net()
    rid, at = n.snap(0.05, 40.001)
    assert rid == 1 and 4 < at < 5
    steps = list(n.downstream(rid, at, 100))
    assert [s[1] for s in steps if s[0] == "reach"] == [1, 2, 3]
    assert steps[-1][0] == "mouth"


def test_river_link_only_downstream():
    zones = [{"id": "down", "type": "riverBathingWater", "lon": 0.15, "lat": 40, "water_body": None},
             {"id": "up", "type": "riverBathingWater", "lon": 0.01, "lat": 40, "water_body": None},
             {"id": "other", "type": "riverBathingWater", "lon": 0.05, "lat": 40.5, "water_body": None}]
    links = link.build([discharge("D", 0.05, 40)], zones, net())
    assert [(l.zone, l.method) for l in links] == [("down", "river")]
    assert 8 < links[0].km < 9


def test_mouth_and_water_body():
    zones = [{"id": "beach", "type": "coastalBathingWater", "lon": 0.32, "lat": 40, "water_body": "ES-X1"},
             {"id": "near", "type": "coastalBathingWater", "lon": 0.53, "lat": 40, "water_body": "ESX1"},
             {"id": "far", "type": "coastalBathingWater", "lon": 0.6, "lat": 40, "water_body": "ESX1"},
             {"id": "elsewhere", "type": "coastalBathingWater", "lon": 0.51, "lat": 40, "water_body": "ESX2"}]
    links = link.build([discharge("D", 0.25, 40), discharge("S", 0.5, 40, "CW", "ES X 1")], zones, net())
    got = {(l.discharge, l.zone, l.method) for l in links}
    assert ("D", "beach", "mouth") in got
    assert ("S", "near", "water_body") in got           # same body once normalised, ~2.6 km
    assert not {z for _, z, _ in got} & {"far", "elsewhere"}   # ~8.5 km away; or another body
    assert all(l.km <= c.SAME_BODY_KM for l in links if l.method == "water_body")
