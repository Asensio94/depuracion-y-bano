"""EEA Discodata: a read-only SQL endpoint over the datasets the countries report to the EEA."""
from __future__ import annotations

import requests

from ..config import DISCODATA

PAGE = 20000


def query(sql: str, timeout: int = 180) -> list[dict]:
    """Every row of a query in one page.

    Paging would need ORDER BY, which the endpoint refuses for some columns; a full page means the
    result was cut, so it fails rather than return part of a table. Callers sort the rows themselves.
    """
    r = requests.get(DISCODATA, params={"query": sql, "p": 1, "nrOfHits": PAGE}, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(f"Discodata: {body['errors']} for {sql}")
    rows = body.get("results", [])
    if len(rows) >= PAGE:
        raise RuntimeError(f"Discodata returned a full page ({PAGE} rows): raise PAGE for {sql}")
    return rows
