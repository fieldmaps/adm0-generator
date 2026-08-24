"""Shared utilities and DuckDB connection setup."""

import contextlib
import re
import threading
import time
from collections.abc import Iterator
from logging import FileHandler, Formatter, getLogger
from pathlib import Path
from shutil import make_archive
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

import psutil
from duckdb import DuckDBPyConnection, connect

from .config import ALL_LANDS, PARQUET_OPTS, debug, download_dir, tmp_dir

_PROCESS = psutil.Process()
logger = getLogger(__name__)

_PARQUET_PLAIN = "(COMPRESSION ZSTD)"
_MEM_Q = "SELECT COALESCE(SUM(memory_usage_bytes), 0) FROM duckdb_memory()"


def _query_label(query: str) -> str:
    q = " ".join(query.split())
    m = re.search(r'CREATE (?:OR REPLACE )?TABLE "([^"]+)"', q, re.IGNORECASE)
    if m:
        return f"CREATE {m.group(1)}"
    m = re.search(r'DROP TABLE (?:IF EXISTS )?"([^"]+)"', q, re.IGNORECASE)
    if m:
        return f"DROP {m.group(1)}"
    m = re.search(r'ALTER TABLE "[^"]+" RENAME TO "([^"]+)"', q, re.IGNORECASE)
    if m:
        return f"RENAME TO {m.group(1)}"
    m = re.search(r"COPY .+? TO '([^']+)'", q, re.IGNORECASE)
    if m:
        return f"COPY {m.group(1)}"
    m = re.search(r'INSERT INTO "([^"]+)"', q, re.IGNORECASE)
    if m:
        return f"INSERT {m.group(1)}"
    return q[:80]


class _EagerResult:
    """Materialized DuckDB result that survives subsequent execute() calls."""

    def __init__(self, rows: list) -> None:
        self._rows = rows
        self._idx = 0

    def fetchall(self) -> list:
        return self._rows

    def fetchone(self) -> tuple | None:
        if self._idx < len(self._rows):
            row = self._rows[self._idx]
            self._idx += 1
            return row
        return None


class _Batch:
    """Accumulator for consecutive execute() calls that share the same label."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.count = 0
        self.total_time = 0.0
        self.max_rss = 0
        self.duckdb_delta = 0.0
        self.duckdb_total = 0.0

    def add(self, elapsed: float, rss: int, delta: float, total: float) -> None:
        """Fold one execute()'s stats into this batch."""
        self.count += 1
        self.total_time += elapsed
        self.max_rss = max(self.max_rss, rss)
        self.duckdb_delta += delta
        self.duckdb_total = total


class ProfiledConnection:
    """Proxy around DuckDBPyConnection; logs RSS peak and duckdb delta per execute().

    Consecutive execute() calls that share the same query label (e.g. a Python
    loop emitting N INSERTs into the same table) are coalesced into one batch
    summary line, emitted when a different label arrives or on close().
    """

    def __init__(self, conn: DuckDBPyConnection) -> None:  # noqa: D107
        self._conn = conn
        self._batch: _Batch | None = None

    def execute(self, query: str, parameters: list | None = None):  # noqa: ANN201
        """Log wall-clock time, RSS peak, and duckdb delta/total, then forward."""
        if not debug:
            return (
                self._conn.execute(query, parameters)
                if parameters is not None
                else self._conn.execute(query)
            )
        t0 = time.perf_counter()
        before_rss = _PROCESS.memory_info().rss
        before_ddb = self._conn.execute(_MEM_Q).fetchall()[0][0]

        peak_rss = [before_rss]
        stop = threading.Event()

        def _poll() -> None:
            while not stop.is_set():
                with contextlib.suppress(Exception):
                    peak_rss[0] = max(peak_rss[0], _PROCESS.memory_info().rss)
                stop.wait(0.05)

        threading.Thread(target=_poll, daemon=True).start()

        result = (
            self._conn.execute(query, parameters)
            if parameters is not None
            else self._conn.execute(query)
        )
        rows = result.fetchall()

        stop.set()
        after_rss = _PROCESS.memory_info().rss
        peak_rss[0] = max(peak_rss[0], after_rss)
        after_ddb = self._conn.execute(_MEM_Q).fetchall()[0][0]

        elapsed = time.perf_counter() - t0
        label = _query_label(query)
        if self._batch is None or self._batch.label != label:
            self._flush()
            self._batch = _Batch(label)
        self._batch.add(elapsed, peak_rss[0], after_ddb - before_ddb, after_ddb)
        return _EagerResult(rows)

    def _flush(self) -> None:
        """Emit the accumulated batch summary, if any."""
        b = self._batch
        if b is None:
            return
        prefix = "query" if b.count == 1 else f"query x{b.count}"
        logger.info(
            "%s %.3fs | rss peak %.0f MB | duckdb %+.0f MB | %.0f MB total | %s",
            prefix,
            b.total_time,
            b.max_rss / 1e6,
            b.duckdb_delta / 1e6,
            b.duckdb_total / 1e6,
            b.label,
        )
        self._batch = None

    def close(self) -> None:
        """Flush the pending batch and close the underlying connection."""
        self._flush()
        self._conn.close()

    def __getattr__(self, name: str) -> object:  # noqa: D105
        return getattr(self._conn, name)


@contextlib.contextmanager
def log_file(name: str) -> Iterator[None]:
    """Tee root logger to ``tmp/{name}.log`` for the duration of the block.

    Pair the ``name`` with the matching ``get_conn()`` name so each .duckdb
    file written has a sibling .log capturing every log line for that scope.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    handler = FileHandler(tmp_dir / f"{name}.log", mode="w")
    handler.setFormatter(
        Formatter("%(asctime)s - %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    root = getLogger()
    root.addHandler(handler)
    try:
        yield
    finally:
        root.removeHandler(handler)
        handler.close()


def get_conn(
    name: str, land: str | None = None, *, reset: bool = True
) -> DuckDBPyConnection:
    """Create a file-based DuckDB connection with the spatial extension loaded.

    The DB file is ``tmp/{name}.duckdb`` or ``tmp/{land}_{name}.duckdb`` when
    ``land`` is given (land-first to mirror the land-outer loop), so each
    step x land combination is fully isolated.

    With ``reset=True`` (default), the .duckdb file is deleted first. Pass
    ``reset=False`` to attach to an existing file (e.g. a snapshot restored via
    ``cp``) for sub-step iteration via ``iter.py``.
    """
    prefix = f"{land}_" if land else ""
    db_path = tmp_dir / f"{prefix}{name}.duckdb"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    if reset:
        db_path.unlink(missing_ok=True)
    conn = connect(db_path)
    conn.execute("LOAD spatial")
    conn.execute("SET enable_progress_bar = false")
    conn.execute("SET geometry_always_xy = true")
    conn.execute("SET preserve_insertion_order = false")
    conn.execute("SET threads = 4")
    raw = conn.execute(
        "SELECT value FROM duckdb_settings() WHERE name = 'memory_limit'"
    ).fetchall()[0][0]
    value, unit = raw.split()
    conn.execute(f"SET memory_limit = '{float(value) * 0.75:.2f} {unit}'")
    return cast("DuckDBPyConnection", ProfiledConnection(conn))


def write_parquet(
    conn: DuckDBPyConnection, table: str, *, spatial: bool = True
) -> None:
    """Write a DuckDB table to a parquet file in tmp_dir."""
    opts = PARQUET_OPTS if spatial else _PARQUET_PLAIN
    path = tmp_dir / f"{table}.parquet"
    conn.execute(f"COPY (SELECT * FROM \"{table}\") TO '{path}' {opts}")


def load_parquet(conn: DuckDBPyConnection, table: str) -> None:
    """Load a parquet file from tmp_dir into a DuckDB table."""
    path = tmp_dir / f"{table}.parquet"
    conn.execute(f"CREATE OR REPLACE TABLE \"{table}\" AS SELECT * FROM '{path}'")


def copy_from_db(conn: DuckDBPyConnection, src: Path, table: str) -> None:
    """Copy a table from another DuckDB file into conn."""
    conn.execute(f"ATTACH '{src}' AS src_db (READ_ONLY)")
    conn.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM src_db."{table}"')
    conn.execute("DETACH src_db")


def discard(conn: DuckDBPyConnection, table: str) -> None:
    """Drop a table from the DuckDB connection (no-op when --debug is set)."""
    if debug:
        return
    conn.execute(f'DROP TABLE IF EXISTS "{table}"')


def has_invalid_coverage(conn: DuckDBPyConnection, table: str) -> bool:
    """Return True if the polygons in ``table`` have overlaps or gaps."""
    return bool(
        conn.execute(f"""--sql
            SELECT ST_CoverageInvalidEdges_Agg(geom) IS NOT NULL
            FROM "{table}"
        """).fetchall()[0][0]
    )


def raise_issues(issues: list[str], context: str) -> None:
    """Log and raise a single RuntimeError if any issues were collected."""
    if not issues:
        return
    for issue in issues:
        logger.info("%s: %s", context, issue)
    raise RuntimeError(f"{context}: {len(issues)} issue(s), {'; '.join(issues)}")


def export_debug_tables(
    conn: DuckDBPyConnection,
    name: str,
    land: str | None = None,
    only: set[str] | None = None,
) -> None:
    """Export tables under ``tmp/debug/`` mirroring the land-outer loop.

    Per-land tables go to ``tmp/debug/{land}/{name}/{table}.parquet`` (with the
    ``{land}_`` prefix stripped from the filename); shared tables go to
    ``tmp/debug/{name}/{table}.parquet``. Only the land and step are folders.
    """
    debug_dir = tmp_dir / "debug"
    land_base = debug_dir / land / name if land else None
    shared_base = debug_dir / name
    other_prefixes = tuple(f"{ln}_" for ln in ALL_LANDS if ln != land)
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' ORDER BY table_name"
    ).fetchall()
    prefix = f"{land}_" if land else None
    for (table,) in tables:
        if only is not None and table not in only:
            continue
        if table.startswith(other_prefixes):
            continue
        if prefix and table.startswith(prefix):
            out = land_base / f"{table[len(prefix) :]}.parquet"
        else:
            out = shared_base / f"{table}.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        has_geom = conn.execute(
            "SELECT COUNT(*) > 0 FROM information_schema.columns "
            f"WHERE table_name = '{table}' AND data_type = 'GEOMETRY'"
        ).fetchall()[0][0]
        opts = PARQUET_OPTS if has_geom else _PARQUET_PLAIN
        conn.execute(f"COPY \"{table}\" TO '{out}' {opts}")
        logger.info("debug export: %s", out.relative_to(tmp_dir))


def get_source_dates() -> tuple[str, str]:
    """Return ``(osm_date, lsib_date)`` as ISO date strings."""
    osm_date = (download_dir / "osm/.date").read_text().strip()
    lsib_date = (download_dir / "lsib/.date").read_text().strip()
    return osm_date, lsib_date


def zip_path(file: Path, file_zip: Path) -> None:
    """Compress file or directory into a zip archive."""
    file_zip.parent.mkdir(parents=True, exist_ok=True)
    if file.is_file():
        with ZipFile(file_zip, "w", ZIP_DEFLATED) as z:
            z.write(file, file.name)
    if file.is_dir():
        make_archive(str(file_zip.with_suffix("")), "zip", file)
