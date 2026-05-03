"""Fetch and persist publication dates for OSM land and LSIB datasets."""

from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from duckdb import DuckDBPyConnection
from httpx import Client, Timeout

from app.config import LAND_OSM_URL, LSIB_META_URL, LSIB_NS


def _get_osm_land_date(client: Client) -> str:
    r = client.head(LAND_OSM_URL)
    r.raise_for_status()
    last_modified = r.headers.get("last-modified")
    if not last_modified:
        msg = "OSM land date not found in Last-Modified response header"
        raise ValueError(msg)
    return parsedate_to_datetime(last_modified).date().isoformat()


def _get_lsib_date(client: Client) -> str:
    r = client.get(LSIB_META_URL, headers={"Accept": "application/xml"})
    r.raise_for_status()
    root = ET.fromstring(r.text)  # noqa: S314
    el = root.find(".//gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:Date", LSIB_NS)
    if el is None or el.text is None:
        msg = "LSIB date not found in metadata response"
        raise ValueError(msg)
    return el.text


def main(conn: DuckDBPyConnection) -> None:
    """Fetch OSM land and LSIB publication dates and store in the dates table."""
    with Client(http2=True, timeout=Timeout(60, connect=30)) as client:
        osm_date = _get_osm_land_date(client)
        lsib_date = _get_lsib_date(client)
    conn.execute(f"""--sql
        CREATE OR REPLACE TABLE dates AS
        SELECT '{osm_date}'::DATE AS osm_date, '{lsib_date}'::DATE AS lsib_date
    """)
