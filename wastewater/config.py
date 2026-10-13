"""Paths, endpoints and the parameters of every rule, in one place (the page prints them)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
CACHE_DIR = ROOT / ".cache"            # large inputs re-downloaded on demand, never committed

PAGES = "https://asensio94.github.io/depuracion-y-bano/"
REPO = "https://github.com/Asensio94/depuracion-y-bano"

# EEA Discodata: read-only SQL over the reported datasets.
DISCODATA = "https://discodata.eea.europa.eu/sql"
UWWTD_DB = "[WISE_UWWTD].[latest]"
BWD_DB = "[WISE_BWD].[latest]"
# EEA geospatial catalogue: tells which "Status of bathing water" release is the latest.
EEA_CATALOGUE = "https://sdi.eea.europa.eu/catalogue/srv/api/search/records/_search"
EEA_DATA = "https://sdi.eea.europa.eu/data/{uuid}"
BATHING_TITLE = "Bathing Water Directive - Status of bathing water"
BATHING_SEASONS_KEPT = 4               # the classification itself already looks back four seasons

# HydroRIVERS v1.0, Europe: river reaches with their downstream neighbour.
HYDRORIVERS_URL = "https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_eu_shp.zip"
SPAIN_BBOX = (-10.0, 35.0, 4.6, 44.0)  # mainland and Balearics; the Canaries have no river bathing waters

# IGN municipalities with INE codes, packaged as TopoJSON by es-atlas (~200 m), as in estado-iba.
MUNICIPALITIES_URL = "https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/municipalities.json"
MUNICIPALITY_SNAP_DEG = 0.05           # beaches lie on the coastline the simplified polygons cut off

# --- Directive 91/271/EEC thresholds (population equivalent, p.e.) ---
MIN_COLLECTED_PCT = 98.0               # collected + individual systems (IAS) below this: collecting gap
MAX_UNTREATED_PCT = 2.0                # collected but discharged untreated above this: treatment gap
SECONDARY_FRESH_PE = 2_000             # Art. 4: fresh water and estuaries
SECONDARY_COASTAL_PE = 10_000          # Art. 4: coastal waters
STRINGENT_PE = 10_000                  # Art. 5: sensitive areas and their catchments
# --- Recast, Directive (EU) 2024/3019 ---
RECAST_LARGE_PE = 150_000              # N and P removal by 2039, quaternary treatment by 2045

# --- Linking a discharge with bathing waters downstream ---
RIVER_SNAP_KM = 2.0                    # a point counts on a reach this close to it
RIVER_DOWNSTREAM_KM = 30.0             # how far downstream a discharge is followed
SAME_BODY_KM = 5.0                     # coast, estuary or lake: same water body and this close; also around a river mouth

# --- Validation: judgment C-205/17 (CJEU, 25 July 2018) ---
# Pending in September 2022 according to the Ministry (periodic penalty still running).
C205_PENDING_2022 = {"ES1110070001010": "Barbate", "ES1210050005010": "Matalascañas",
                     "ES1290080001010": "Alhaurín el Grande", "ES5380200130835": "Valle de Güímar (Güímar Sur)"}
# Already compliant by then (judgment, para. 47, and the same note); found in the report under these codes.
C205_RESOLVED = {"ES1110350018010": "Tarifa", "ES1290750003030": "Nerja", "ES3330242402010": "Gijón-Este",
                 "ES1290510006010": "Estepona (San Pedro de Alcántara)", "ES5380230130522": "Noreste (Valle Guerra)",
                 "ES10120270001010": "Benicarló", "ES10120890001010": "Peñíscola", "ES12360571403010": "Vigo",
                 "ES12150782911010": "Santiago de Compostela"}
