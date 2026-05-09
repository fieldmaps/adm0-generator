"""Drop intermediate tables after each world-view export."""

from logging import getLogger

from duckdb import DuckDBPyConnection

from app.config import LAYERS_INTERMEDIATE, LAYERS_WORLD
from app.utils import discard

logger = getLogger(__name__)


def main(conn: DuckDBPyConnection, land: str, world: str) -> None:
    """Drop world-scoped intermediate tables and their parquet files."""
    for layer in LAYERS_WORLD:
        discard(conn, f"{land}_{layer}_{world}")
    logger.info("%s_%s", land, world)


def postprocessing_land(conn: DuckDBPyConnection, land: str) -> None:
    """Drop all intermediate tables for one land after its world views are done."""
    for layer in LAYERS_INTERMEDIATE:
        discard(conn, f"{land}_{layer}")
    logger.info("%s_postprocessing", land)
